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
    _keys(request,{'schema_version','kind','registered_graph_sha256','node_images','extra_edges',
                   'coincidence_tolerance_angstrom','max_atom_tests'})
    if (type(request['schema_version']) is not int or request['schema_version']!=1
            or request['kind']!='topostitch-representative-proposal'):
        raise ValueError('Unsupported representative proposal kind/schema')
    if not isinstance(request['registered_graph_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',request['registered_graph_sha256']):
        raise ValueError('Require the exact registered graph SHA-256')
    observation=preview_registered_relabel(paths['source'],paths['discovery'],paths['registration'],
        node_images=request['node_images'],extra_edges=request['extra_edges'],
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
