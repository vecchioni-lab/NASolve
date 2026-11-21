"""Recompute the mathematical diagnostic without changing scientific authority."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import pytest
from nasolve.cif_recovered_precision import (
    audit_recovered_precision, read_recovered_precision, inspect_declared_axis, REPORT, RESULT)


def parent_fixture(tmp_path, monkeypatch):
    from tests.test_cif_recovered_resolution import parent_fixture as make_torsions
    from nasolve.cif_recovered_resolution import audit_recovered_resolution
    *parents,sdk,phenix=make_torsions(tmp_path,monkeypatch)
    out=tmp_path/'c102';r=audit_recovered_resolution(*parents,phenix,out,timeout_seconds=30)
    assert r['status']=='RECOVERED_RESOLUTION_AUDIT_COMPLETE'
    raw=json.loads((parents[0]/'job/torsion_result.json').read_bytes())
    # Only the synthetic protocol fixture's explicit fake header is authorized.
    monkeypatch.setattr('nasolve.cif_recovered_precision.SUPPORTED_HEADER_SHA256',raw['installed_dihedral_sources'][0]['sha256'])
    return [out,*parents],sdk


def read(out, parents):
    return read_recovered_precision(out,resolution_directory=parents[0],torsion_directory=parents[1],
        geometry_directory=parents[2],gradient_directory=parents[3],recovery_directory=parents[4])


def test_saved_diagnostic_relocates_without_sdk_or_parent_mutation(tmp_path,monkeypatch):
    from tests.test_cif_mixed_torsion import parent_files
    parents,sdk=parent_fixture(tmp_path,monkeypatch);before=parent_files(*parents)
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Saved audit launched a process'))
    out=tmp_path/'precision';report=audit_recovered_precision(*parents,out)
    assert report['status']=='RECOVERED_PRECISION_DIAGNOSTIC_COMPLETE'
    assert report['new_native_calls']==0 and report['endpoint_requalification']=='NOT_RUN'
    assert report['coordinate_decision']['selected']=='verified_recovered_model'
    assert not report['automatic_adoption'] and report['candidate_preparation']=='NOT_RUN'
    assert all(p.read_bytes()==value for p,value in before.items())
    moved=tmp_path/'moved';moved.mkdir();new=[]
    for i,parent in enumerate(parents):parent.rename(moved/str(i));new.append(moved/str(i))
    out.rename(moved/'precision');out=moved/'precision'
    import shutil
    shutil.rmtree(sdk)
    assert read(out,new)==report


@pytest.mark.parametrize('defect',['summary','selection','new_calls_bool','schema_bool','reference','declaration','extra','parent_bytes','header'])
def test_replay_rejects_rebound_results_and_false_authority(tmp_path,monkeypatch,defect):
    from nasolve.cif_recovered_precision import _ref
    parents,_=parent_fixture(tmp_path,monkeypatch);out=tmp_path/'precision'
    report=audit_recovered_precision(*parents,out)
    if defect=='summary':report['summary']['decimal_audited_rows']+=1
    elif defect=='selection':report['coordinate_decision']['selected']='qualified_geometry_endpoint'
    elif defect=='new_calls_bool':report['new_native_calls']=False
    elif defect=='schema_bool':report['schema_version']=True
    elif defect=='extra':(out/'extra.json').write_text('{}')
    elif defect=='parent_bytes':
        p=parents[0]/'recovered_resolution_audit.json';p.write_bytes(p.read_bytes()+b' ')
    elif defect=='header':monkeypatch.setattr('nasolve.cif_recovered_precision.SUPPORTED_HEADER_SHA256','0'*64)
    else:
        p=out/RESULT;v=json.loads(p.read_bytes())
        if defect=='reference':
            row=next(r for r in v['rows'] if 'audit' in r)
            row['audit']['orders']['forward']['references'][-1]['target']='123'
        else:v['declarations'][0]['status']='DECLARED_LINEAR_ROW_MATCH'
        p.write_text(json.dumps(v));report['outputs']=[_ref(p,out)]
    (out/REPORT).write_text(json.dumps(report))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Reader launched'))
    with pytest.raises(ValueError):read(out,parents)


@pytest.mark.parametrize('mode',['existing','symlink','inside_parent'])
def test_previous_attempts_and_parent_directories_are_protected(tmp_path,mode):
    parents=[tmp_path/str(i) for i in range(5)]
    for p in parents:p.mkdir()
    target=tmp_path/'keep';target.mkdir();(target/'evidence').write_text('KEEP')
    if mode=='existing':out=target
    elif mode=='symlink':
        out=tmp_path/'alias';out.symlink_to(target,target_is_directory=True)
    else:out=parents[0]/'new'
    with pytest.raises(ValueError):audit_recovered_precision(*parents,out)
    assert (target/'evidence').read_text()=='KEEP'


def declaration_fixture(tmp_path):
    from tests.test_cif_linear_torsion_candidate import dictionary
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.cif_triple_bond_audit import _rows
    path,_=dictionary(tmp_path,'Q17');v=_values(path,'Q17')
    definition={}
    for category,label,count in [('bond','bonds',2),('angle','angles',3),('tor','torsions',4)]:
        rows=[]
        for raw in _rows(v,category,count):
            row={k:raw[k] for k in raw if k not in {'atoms','comp_id'}}
            row.update({'atom_id_'+str(i+1):n for i,n in enumerate(raw['atoms'])})
            for k in ['value_angle','value_angle_esd','value_dist','value_dist_esd','period']:
                if k in row:row[k]=float(row[k])
            if category=='bond':row['type']={'SING':'single','TRIP':'triple'}[row['value_order']]
            rows.append(row)
        definition[label]=rows
    proxy={'angle_ideal':20.,'weight':1/900,'periodicity':3}
    return v,definition,proxy


@pytest.mark.parametrize('reverse',[False,True])
def test_declaration_inspection_uses_graph_and_targets_without_writing_candidate(tmp_path,reverse):
    values,definition,proxy=declaration_fixture(tmp_path);before=deepcopy((values,definition,proxy))
    names=['L','X','Y','R'];names=names[::-1] if reverse else names
    r=inspect_declared_axis(values,names,definition,proxy)
    assert r['status']=='DECLARED_LINEAR_ROW_MATCH' and all(r['checks'].values())
    assert r['selection_coordinates']=='NOT_USED' and r['candidate_preparation']=='NOT_RUN'
    assert (values,definition,proxy)==before


@pytest.mark.parametrize('defect',['native_angle','native_bond','native_period','proxy_weight','duplicate_angle','bent_declaration','no_triple','bad_path'])
def test_changed_or_ambiguous_declarations_cannot_claim_match(tmp_path,defect):
    v,d,p=declaration_fixture(tmp_path);names=['L','X','Y','R']
    if defect=='native_angle':d['angles'][0]['value_angle']=179.
    elif defect=='native_bond':next(r for r in d['bonds'] if r['type']=='triple')['value_dist']+=.1
    elif defect=='native_period':d['torsions'][0]['period']=1
    elif defect=='proxy_weight':p['weight']*=2
    elif defect=='duplicate_angle':
        for k in list(v):
            if k.startswith('_chem_comp_angle.'):v[k].append(v[k][0])
    elif defect=='bent_declaration':v['_chem_comp_angle.value_angle'][0]='179'
    elif defect=='no_triple':v['_chem_comp_bond.value_order'][1]='SING'
    else:names[-1]='S'
    if defect in {'duplicate_angle','bent_declaration','bad_path'}:
        with pytest.raises(ValueError):inspect_declared_axis(v,names,d,p)
    else:
        r=inspect_declared_axis(v,names,d,p)
        assert r['status'] != 'DECLARED_LINEAR_ROW_MATCH'
