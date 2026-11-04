"""Saved-evidence precision and declaration audit after C102; no native job."""
from copy import deepcopy
from pathlib import Path

from . import cif_recovered_resolution as resolution
from . import cif_recovered_torsion as torsion
from . import cif_mixed_source_recovery as recovery
from . import cif_torsion_precision as precision
from . import cif_linear_torsion_candidate as linear
from .cif_triple_bond_audit import _key, _rows, _numeric
from .cif_stereochemistry_audit import _values, _graph
from .cif_mixed_torsion import _bytes

POLICY_ID = 'cif-recovered-independent-torsion-precision-v1'
REPORT = 'recovered_precision_audit.json'
RESULT = 'precision_result.json'
ANCHOR = 'recovered_precision_directory'
RESOLUTION_ANCHOR = 'recovered_resolution_directory'
# The mathematical function was inspected in this recorded native header.
# An unfamiliar implementation requires a new, explicit method review.
SUPPORTED_HEADER_SHA256 = '4f006d773127bb1fb4134bc5ce6aec6a7038f5fd0ef7466dc7ebd9d1e9683c48'
_load, _dump, _need = torsion._load, torsion._dump, precision._need


def _ref(path, root, anchor=ANCHOR):
    return torsion._ref(path, root, anchor)


def inspect_declared_axis(values, names, definition, proxy):
    """Check one row against existing declaration prerequisites, without editing.

    This deliberately makes no complete-candidate or native-delta claim.
    """
    result = {'policy_id':linear.POLICY_ID,'scope':'ONE_CURRENT_DICTIONARY_ROW_AND_EFFECTIVE_DEFINITION',
              'selection_coordinates':'NOT_USED','candidate_preparation':'NOT_RUN','automatic_adoption':False}
    elements, orders, _, neighbors = _graph(values)
    if 'TRIPLE' not in orders.values():
        return {**result,'status':'NOT_SELECTED_BY_DECLARATIONS'}
    angles, _ = linear._linear_triples(values)
    matched = [row for row in angles if _key(row['atoms']) in {_key(names[:3]),_key(names[1:])}]
    if not matched:
        return {**result,'status':'NOT_SELECTED_BY_DECLARATIONS'}
    _need(len(set(names)) == 4 and all(n in neighbors for n in names)
          and all(b in neighbors[a] for a,b in zip(names,names[1:])))
    linear._columns(values,linear.T,['comp_id','id','atom_id_1','atom_id_2','atom_id_3','atom_id_4','value_angle','value_angle_esd','period'])
    source = [row for row in _rows(values,'tor',4) if _key(row['atoms']) == _key(names)]
    _need(len(source) == 1)
    source = source[0]
    target, esd, period = [_numeric(source.get(k)) for k in ['value_angle','value_angle_esd','period']]
    _need(target is not None and esd is not None and esd > 0 and period is not None and period >= 0 and period == int(period))
    native = [row for row in definition['torsions'] if _key([row['atom_id_'+str(i)] for i in range(1,5)]) == _key(names)]
    _need(len(native) == 1)
    native = native[0]
    checks = {'torsion_target':native['value_angle'] == target == proxy['angle_ideal'],
              'torsion_esd':native['value_angle_esd'] == esd and proxy['weight'] == 1/(esd*esd),
              'torsion_period':native['period'] == period == proxy['periodicity']}
    native_angles, native_bonds = [], []
    for i,row in enumerate(matched):
        found = [r for r in definition['angles'] if _key([r['atom_id_'+str(j)] for j in range(1,4)]) == _key(row['atoms'])]
        _need(len(found) == 1); native_angles.append(found[0])
        checks['linear_angle_'+str(i)] = (found[0]['value_angle'] == 180. and
            found[0]['value_angle_esd'] == _numeric(row['declared_angle']['value_angle_esd']))
    for i,pair in enumerate(sorted({_key(r['triple_bond']) for r in matched})):
        native_rows = [r for r in definition['bonds'] if _key([r['atom_id_1'],r['atom_id_2']]) == pair]
        dictionary_rows = [r for r in _rows(values,'bond',2) if _key(r['atoms']) == pair]
        _need(len(native_rows) == len(dictionary_rows) == 1); native_bonds.append(native_rows[0])
        a,b = native_rows[0],dictionary_rows[0]
        checks['triple_bond_'+str(i)] = (str(a['type']).upper() in {'TRIP','TRIPLE'} and
            a['value_dist'] == _numeric(b.get('value_dist')) and
            a['value_dist_esd'] == _numeric(b.get('value_dist_esd')))
    return {**result,'status':'DECLARED_LINEAR_ROW_MATCH' if all(checks.values()) else 'DECLARATION_REVIEW',
            'checks':checks,'source_torsion':source,'native_torsion':native,
            'declared_linear_angles':matched,'native_angles':native_angles,'native_triple_bonds':native_bonds}


def _declaration(expected, proxy, dictionary_values):
    atoms = [expected['atoms'][i] for i in proxy['i_seqs']]
    identities = [a['identity'] for a in atoms]
    identity = identities[0]
    if any(i != identity for i in identities):
        return {'status':'UNASSESSED_CROSS_RESIDUE','candidate_preparation':'NOT_RUN'}
    component = identity['resname'].strip()
    matching = [(ref,path) for ref,path,codes in dictionary_values if component in codes]
    # Modified dictionary blocks are deliberately not treated as base sources.
    mappings = [r for r in expected['monomer_mappings']['rows'] if all(
        str(r.get('literal_identity',{}).get(k,'')).strip() == str(identity.get(k,'')).strip()
        for k in ['model_id','chain_id','resseq','icode','altloc','resname'])]
    if len(matching) != 1 or len(mappings) != 1:
        return {'status':'UNASSESSED_AMBIGUOUS_SOURCE_OR_SITE','component':component,'candidate_preparation':'NOT_RUN'}
    ref,path = matching[0]
    names = [a['atom_id'] for a in atoms]
    try:
        result = inspect_declared_axis(_values(path,component),names,mappings[0]['metadata']['effective_definition'],proxy)
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        result = {'status':'DECLARATION_REVIEW','finding_type':type(exc).__name__,
                  'finding':str(exc),'candidate_preparation':'NOT_RUN','automatic_adoption':False}
    return {**result,'component':component,'site':mappings[0]['site'],'atom_names':names,'dictionary':ref}


def _inputs(resolution_dir, torsions, geometry, gradient, parent):
    source = resolution.read_recovered_resolution(resolution_dir,torsion_directory=torsions,
        geometry_directory=geometry,gradient_directory=gradient,recovery_directory=parent)
    _need(source['status'] == 'RECOVERED_RESOLUTION_AUDIT_COMPLETE')
    raw = _load(torsions/'job/torsion_result.json')
    headers = raw['installed_dihedral_sources']
    _need(len([r for r in headers if r['path']=='dihedral.h' and r['status']=='RECORDED'
               and r['sha256']==SUPPORTED_HEADER_SHA256]) == 1)
    spec = _load(torsions/'job/torsion_spec.json')
    expected = _load(torsions/'job/expected_inventory.json')
    recorded = _load(torsions/torsion.REPORT)
    _need(_ref(torsions/torsion.REPORT,torsions,resolution.TORSION_ANCHOR)==source['inputs']['torsion_report']
          and _ref(torsions/'job/torsion_result.json',torsions,resolution.TORSION_ANCHOR)==source['inputs']['torsion_result'])
    for name in ['job/torsion_spec.json','job/expected_inventory.json']:
        _need(_ref(torsions/name,torsions,torsion.ANCHOR) in recorded['outputs'])
    bindings = {**deepcopy(source['inputs']),
                'resolution_report':_ref(resolution_dir/resolution.REPORT,resolution_dir,RESOLUTION_ANCHOR),
                'torsion_spec':_ref(torsions/'job/torsion_spec.json',torsions,resolution.TORSION_ANCHOR)}
    return source,raw,spec,expected,bindings


def _analyze(source, raw, spec, expected, bindings, parent):
    from .ligand_profiles import _blocks
    dictionaries=[]
    for ref in bindings['dictionaries']:
        path = recovery._resolve(parent,ref)
        codes={c for b in _blocks(path) for c in b.values.get('_chem_comp_atom.comp_id',[])}
        dictionaries.append((ref,path,codes))
    selected=spec['selection']['selected'];_need(1<=len(selected)<=8)
    declarations=[_declaration(expected,r['proxy'],dictionaries) for r in selected]
    rows=[]
    for case in ['initial','full_precision','pdb_rounded']:
        points=spec['coordinate_cases'][case]
        records=raw['audit']['cases'][case]['proxies'];_need(len(records)==len(selected)==len(raw['selected_native_parameters']))
        for index,(selection,record,native) in enumerate(zip(selected,records,raw['selected_native_parameters'])):
            proxy=selection['proxy'];_need(record['proxy']==proxy and all(native[k]==v for k,v in proxy.items()))
            row={'case':case,'selection_index':index,'proxy':proxy,
                 'atom_labels':[expected['atoms'][i]['label'] for i in proxy['i_seqs']],
                 'selection_reason':selection['selection_reason']}
            if proxy['alt_angle_ideals'] not in (None,[]) or proxy['periodicity']<=0:
                rows.append({**row,'status':'UNASSESSED_UNSUPPORTED_FUNCTION'});continue
            local=[points[i] for i in proxy['i_seqs']]
            audit=precision.audit_precision(local,native,{order:v['baseline'] for order,v in record['orders'].items()})
            rows.append({**row,'status':audit['status'],'audit':audit})
    audited=[r for r in rows if r['status']=='DECIMAL_DIAGNOSTIC_COMPLETE']
    comparisons=[{'case':r['case'],'selection_index':r['selection_index'],'order':order,'kernel':kind,
                  'maximum_absolute_difference':value['gradient']['maximum_absolute_difference']}
                 for r in audited for order,values in r['audit']['native_comparisons'].items()
                 for kind,value in values.items() if not value['gradient_consistent']]
    summary={'selected_proxies':len(selected),'case_proxy_rows':len(rows),'decimal_audited_rows':len(audited),
             'unassessed_rows':sum(r['status'].startswith('UNASSESSED') for r in rows),
             'undefined_rows':sum(r['status']=='UNDEFINED_COLLINEAR' for r in rows),
             'supported_reference_controls_pass':len(audited)>0 and all(
                 r['audit']['precision_stable'] and r['audit']['reversal_consistent'] and r['audit']['finite_differences_consistent'] for r in audited),
             'native_strict_gradient_disagreements':comparisons,
             'declared_linear_row_matches':sum(r['status']=='DECLARED_LINEAR_ROW_MATCH' for r in declarations),
             'endpoint_requalification':'NOT_RUN','automatic_adoption':False}
    return {'schema_version':1,'policy_id':POLICY_ID,'rows':rows,'declarations':declarations,'summary':summary,
            'method':{'reference_policy':precision.POLICY_ID,'precisions':list(precision.PRECISIONS),
                      'steps':list(precision.STEPS),'input_values':'EXACT_BINARY64_VALUES; DECIMAL_FROM_FLOAT',
                      'energy':'9600 * weight / n^2 * (1 - cos(n * (model - ideal)))',
                      'gradient':'FORWARD_AUTOMATIC_DIFFERENTIATION_OF_NORMALIZED_PLANE_NORMAL_EXPRESSION',
                      'pi':'MACHIN_IDENTITY_AT_WORKING_PRECISION; NOT_BINARY64_OPERATION_EMULATION',
                      'native_header_sha256':SUPPORTED_HEADER_SHA256,'historical_native_sources':raw['installed_sources'],
                      'native_header_records':raw['installed_dihedral_sources']},
            'inherited_resolution_summary':source['summary'],
            'limitations':['The reference tests the mathematical periodic function, not native floating-point operation ordering.',
                'Strict native comparisons use the existing 1e-8/1e-10 comparison; original derivative thresholds are unchanged.',
                'Decimal finite differences do not reclassify binary64 samples or qualify the full objective.',
                'Alternate ideals and nonpositive periodicities are explicitly unassessed.',
                'Row declaration matches do not prepare a complete candidate or prove any native omission delta.']}


def _report(source, bindings, result, output_ref):
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'RECOVERED_PRECISION_DIAGNOSTIC_COMPLETE',
            'inputs':bindings,'outputs':[output_ref],'summary':result['summary'],
            'coordinate_decision':deepcopy(source['coordinate_decision']),
            'original_geometry_qualification':deepcopy(source['original_geometry_qualification']),
            'source_chemical_findings':source['source_chemical_findings'],
            'new_native_calls':0,'captured_code_execution':'NOT_RUN','dictionary_generation':'NOT_RUN',
            'candidate_preparation':'NOT_RUN','model_optimization':'NOT_RUN','endpoint_requalification':'NOT_RUN',
            'scientific_qualification':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False,
            'policy_authority':'NARestraints'}


def audit_recovered_precision(resolution_directory,torsion_directory,geometry_directory,gradient_directory,recovery_directory,output):
    """Create a fresh mathematical diagnostic using only validated saved data."""
    parents=list(map(Path,(resolution_directory,torsion_directory,geometry_directory,gradient_directory,recovery_directory)))
    root=Path(output).absolute()
    _need(not root.exists() and not any(p.is_symlink() for p in [root,*root.parents])
          and not any(root.resolve().is_relative_to(p.resolve()) for p in parents))
    source,raw,spec,expected,bindings=_inputs(*parents)
    result=_analyze(source,raw,spec,expected,bindings,parents[-1])
    root.mkdir(parents=True);_dump(root/RESULT,result)
    report=_report(source,bindings,result,_ref(root/RESULT,root));_dump(root/REPORT,report)
    return report


def read_recovered_precision(directory,*,resolution_directory,torsion_directory,geometry_directory,gradient_directory,recovery_directory):
    """Recompute every reference and declaration without native code or edits."""
    from .cif_mixed_recovery import _safe
    root=Path(directory);parents=list(map(Path,(resolution_directory,torsion_directory,geometry_directory,gradient_directory,recovery_directory)))
    try:
        _need(not any(p.is_symlink() for p in [root,*root.parents,*root.rglob('*')]))
        report=_load(root/REPORT)
        _need(set(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())=={REPORT,RESULT})
        _need(report['outputs']==[_ref(root/RESULT,root)] and _safe(report['outputs'][0]['path']))
        source,raw,spec,expected,bindings=_inputs(*parents)
        result=_analyze(source,raw,spec,expected,bindings,parents[-1])
        _need(_bytes(_load(root/RESULT))==_bytes(result)
              and _bytes(report)==_bytes(_report(source,bindings,result,_ref(root/RESULT,root))))
        return report
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete recovered precision report') from exc
