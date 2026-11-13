"""Portable, read-only graphical comparison of a verified TopoStitch preview.

The scene contains actual frozen coordinates and an optional explicitly selected
mate. It owns no model selection, scientific approval or checkpoint state.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files
import json
import math
from pathlib import Path
import sys

from .topostitch_coordinates import ResidueSite,_read_atoms,_residue
from .topostitch_inspect import load_registered_end_assignments
from .topostitch_preview import _json,load_bend_preview
from .topostitch_registration import _coordinate_site

_RING=('N1','C2','N3','C4','C5','C6')


def _label(site):
    return f'{site.chain}:{site.residue_number}{site.insertion_code}'


def preview_scene(directory, *, candidate_index=None, radius_angstrom=None,
                  periodic=False, max_pairs=100_000, max_image_tests=100_000):
    """Build a detached scene after replay; never trust a supplied fit report."""
    if type(periodic) is not bool:
        raise ValueError('periodic must be a boolean')
    if candidate_index is None and (periodic or radius_angstrom is not None):
        raise ValueError('A candidate index is required for a mate/radius selection')
    if candidate_index is not None and (type(candidate_index) is not int or candidate_index<0 or radius_angstrom is None):
        raise ValueError('An explicit nonnegative candidate index and radius are required')
    root=Path(directory)
    receipt_bytes=(root/'preview.json').read_bytes()
    receipt=load_bend_preview(root)
    snapshots={name:(root/ref['relative_path']).read_bytes() for name,ref in receipt['artifacts'].items()}
    if _json(receipt_bytes)!=receipt or any(sha256(data).hexdigest()!=receipt['artifacts'][name]['sha256'] for name,data in snapshots.items()):
        raise ValueError('Preview changed while preparing its view')
    registry=_json(snapshots['registration']);manifest=_json(snapshots['discovery'])
    copy=next(c for c in registry['copies'] if c['copy_id']==receipt['window']['copy_id'])
    mapping={m['logical_site']:_coordinate_site(m['coordinate_site']) for m in copy['mappings']}
    movable={mapping[s] for s in receipt['window']['movable_sites']}
    fixed={mapping[s] for s in receipt['window']['fixed_sites']}
    digest,assignments,_,_=load_registered_end_assignments(root/'source.pdb',root/'discovery.json',root/'registration.json')
    selected=None;contacts=None;crystal=None;source_audit=None;candidate_audit=None
    identity=lambda xyz:list(xyz)
    instances=[('source',movable|fixed,identity)]
    if candidate_index is not None:
        from .topostitch_contacts import inspect_end_contacts
        observation=inspect_end_contacts(root/'source.pdb',assignments,expected_sha256=digest,
            max_distance_angstrom=radius_angstrom,periodic=periodic,max_pairs=max_pairs,max_image_tests=max_image_tests)
        screen=observation['periodic_screening' if periodic else 'screening']
        if candidate_index>=len(screen['candidates']):raise ValueError('Candidate index is outside the exact source search')
        selected=screen['candidates'][candidate_index]
        if receipt['window']['end_id'] not in selected['ends']:
            raise ValueError('Selected connection does not contain the preview window')
        by_id={a.end_id:a for a in assignments};instances=[];transform=identity
        if periodic:
            from .topostitch_transport import crystallographic_image
            from .topostitch_images import _attach_image_audit,_audit_transformed_image
            crystal={k:screen['inputs'][k] for k in ('cell_parameters','space_group')}
            image=crystallographic_image(**crystal,operator_xyz=selected['target_image']['operator_xyz'])
            transform=lambda xyz:list(image.apply(xyz))
            _attach_image_audit(root/'source.pdb',assignments,observation,candidate_index=candidate_index)
            source_audit=observation['selected_image_identity']
            # The preview replay already proves identity-preserving atom motion.
            # Keep ambiguity visible for inspection instead of hiding the model.
            if source_audit['assessment']=='SELECTED_COORDINATES_DISTINCT':
                candidate_audit=_audit_transformed_image(snapshots['candidate'],source_audit,**crystal)
        for role,end_id in zip(('source','target'),selected['ends']):
            end=by_id[end_id];sites=set(end.overhang_sites+end.terminal_pair+end.inner_pair)
            if end_id==receipt['window']['end_id']:sites|=movable|fixed
            instances.append((role,sites,transform if role=='target' else identity))
        contacts=observation['contact_assessment']['candidates'][candidate_index]
    inventories=[_read_atoms(snapshots[k]) for k in ('source','candidate')]
    atoms=[];lookup={};rings=[];traces=[]
    for role,sites,transform in instances:
        for site in sorted(sites,key=lambda s:(s.chain,s.residue_number,s.insertion_code)):
            code,before=_residue(inventories[0],site);after_code,after=_residue(inventories[1],site)
            if code!=after_code or set(before)!=set(after):raise ValueError('Preview atom identities differ')
            for name in sorted(before):
                index=len(atoms);lookup[(role,site,name)]=index
                atoms.append({'site':asdict(site),'label':_label(site),'residue_code':'D'+code,
                    'atom_name':name,'instance':role,'scope':'movable' if site in movable else 'fixed' if site in fixed else 'partner',
                    'before':transform(before[name]),'after':transform(after[name]),
                    'displacement_angstrom':math.dist(before[name],after[name])})
            ring=[lookup[(role,site,n)] for n in _RING if n in before]
            if len(ring)==len(_RING):rings.append(ring)
        for strand in manifest['strands']:
            for a,b in zip(strand['sites'],strand['sites'][1:]):
                left=(role,mapping.get(a),"O3'");right=(role,mapping.get(b),"O3'")
                if left in lookup and right in lookup:traces.append([lookup[left],lookup[right]])
    contact_edges=[];incomplete=0
    if contacts is not None:
        for pair in contacts['residue_pairs']:
            for bond in pair['bonds']:
                keys=[(a['image'],ResidueSite(**a['site']),a['atom_name']) for a in bond['atoms']]
                if any(k not in lookup for k in keys):incomplete+=1;continue
                ids=[lookup[k] for k in keys]
                contact_edges.append({'atoms':ids,'before_angstrom':math.dist(*(atoms[i]['before'] for i in ids)),
                    'after_angstrom':math.dist(*(atoms[i]['after'] for i in ids)),
                    'reference_angstrom':bond['reference_ideal']})
    warnings=[]
    if source_audit is not None and source_audit['assessment']!='SELECTED_COORDINATES_DISTINCT':warnings.append('The selected original images need identity or occupancy review.')
    if candidate_audit is not None and candidate_audit['assessment']!='SELECTED_COORDINATES_DISTINCT':warnings.append('The candidate introduces a selected-image coincidence; review this placement.')
    if incomplete:warnings.append(f'{incomplete} proposed contacts lack displayable atoms.')
    if (root/'preview.json').read_bytes()!=receipt_bytes or any((root/receipt['artifacts'][k]['relative_path']).read_bytes()!=v for k,v in snapshots.items()):
        raise ValueError('Preview inputs changed while preparing the view')
    return {'schema_version':1,'kind':'topostitch-preview-view',
        'source_model_sha256':receipt['source_model_sha256'],'candidate_model_sha256':receipt['candidate_model_sha256'],
        'preview_receipt_sha256':sha256(receipt_bytes).hexdigest(),'workflow':receipt['workflow'],
        'runtime_authority':False,'geometry_validated':False,'window':receipt['window'],
        'atoms':atoms,'base_rings':rings,'traces':traces,'contacts':contact_edges,'crystal':crystal,
        'selected_candidate':selected,'source_image_assessment':None if source_audit is None else source_audit['assessment'],
        'candidate_image_assessment':None if candidate_audit is None else candidate_audit['assessment'],
        'max_atom_displacement_angstrom':receipt['max_atom_displacement_angstrom'],
        'backbone_audit':receipt['backbone_audit'],'warnings':warnings,
        'scope':'Declared O3-prime traces and selected base contacts; lines are not an inferred covalent graph',
        'search':None if selected is None else {'candidate_index':candidate_index,'radius_angstrom':radius_angstrom,
            'periodic':periodic,'max_pairs':max_pairs,'max_image_tests':max_image_tests}}


def _html(scene):
    data=json.dumps(scene,separators=(',',':'),allow_nan=False,ensure_ascii=True)
    data=data.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    template=files('nasolve').joinpath('data/topostitch-view.html').read_text(encoding='utf-8')
    return template.replace('__SCENE_JSON__',data)


def write_preview_view(directory,output_path,**options):
    root=Path(directory).resolve();out=Path(output_path).absolute()
    if out.exists():raise FileExistsError(out)
    if out.resolve().is_relative_to(root):raise ValueError('Write the view outside the frozen preview directory')
    scene=preview_scene(root,**options)
    with out.open('x',encoding='utf-8') as stream:stream.write(_html(scene))
    return scene


def main(argv=None):
    parser=argparse.ArgumentParser(prog='nasolve-topostitch-view',description='Write an offline, read-only view of a verified original/candidate preview.')
    parser.add_argument('preview',type=Path)
    parser.add_argument('--out',type=Path,required=True,help='New standalone HTML file outside the frozen preview')
    parser.add_argument('--candidate',type=int,help='Explicit candidate index in the original model search')
    parser.add_argument('--radius',type=float,help='Exact source search radius when choosing a candidate')
    parser.add_argument('--periodic',action='store_true',help='Show the exact chosen symmetry mate (requires topology extra)')
    parser.add_argument('--max-pairs',type=int,default=100_000)
    parser.add_argument('--max-image-tests',type=int,default=100_000)
    args=parser.parse_args(argv)
    try:scene=write_preview_view(args.preview,args.out,candidate_index=args.candidate,radius_angstrom=args.radius,
        periodic=args.periodic,max_pairs=args.max_pairs,max_image_tests=args.max_image_tests)
    except (OSError,ValueError,RuntimeError) as exc:parser.exit(2,f'{parser.prog}: {exc}\n')
    print(f'Read-only view: {args.out}\n{len(scene["atoms"])} displayed atom instances; candidate remains unreviewed.')
    return 0


if __name__=='__main__':sys.exit(main())
