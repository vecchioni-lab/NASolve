"""Bind source-selected bond proposals to one existing prepared repair attempt.

This adapter neither runs tools nor authorizes chemistry. The existing prepared
executor owns the library lookup, repair, attribution, fallback and publication.
"""
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_dictionary_sites import _need
from .cif_dictionary_store import _bytes, _json, resolve_dictionary_snapshot
from .cif_energy_library import discover_bond_targets, read_energy_library
from .cif_linear_bond_reference import linear_bond_query
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-prepared-source-bond-discovery-v1'
ANCHOR = 'repair_directory'
REPORT = 'bond_discovery.json'


def bond_discovery_fields(enabled, explicit=None):
    _need(type(enabled) is bool, 'automatic_bond_targets must be a boolean')
    _need(not enabled or explicit is None, 'Automatic and explicit bond targets cannot be combined')
    return {'bond_discovery_policy':POLICY_ID} if enabled else {}


def prepared_bond_queries(bundle):
    """Screen exact frozen sources using the existing coordinate-free query."""
    bundle=Path(bundle);prepared=read_dictionary_bundle(bundle);queries={}
    codes=prepared['report']['components']
    _need(1<=len(codes)<=16, 'Bond discovery requires one to sixteen source-owned components')
    for code in sorted(codes):
        source=resolve_dictionary_snapshot(bundle/'components'/code/'snapshot')['source']
        query=linear_bond_query(source,code)
        queries[code]=dict(source_sha256=query['source_sha256'],
            query_sha256=sha256(_bytes(query)).hexdigest(),selected_bonds=query['selected_bonds'])
    return queries


def bond_discovery_plan(directory, dictionaries):
    """Reproduce all proposals for the exact dictionaries preceding bond repair.

    Captured lookup failure stays explicit; deciding whether it permits original
    fallback belongs to the executor's frozen optional-failure policy.
    """
    root=Path(directory);bundle=root/'bundle';prepared=read_dictionary_bundle(bundle)
    queries=prepared_bond_queries(bundle)
    _need(isinstance(dictionaries,(list,tuple)) and len(dictionaries)==len(prepared['after_dictionaries']),
          'Discovery requires the complete ordered prepared dictionary set')
    refs=[_ref(Path(p),root,ANCHOR) for p in dictionaries]
    selected=[code for code,row in queries.items() if row['selected_bonds']]
    indices={code:prepared['after_dictionaries'].index(prepared['component_dictionaries'][code]) for code in selected}
    _need(len(set(indices.values()))==len(indices),'Discovery requires distinct source-owned component dictionaries')
    library=None;proposals={};choices={};status='NO_SOURCE_NEIGHBORHOODS'
    if selected:
        lookup=read_energy_library(root/'energy-library')
        spec=_json((root/'energy-library/spec.json').read_bytes())
        _need(_bytes(spec['consumer'])==_bytes(prepared['report']['consumer']),
              'Discovery library belongs to another consumer')
        library=_ref(root/'energy-library/energy_library_receipt.json',root,ANCHOR)
        status='REFERENCE_UNAVAILABLE'
        if lookup['status']=='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED':
            status='DISCOVERED'
            for code in selected:
                source=resolve_dictionary_snapshot(bundle/'components'/code/'snapshot')['source']
                proposal=discover_bond_targets(source,dictionaries[indices[code]],code,root/'energy-library',
                                              consumer=prepared['report']['consumer'])
                proposals[code]=proposal;choices.update(proposal['bond_targets'])
    _need(refs==[_ref(Path(p),root,ANCHOR) for p in dictionaries]
          and queries==prepared_bond_queries(bundle),'Discovery inputs changed during planning')
    return dict(schema_version=1,policy_id=POLICY_ID,status=status,queries=queries,
        dictionaries=refs,library=library,proposals=proposals,choices=choices,
        chemical_approval='NOT_ASSESSED',automatic_adoption=False,new_native_calls=0)


def read_bond_discovery_plan(directory,dictionaries,record):
    """Verify saved decisions offline; never create a new attempt or write files."""
    _need(isinstance(record,dict) and _bytes(record)==_bytes(bond_discovery_plan(directory,dictionaries)),
          'Frozen bond discovery does not reproduce from its exact source/dictionary/library')
    return record


def validate_prepared_bond_discovery(directory, execution):
    """Bind a completed execution to its saved proposal and preceding stages."""
    from .cif_dictionary_sites import _safe, _read
    root=Path(directory)
    _need(execution.get('bond_discovery_policy')==POLICY_ID and 'bond_targets' not in execution,
          'Execution discovery intent differs or competes with explicit choices')
    queries=prepared_bond_queries(root/'bundle')
    eligible=[code for code,row in queries.items() if row['selected_bonds']]
    if 'bond_discovery' not in execution:
        _need(not any(k in execution for k in ('energy_library','bond_plans','bond_results'))
              and (not eligible or execution.get('status')=='SOURCE_PREPARATION_UNQUALIFIED'
                   or 'optional_failure' in execution), 'Execution lost its frozen bond discovery')
        return
    _need(bool(eligible),'Unexpected discovery for absent source neighborhoods')
    def load(ref):
        _need(isinstance(ref,dict) and ref.get('anchor')==ANCHOR and _safe(ref.get('path')),
              'Invalid discovery dependency reference')
        path=root/ref['path'];_need(_ref(path,root,ANCHOR)==ref,'Discovery dependency changed')
        return _json(_read(path))
    plan=load(execution['plan'])
    dictionaries=[root/'plan'/r['path'] for r in (plan['steps'][-1]['dictionaries_after'] if plan['steps'] else plan['inputs'])]
    # Plane changes precede every discovery; the bond plan must bind their final
    # dictionary bytes, not a pre-plane copy or an unrelated equal-length list.
    for ref in execution.get('plane_plans',[]):
        stage=load(ref);index=stage['dictionary_index']
        _need(type(index) is int and 0<=index<len(dictionaries),'Invalid preceding plane index')
        load_candidate=stage['candidate'];_need(_ref(root/load_candidate['path'],root,ANCHOR)==load_candidate,
                                                'Preceding plane candidate changed')
        dictionaries[index]=root/load_candidate['path']
    ref=execution['bond_discovery']
    _need(isinstance(ref,dict) and ref.get('path')==REPORT,'Discovery has another output location')
    record=read_bond_discovery_plan(root,dictionaries,load(ref))
    _need(record['library']==execution.get('energy_library'),'Discovery library differs from execution')
    if record['status']=='REFERENCE_UNAVAILABLE':
        from .cif_prepared_repair_failure import FALLBACK_POLICY_ID
        _need(execution.get('optional_failure_policy')==FALLBACK_POLICY_ID,
              'Unavailable discovery reference lacks the frozen fallback policy')
    stages=[load(r) for r in execution.get('bond_plans',[])]
    choices=record['choices'];codes=list(choices)
    _need([r.get('component') for r in stages]==codes[:len(stages)],'Bond stages differ from discovered order')
    prepared=read_dictionary_bundle(root/'bundle')
    for stage in stages:
        code=stage['component']
        index=prepared['after_dictionaries'].index(prepared['component_dictionaries'][code])
        _need(stage.get('discovery')==ref and stage.get('requested_bonds')==choices[code]
              and stage.get('dictionary_index')==index
              and stage.get('reference_qualification')==record['proposals'][code]['reference_qualification'],
              'Bond stage differs from its frozen discovered choice')
    if record['status']=='DISCOVERED':
        _need([r.get('component') for r in execution.get('bond_results',[])]==codes[:len(stages)],
              'Discovery results differ from attempted stages')
        _need(len(stages)==len(codes) or 'optional_failure' in execution,
              'Discovered choices silently omitted')
    else:
        _need(not stages and execution.get('bond_results')==[
            dict(component=code,status='REFERENCE_UNAVAILABLE',library=record['library']) for code in eligible],
            'Unavailable discovery must retain all source-neighborhood outcomes')
