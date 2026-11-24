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
import re
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


_TLS_BINDING_KEYS = frozenset((
    'expected_receipt_sha256', 'expected_model_sha256', 'expected_deposition_owner_sha256',
    'component_aliases', 'max_coordinate_component_error_angstrom',
    'max_u_component_error_angstrom_squared', 'max_b_error_angstrom_squared', 'max_occupancy_error'))


def _validate_tls_binding(original_cif, cif_binding):
    if original_cif is None and cif_binding is None:
        return
    if original_cif is None or not isinstance(cif_binding, dict) or set(cif_binding) != _TLS_BINDING_KEYS:
        raise ValueError('Original CIF inspection requires its explicit path and complete path-free CIF binding')


def representative_scene(directory, *, native_receipt=None, cedar_source=None, backbone_intent=False,
                         original_cif=None, cif_binding=None):
    """Inspect a frozen representative proposal, including exact edge images.

    Points are display coordinates, never a new chemical bond or materialized
    model. Missing anchors remain explicit rather than acquiring guessed points.
    """
    from .topostitch_recut_bundle import load_relabel_preview, observe_relabel_native_links, observe_relabel_backbone_intent
    if type(backbone_intent) is not bool:
        raise ValueError('backbone_intent must be a boolean')
    _validate_tls_binding(original_cif, cif_binding)
    if cedar_source is not None and native_receipt is None and original_cif is None:
        raise ValueError('A trusted Cedar source requires an explicit native receipt or original CIF binding')
    from .topostitch_registration import _fingerprint
    import gemmi
    root=Path(directory);receipt_bytes=(root/'preview.json').read_bytes()
    receipt=load_relabel_preview(root)
    snapshots={k:(root/ref['relative_path']).read_bytes() for k,ref in receipt['artifacts'].items()}
    if (_fingerprint(_json(receipt_bytes))!=_fingerprint(receipt)
            or any(sha256(b).hexdigest()!=receipt['artifacts'][k]['sha256'] for k,b in snapshots.items())):
        raise ValueError('Representative preview changed while preparing its view')
    observation=receipt['observation'];bound=observation['registered_graph'];graph=bound['periodic_graph']
    nodes={n['node_id']:n for n in bound['nodes']}
    owner={i:n for n in nodes.values() for i in n['atom_indices']}
    requested=set(observation['requested_image_atom_indices'])
    images={g['node_id']:g['operator_xyz'] for g in observation['atom_image_groups']}
    atoms=[];residues={}
    for i,record in enumerate(observation['source_orbit_observation']['atoms']):
        identity=record['identity'];site={k:identity[k] for k in ('chain','residue_number','insertion_code')}
        node=owner.get(i);before=record['position_angstrom'];after=observation['proposed_points_angstrom'][i]
        atom=dict(site=site,label=_label(ResidueSite(**site)),residue_code=identity['residue_code'],
            atom_name=identity['atom_name'],altloc=identity['altloc'],occupancy=record['occupancy'],
            source_atom_index=i,node_id=None if node is None else node['node_id'],
            logical_site=None if node is None else node['logical_site'],copy_id=None if node is None else node['copy_id'],
            protected=False if node is None else node['protected'],do_not_connect=False if node is None else node['do_not_connect'],
            mapping_issues=[] if node is None else node['issues'],
            representative_operator_xyz='x,y,z' if node is None else images.get(node['node_id'],'x,y,z'),
            instance='target' if i in requested else 'source',scope='representative' if i in requested else 'unchanged',
            before=before,after=after,displacement_angstrom=math.dist(before,after))
        atoms.append(atom)
        key=tuple(identity[k] for k in ('chain','residue_number','insertion_code','residue_code','altloc'))
        residues.setdefault(key,{}).setdefault(atom['atom_name'],[]).append(i)
    rings=[[names[n][0] for n in _RING] for names in residues.values() if all(len(names.get(n,[]))==1 for n in _RING)]
    edges=[]
    for edge in observation['edge_image_observations']:
        labels={role+'_label':nodes[edge[role+'_node_id']]['copy_id']+'/'+nodes[edge[role+'_node_id']]['logical_site'] for role in ('source','target')}
        edges.append({**edge,**labels})
    cell=gemmi.UnitCell(*graph['crystal']['cell_parameters'])
    fractional=[(x,y,z) for x in (0,1) for y in (0,1) for z in (0,1)]
    corners=[list(cell.orthogonalize(gemmi.Fractional(*p))) for p in fractional]
    cell_edges=[[i,j] for i,p in enumerate(fractional) for j,q in enumerate(fractional) if i<j and sum(a!=b for a,b in zip(p,q))==1]
    warnings=['A representative change is not a physical bend. Edge lengths use O3′ display anchors, not chemical bond lengths.',
              'Whole-object identity, seam chemistry and complete scattering invariance remain unqualified.']
    if observation['unavailable_anchor_node_ids']:warnings.append(f'{len(observation["unavailable_anchor_node_ids"])} declared nodes lack an unambiguous O3′ display anchor.')
    if bound['scope']['unrepresented_atom_indices']:warnings.append(f'{len(bound["scope"]["unrepresented_atom_indices"])} source atoms have no declared graph owner; they remain unchanged.')
    if bound['scope']['outside_declared_routes']:warnings.append(f'{len(bound["scope"]["outside_declared_routes"])} registered nodes are outside the declared routes.')
    if observation['source_orbit_observation']['issues']:warnings.append('Source orbit or occupancy findings require review; see provenance.')
    if (root/'preview.json').read_bytes()!=receipt_bytes or any((root/receipt['artifacts'][k]['relative_path']).read_bytes()!=v for k,v in snapshots.items()):
        raise ValueError('Representative preview inputs changed while preparing the view')
    scene=dict(schema_version=1,kind='topostitch-representative-view',source_model_sha256=receipt['source_model_sha256'],
        preview_receipt_sha256=sha256(receipt_bytes).hexdigest(),representative_preview_sha256=observation['preview_sha256'],
        proposal_sha256=receipt['proposal_sha256'],registered_graph_sha256=receipt['registered_graph_sha256'],
        workflow=receipt['workflow'],runtime_authority=False,coordinates_materialized=False,graphical_review_recorded=False,
        chemical_connectivity_changed=False,atoms=atoms,base_rings=rings,traces=[],contacts=[],
        periodic_edges=edges,nodes=bound['nodes'],declared_routes=bound['declared_routes'],graph_scope=bound['scope'],
        crystal=graph['crystal'],cell_corners=corners,cell_edges=cell_edges,
        component_count=len(graph['components']),cycle_count=graph['cycle_count'],
        source_image_assessment=observation['source_orbit_observation']['assessment'],
        source_orbit_issues=observation['source_orbit_observation']['issues'],warnings=warnings,
        max_atom_displacement_angstrom=max((a['displacement_angstrom'] for a in atoms),default=0.),
        scope='All present source atoms and declared typed graph; target endpoints use exact edge images. No inferred chemical links.')
    if 'forest_selection' in receipt:scene['forest_selection']=receipt['forest_selection']
    if native_receipt is not None:
        native_links=observe_relabel_native_links(root,native_receipt,cedar_source=cedar_source)
        if native_links['preview_receipt_sha256']!=sha256(receipt_bytes).hexdigest():
            raise ValueError('Native link observation belongs to a different representative preview')
        scene['native_links']=native_links
        if native_links['proposed_seam_count']:
            scene['warnings'].append(f'{native_links["proposed_seam_count"]} existing source interresidue bonds cross this proposed ASU boundary; symmetry-bond enforcement remains disabled.')
        if native_links['source_symmetry_links_unqualified']:
            scene['warnings'].append('Source symmetry-bond entries are retained but are outside this identity-link observation.')
    if backbone_intent:
        intent = observe_relabel_backbone_intent(root)
        if intent['preview_receipt_sha256'] != sha256(receipt_bytes).hexdigest():
            raise ValueError('Backbone intent belongs to a different representative preview')
        scene['backbone_intent'] = intent
    if original_cif is not None:
        from .topostitch_cif_tls import observe_relabel_cif_tls
        tls = observe_relabel_cif_tls(root, original_cif, cedar_source=cedar_source, **cif_binding)
        if cif_binding['expected_receipt_sha256'] != scene['preview_receipt_sha256']:
            raise ValueError('Original CIF TLS observation belongs to a different preview')
        if ((root/'preview.json').read_bytes() != receipt_bytes
                or any((root/receipt['artifacts'][k]['relative_path']).read_bytes() != v for k,v in snapshots.items())):
            raise ValueError('Representative preview changed during TLS inspection')
        scene['original_cif_tls'] = tls
    return scene


_MAX_COMPARISON_POINTS = 50_000


def representative_comparison(directories, *, native_receipt=None, cedar_source=None, backbone_intent=False):
    """Compare 2–8 explicit cuts of one frozen source/graph without selecting one.

    Each alternative is the existing verified scene, not a new model or recipe.
    Ordered local cut numbers are presentation identifiers; hashes bind identity.
    """
    from .topostitch_recut_bundle import _FILES
    from .topostitch_registration import _fingerprint
    if not isinstance(directories, (list, tuple)) or not 2 <= len(directories) <= 8:
        raise ValueError('Require 2 to 8 explicit representative packet paths')
    roots = [Path(path).resolve() for path in directories]
    if len(set(roots)) != len(roots):
        raise ValueError('Comparison requires distinct representative packets')
    frozen = {}
    if native_receipt is not None:
        path = Path(native_receipt).expanduser().resolve()
        frozen[path] = path.read_bytes()
    for root in roots:
        manifest = root / 'preview.json'
        data = manifest.read_bytes()
        receipt = _json(data)
        if not isinstance(receipt, dict) or receipt.get('kind') != 'topostitch-representative-preview-bundle':
            raise ValueError('Cut comparison requires representative preview packets')
        frozen[manifest] = data
        for name in _FILES.values():
            path = root / name
            frozen[path] = path.read_bytes()
    scenes = [representative_scene(root, native_receipt=native_receipt, cedar_source=cedar_source, backbone_intent=backbone_intent)
              for root in roots]
    first = scenes[0]
    if any(scene[key] != first[key] for scene in scenes
           for key in ('source_model_sha256', 'registered_graph_sha256')):
        raise ValueError('Cut alternatives must bind the same source and registered graph')
    if len({scene['preview_receipt_sha256'] for scene in scenes}) != len(scenes):
        raise ValueError('Comparison contains duplicate representative packets')
    points = sum(2 * len(scene['atoms']) + sum(4 for edge in scene['periodic_edges']
                 if edge.get('before_points')) for scene in scenes)
    if points > _MAX_COMPARISON_POINTS:
        raise ValueError('Cut comparison exceeds the 50000-point display budget')
    if any(path.read_bytes() != data for path, data in frozen.items()):
        raise ValueError('Representative packets changed during comparison')
    result = dict(schema_version=1, kind='topostitch-representative-comparison-view',
                  source_model_sha256=first['source_model_sha256'],
                  registered_graph_sha256=first['registered_graph_sha256'],
                  alternatives=[dict(cut_id=i, scene=scene) for i, scene in enumerate(scenes, 1)],
                  selection_applied=False, graphical_review_recorded=False,
                  coordinates_materialized=False, chemical_connectivity_changed=False,
                  runtime_authority=False,
                  scope='Caller-supplied cuts of the same source and declared graph; inspection only, no ranking or approval')
    result['comparison_sha256'] = _fingerprint(result)
    return result


def _read_cut_preference(comparison, path):
    """Bind caller-supplied preference text to a freshly replayed comparison."""
    from .topostitch_inspect import _keys
    path = Path(path)
    if path.stat().st_size > 16_384:
        raise ValueError('Cut preference exceeds the 16384-byte size limit')
    data = path.read_bytes()
    if len(data) > 16_384:
        raise ValueError('Cut preference exceeds the 16384-byte size limit')
    request = _json(data)
    fields = {'schema_version', 'kind', 'comparison_sha256', 'source_model_sha256',
              'registered_graph_sha256', 'decision', 'preferred_preview_receipt_sha256', 'comment'}
    if not isinstance(request, dict):
        raise ValueError('Cut preference must be an object')
    _keys(request, fields)
    if (type(request['schema_version']) is not int or request['schema_version'] != 1
            or request['kind'] != 'topostitch-cut-preference'):
        raise ValueError('Unsupported cut preference kind/schema')
    if any(request[key] != comparison[key] for key in
           ('comparison_sha256', 'source_model_sha256', 'registered_graph_sha256')):
        raise ValueError('Preference does not match this exact source-bound comparison')
    decision = request['decision']
    preferred = request['preferred_preview_receipt_sha256']
    if decision not in ('prefer_cut', 'keep_original', 'needs_revision'):
        raise ValueError('Unsupported cut preference decision')
    hashes = [row['scene']['preview_receipt_sha256'] for row in comparison['alternatives']]
    if ((decision == 'prefer_cut' and preferred not in hashes)
            or (decision != 'prefer_cut' and preferred is not None)):
        raise ValueError('Preference must identify exactly one displayed cut or no cut')
    if not isinstance(request['comment'], str) or len(request['comment']) > 2000:
        raise ValueError('Preference comment must contain at most 2000 characters')
    if path.read_bytes() != data:
        raise ValueError('Cut preference changed during validation')
    return {**request, 'kind': 'topostitch-bound-cut-preference',
            'preference_file_sha256': sha256(data).hexdigest(),
            'reviewer_authenticated': False, 'scientific_acceptance': False,
            'checkpoint_selection_applied': False, 'runtime_authority': False}


def validate_cut_preference(directories, preference_path, *, native_receipt=None, cedar_source=None, backbone_intent=False):
    """Reopen an exact comparison before accepting a preference as review input.

    This records neither authenticated human approval nor a checkpoint selection.
    Callers supply explicit packet paths; a checksum never becomes a file locator.
    """
    comparison = representative_comparison(directories, native_receipt=native_receipt, cedar_source=cedar_source, backbone_intent=backbone_intent)
    return _read_cut_preference(comparison, preference_path)


def _script_json(value):
    data=json.dumps(value,separators=(',',':'),allow_nan=False,ensure_ascii=True)
    data=data.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return data


def _html(scene,preference=None):
    template=files('nasolve').joinpath('data/topostitch-view.html').read_text(encoding='utf-8')
    payloads={'__SCENE_JSON__':_script_json(scene),'__PREFERENCE_JSON__':_script_json(preference)}
    return re.sub('__SCENE_JSON__|__PREFERENCE_JSON__',lambda match:payloads[match.group()],template)


def write_preview_view(directory,output_path,*,native_receipt=None,cedar_source=None,comparison_directories=(),preference_path=None,backbone_intent=False,original_cif=None,cif_binding=None,**options):
    _validate_tls_binding(original_cif, cif_binding)
    if cedar_source is not None and native_receipt is None and original_cif is None:
        raise ValueError('A trusted Cedar source requires an explicit native receipt or original CIF binding')
    if type(backbone_intent) is not bool:
        raise ValueError('backbone_intent must be a boolean')
    root=Path(directory).resolve();out=Path(output_path).absolute()
    if out.exists():raise FileExistsError(out)
    if not isinstance(comparison_directories,(list,tuple)) or len(comparison_directories)>7:
        raise ValueError('At most seven additional explicit comparison paths are supported')
    if original_cif is not None and comparison_directories:
        raise ValueError('Original CIF TLS inspection currently requires one explicit representative preview')
    roots=[root]+[Path(path).resolve() for path in comparison_directories]
    if any(out.resolve().is_relative_to(path) for path in roots):raise ValueError('Write the view outside every frozen preview directory')
    receipt=_json((root/'preview.json').read_bytes())
    if not isinstance(receipt,dict):raise ValueError('Unsupported preview receipt')
    kind=receipt.get('kind')
    if comparison_directories or kind=='topostitch-representative-preview-bundle':
        defaults=dict(candidate_index=None,radius_angstrom=None,periodic=False,max_pairs=100_000,max_image_tests=100_000)
        if any(k not in defaults or type(v) is not type(defaults[k]) or v!=defaults[k] for k,v in options.items()):
            raise ValueError('Representative preview already declares its images; bend-search options do not apply')
        scene=(representative_comparison(roots,native_receipt=native_receipt,cedar_source=cedar_source,backbone_intent=backbone_intent) if comparison_directories
               else representative_scene(root,native_receipt=native_receipt,cedar_source=cedar_source,backbone_intent=backbone_intent,original_cif=original_cif,cif_binding=cif_binding))
    else:
        if original_cif is not None:raise ValueError('Original CIF TLS inspection requires a representative preview')
        if backbone_intent:raise ValueError('Backbone intent observation requires a representative preview')
        if native_receipt is not None:raise ValueError('Native seam observation requires a representative preview')
        scene=preview_scene(root,**options)
    if preference_path is not None and scene['kind']!='topostitch-representative-comparison-view':
        raise ValueError('A cut preference requires an explicit comparison')
    preference=None if preference_path is None else _read_cut_preference(scene,preference_path)
    html=_html(scene,preference)  # Validate the installed asset before creating any output.
    with out.open('x',encoding='utf-8') as stream:stream.write(html)
    return scene


def main(argv=None):
    parser=argparse.ArgumentParser(prog='nasolve-topostitch-view',description='Write an offline, read-only view of a verified bend or representative preview.')
    parser.add_argument('preview',type=Path)
    parser.add_argument('--out',type=Path,required=True,help='New standalone HTML file outside the frozen preview')
    parser.add_argument('--compare',type=Path,action='append',default=[],help='Additional explicit cut packet from the same source/graph (repeat up to seven times)')
    parser.add_argument('--preference',type=Path,help='Reopen a saved preference bound to this exact comparison; never selects a model')
    parser.add_argument('--candidate',type=int,help='Explicit candidate index in the original model search')
    parser.add_argument('--radius',type=float,help='Exact source search radius when choosing a candidate')
    parser.add_argument('--periodic',action='store_true',help='Show the exact chosen symmetry mate (requires topology extra)')
    parser.add_argument('--max-pairs',type=int,default=100_000)
    parser.add_argument('--max-image-tests',type=int,default=100_000)
    parser.add_argument('--backbone-intent',action='store_true',help='Show declared backbone continuation and phosphate inventory without changing chemistry')
    parser.add_argument('--native-receipt',type=Path,help='Optional authenticated source capture for existing-link seam observations')
    parser.add_argument('--cedar-source',type=Path,help='Explicit trusted developer Cedar source; default uses installed owners')
    parser.add_argument('--original-cif',type=Path,help='Original coordinate CIF for read-only TLS membership inspection')
    parser.add_argument('--cif-binding',type=Path,help='Path-free JSON with exact source/preview/owner hashes, aliases and working-file precision bounds')
    args=parser.parse_args(argv)
    try:
        binding=None if args.cif_binding is None else _json(args.cif_binding.read_bytes())
        scene=write_preview_view(args.preview,args.out,candidate_index=args.candidate,radius_angstrom=args.radius,
        periodic=args.periodic,max_pairs=args.max_pairs,max_image_tests=args.max_image_tests,native_receipt=args.native_receipt,cedar_source=args.cedar_source,comparison_directories=args.compare,preference_path=args.preference,backbone_intent=args.backbone_intent,original_cif=args.original_cif,cif_binding=binding)
    except (OSError,ValueError,RuntimeError,ImportError) as exc:parser.exit(2,f'{parser.prog}: {exc}\n')
    detail=(str(len(scene['alternatives']))+' explicit cuts; none selected' if 'alternatives' in scene
            else str(len(scene['atoms']))+' displayed atom instances; proposal remains unreviewed')
    print(f'Read-only view: {args.out}\n{detail}.')
    return 0


if __name__=='__main__':sys.exit(main())
