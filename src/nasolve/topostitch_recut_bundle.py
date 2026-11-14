"""Immutable, replayable explicit representative previews for Pine review.

Only unchanged source inputs and a derived JSON observation are stored. This
packet is neither an edited ASU nor a NASolve checkpoint or chemistry decision.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from .run_context import artifact_reference, resolve_artifact_path
from .topostitch_inspect import _keys
from .topostitch_preview import _json
from .topostitch_recut import preview_registered_relabel
from .topostitch_registration import _fingerprint

_FILES={'source':'source.pdb','discovery':'discovery.json',
        'registration':'registration.json','proposal':'proposal.json'}


def _prepare(model,discovery,registration,proposal):
    paths={name:Path(path) for name,path in zip(_FILES,(model,discovery,registration,proposal))}
    snapshots={name:path.read_bytes() for name,path in paths.items()}
    request=_json(snapshots['proposal'])
    if (not isinstance(request,dict) or type(request.get('schema_version')) is not int
            or request['schema_version']!=1 or request.get('kind') not in
            ('topostitch-representative-proposal','topostitch-forest-proposal')):
        raise ValueError('Unsupported representative proposal kind/schema')
    common={'schema_version','kind','registered_graph_sha256','extra_edges',
            'coincidence_tolerance_angstrom','max_atom_tests'}
    forest_request=request['kind']=='topostitch-forest-proposal'
    _keys(request,common|({'selected_edge_ids','anchor_node_ids'} if forest_request else {'node_images'}))
    if not isinstance(request['registered_graph_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',request['registered_graph_sha256']):
        raise ValueError('Require the exact registered graph SHA-256')
    selection=None
    if forest_request:
        from .topostitch_graph import build_registered_periodic_graph,propose_forest_representatives
        bound=build_registered_periodic_graph(paths['source'],paths['discovery'],paths['registration'],extra_edges=request['extra_edges'])
        if bound['report_sha256']!=request['registered_graph_sha256']:
            raise ValueError('Registered graph checksum mismatch for the selected forest')
        graph=bound['periodic_graph']
        derived=propose_forest_representatives(graph,selected_edge_ids=request['selected_edge_ids'],
            anchor_node_ids=request['anchor_node_ids'],expected_graph_sha256=graph['graph_sha256'])
        images=derived['node_images']
        selection=dict(selected_edge_ids=derived['selected_edge_ids'],anchor_node_ids=derived['anchor_node_ids'],
            source_graph_sha256=graph['graph_sha256'],graph_proposal_sha256=derived['proposal_sha256'])
    else:images=request['node_images']
    observation=preview_registered_relabel(paths['source'],paths['discovery'],paths['registration'],
        node_images=images,extra_edges=request['extra_edges'],
        expected_registered_graph_sha256=request['registered_graph_sha256'],
        coincidence_tolerance_angstrom=request['coincidence_tolerance_angstrom'],
        max_atom_tests=request['max_atom_tests'])
    if any(path.read_bytes()!=snapshots[name] for name,path in paths.items()):
        raise ValueError('Representative proposal inputs changed during preparation')
    receipt=dict(schema_version=1,kind='topostitch-representative-preview-bundle',
        status='PREVIEW_BUILT_REVIEW_REQUIRED',source_model_sha256=observation['source_model_sha256'],
        registered_graph_sha256=request['registered_graph_sha256'],
        proposal_sha256=sha256(snapshots['proposal']).hexdigest(),observation=observation,
        workflow=dict(execution_state='PREVIEW_BUILT',review_state='UNREVIEWED',refinement_state='NOT_ATTEMPTED'),
        coordinates_materialized=False,graphical_review_recorded=False,chemical_connectivity_changed=False,
        checkpoint_created=False,selection_applied=False,runtime_authority=False,
        limitations=['Immutable proposal/source snapshot and numerical image observations only',
                     'No replacement model, editable chemistry registry, native restraint or checkpoint selection',
                     'Exact preview replay requires compatible algorithm and Gemmi runtime; no silent migration',
                     'Scattering observation is separate and must bind this exact source/preview; complete invariance remains open'])
    if selection is not None:receipt['forest_selection']=selection
    return snapshots,receipt


def build_relabel_preview(model,discovery,*,registration_path,proposal_path,output_directory):
    """Freeze one explicit proposal in a new directory after full validation.

    Existing outputs are never overwritten. An interrupted write leaves its
    partial directory for inspection; absence of preview.json means incomplete.
    """
    root=Path(output_directory)
    if root.exists():raise FileExistsError(f'Representative preview already exists: {root}')
    snapshots,receipt=_prepare(model,discovery,registration_path,proposal_path)
    root.mkdir()
    references={}
    for name,filename in _FILES.items():
        path=root/filename
        with path.open('xb') as stream:stream.write(snapshots[name])
        references[name]={**artifact_reference(path,root),'sha256':sha256(snapshots[name]).hexdigest(),
                          'size_bytes':len(snapshots[name])}
    receipt['artifacts']=references
    with (root/'preview.json').open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    return receipt


def load_relabel_preview(directory):
    """Verify anchored inputs and recompute the complete registered observation.

    Rehashing a changed derived report cannot make it replay. No original input
    path is consulted; the only operational inputs are the declared local files.
    """
    root=Path(directory);receipt_bytes=(root/'preview.json').read_bytes();receipt=_json(receipt_bytes)
    if (not isinstance(receipt,dict) or type(receipt.get('schema_version')) is not int
            or receipt['schema_version']!=1 or receipt.get('kind')!='topostitch-representative-preview-bundle'):
        raise ValueError('Unsupported representative preview receipt')
    references=receipt.get('artifacts')
    if not isinstance(references,dict) or set(references)!=set(_FILES):
        raise ValueError('Incomplete representative preview artifact inventory')
    paths={}
    for name,filename in _FILES.items():
        ref=references[name]
        _keys(ref,{'anchor','relative_path','sha256','size_bytes'})
        if (ref['anchor']!='run' or ref['relative_path']!=filename
                or not isinstance(ref['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',ref['sha256'])
                or type(ref['size_bytes']) is not int or ref['size_bytes']<0):
            raise ValueError('Require exact local anchored representative artifacts')
        path=resolve_artifact_path(ref,root)
        if path is None or path.stat().st_size!=ref['size_bytes']:
            raise ValueError('Missing or changed representative preview artifact')
        paths[name]=path
    snapshots,expected=_prepare(*(paths[name] for name in _FILES))
    expected['artifacts']=references
    if _fingerprint(expected)!=_fingerprint(receipt) or (root/'preview.json').read_bytes()!=receipt_bytes:
        raise ValueError('Representative preview does not reproduce from frozen inputs')
    if any(sha256(snapshots[name]).hexdigest()!=references[name]['sha256']
            or paths[name].read_bytes()!=snapshots[name] for name in _FILES):
        raise ValueError('Representative preview artifacts changed during replay')
    return receipt



def observe_relabel_native_links(directory, native_receipt, *, cedar_source=None):
    """Expose existing source bonds that a proposed representation cuts.

    Cedar authenticates the capture and binds native atoms/identity links. Only
    those already interpreted interresidue identity bonds are transported here.
    Source symmetry bonds remain explicit unqualified evidence; no bond, angle,
    terminal atom or model is generated, and native interpretation is not run.
    """
    import math
    from .topostitch_captured_job import _cedar
    from .topostitch_graph import _compose, _inverse
    from .topostitch_periodic import _crystal
    from .topostitch_recut import _arithmetic_bound
    root=Path(directory);manifest=root/'preview.json';manifest_bytes=manifest.read_bytes()
    packet=load_relabel_preview(root)
    frozen={root/ref['relative_path']:(root/ref['relative_path']).read_bytes() for ref in packet['artifacts'].values()}
    if (_fingerprint(_json(manifest_bytes))!=_fingerprint(packet)
            or any(sha256(frozen[root/ref['relative_path']]).hexdigest()!=ref['sha256'] for ref in packet['artifacts'].values())):
        raise ValueError('Representative packet changed before native link binding')
    model=frozen[root/'source.pdb'];preview=packet['observation'];bound=preview['registered_graph']
    if sha256(model).hexdigest()!=packet['source_model_sha256']:
        raise ValueError('Native link source differs from the representative packet')
    with _cedar(cedar_source) as cedar:
        owner=cedar['cif_attachment_native']
        receipt,native,captured=owner._capture(Path(native_receipt),model)
        if receipt['status']!='REVIEW':raise ValueError('Require a complete read-only source native capture')
        keys,labels=owner._native_atoms(native,model)
        links,symmetry=owner._links(native,keys,labels,{key[0] for key in keys})
        crystal=bound['periodic_graph']['crystal']
        gemmi,cell,_=_crystal(crystal['cell_parameters'],crystal['space_group']);identity=gemmi.Op('x,y,z')
        atoms=preview['source_orbit_observation']['atoms'];by_key={};site_images={}
        for i,row in enumerate(atoms):
            a=row['identity']
            if a['altloc'] or a['insertion_code']:raise ValueError('Native link view requires unambiguous source residue identities')
            key=((a['chain'] or '_')+':'+str(a['residue_number']),a['residue_code'],a['atom_name'])
            if key in by_key:raise ValueError('Duplicate source atom identity')
            by_key[key]=i
        if len(keys)!=len(by_key) or set(keys)!=set(by_key):raise ValueError('Native and preview atom identities differ')
        image_by_atom={i:'x,y,z' for i in range(len(atoms))}
        for group in preview['atom_image_groups']:
            for i in group['atom_indices']:image_by_atom[i]=group['operator_xyz']
        for key,i in by_key.items():
            xyz=image_by_atom[i]
            if key[0] in site_images and site_images[key[0]]!=xyz:
                raise ValueError('Native link observation requires whole-residue images')
            site_images[key[0]]=xyz
        node_by_site={node['mapping']['coordinate_site']:node['node_id'] for node in bound['nodes'] if node['mapping'] is not None}
        rows=[]
        for number,link in enumerate(links,1):
            a,b=[tuple(k) for k in link['endpoints']];i,j=by_key[a],by_key[b]
            left,right=gemmi.Op(site_images[a[0]]),gemmi.Op(site_images[b[0]])
            relative=_compose(left,_inverse(right,identity))
            before=[atoms[i]['position_angstrom'],atoms[j]['position_angstrom']]
            proposed=[preview['proposed_points_angstrom'][i],preview['proposed_points_angstrom'][j]]
            transformed=list(cell.op_as_transform(relative).apply(gemmi.Position(*proposed[1])))
            expected=[list(cell.op_as_transform(left).apply(gemmi.Position(*p))) for p in before]
            actual=[proposed[0],transformed];tolerance=_arithmetic_bound(*before,*actual,*expected)
            error=max(abs(a-b) for p,q in zip(actual,expected) for a,b in zip(p,q))
            if error>tolerance or abs(math.dist(*actual)-math.dist(*before))>4*tolerance:
                raise ValueError('Transported native source link changed its image geometry')
            nodes=[node_by_site.get(key[0]) for key in (a,b)]
            declared=[edge['edge_id'] for edge in bound['periodic_graph']['edges']
                if edge['kind']=='covalent_backbone' and None not in nodes
                and {edge['source'],edge['target']}==set(nodes) and edge['target_operator_xyz']=='x,y,z']
            phosphate=None
            if {a[2].replace('*',"'"),b[2].replace('*',"'")}=={"O3'",'P'}:
                site=next(key[0] for key in (a,b) if key[2]=='P')
                present=sorted(key[2] for key in by_key if key[0]==site and key[2] in ('P','OP1','OP2'))
                phosphate=dict(site=site,present_source_atoms=present,missing_source_atoms=sorted(set(('P','OP1','OP2'))-set(present)),atoms_created_or_deleted=False)
            rows.append(dict(link_id=number,source_link=link,source_atom_indices=[i,j],
                status='PROPOSED_SYMMETRY_SEAM' if relative.triplet()!='x,y,z' else 'SAME_REPRESENTATIVE',
                source_site_images=[left.triplet(),right.triplet()],proposed_target_operator_xyz=relative.triplet(),
                before_points=before,after_image_points=actual,after_direct_points=proposed,
                before_distance_angstrom=math.dist(*before),after_image_distance_angstrom=math.dist(*actual),
                after_direct_distance_angstrom=math.dist(*proposed),maximum_coordinate_error_angstrom=error,
                declared_backbone_edge_ids=declared,phosphate_inventory=phosphate))
        if any(path.read_bytes()!=data for path,data in captured.items()):raise ValueError('Native capture changed during seam observation')
    if manifest.read_bytes()!=manifest_bytes or any(path.read_bytes()!=data for path,data in frozen.items()):
        raise ValueError('Representative packet changed during seam observation')
    result=dict(schema_version=1,kind='topostitch-representative-native-link-observation',status='SOURCE_LINKS_REVIEW_REQUIRED',
        source_model_sha256=packet['source_model_sha256'],preview_receipt_sha256=sha256(manifest_bytes).hexdigest(),
        preview_sha256=preview['preview_sha256'],native_receipt_sha256=sha256(captured[Path(native_receipt).expanduser().resolve()]).hexdigest(),
        native_policy_id=receipt['policy_id'],native_version=receipt['phenix_version'],
        native_bond_counts={k:native['geometry']['proxy_counts'][k] for k in ('bond_simple','bond_asu')},
        links=rows,proposed_seam_count=sum(r['status']=='PROPOSED_SYMMETRY_SEAM' for r in rows),
        source_symmetry_links_unqualified=symmetry,source_atom_count=len(atoms),
        bond_enforcement_enabled=False,chemical_connectivity_changed=False,phosphate_atoms_changed=False,
        coordinates_materialized=False,scientific_acceptance=False,runtime_authority=False,
        limitations=['Source native interpretation is evidence, not complete intended topology or chemical approval',
                     'Only existing interresidue identity simple bonds are transported; source symmetry bonds and all angle/exclusion policies remain unqualified',
                     'Direct proposed-ASU separation may be large while exact-image distance is unchanged; no automatic bond, OP3 or dephosphorylation'])
    result['report_sha256']=_fingerprint(result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(prog='nasolve-topostitch-cut-preview',
        description='Freeze an explicit representative proposal for review; no edited model or chemical link.')
    parser.add_argument('model',type=Path)
    parser.add_argument('--discovery',type=Path,required=True)
    parser.add_argument('--registration',type=Path,required=True)
    parser.add_argument('--proposal',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True,help='New immutable preview directory')
    args=parser.parse_args(argv)
    try:
        result=build_relabel_preview(args.model,args.discovery,registration_path=args.registration,
            proposal_path=args.proposal,output_directory=args.out)
    except (OSError,ValueError,RuntimeError) as exc:parser.exit(2,f'{parser.prog}: {exc}\n')
    print(f'Representative preview: {args.out}\n{len(result["observation"]["requested_image_atom_indices"])} atoms proposed in new images; source remains unchanged and preview unreviewed.')
    return 0


if __name__=='__main__':sys.exit(main())
