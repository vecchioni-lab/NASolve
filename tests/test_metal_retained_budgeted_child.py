"""Ordinary child admission borrows an actually owned and charged parent."""
from unittest.mock import patch
import pytest
from nasolve import campaign_records as records
from nasolve.metal import storage_budget as b,parent_archive as p,child_process as c
from nasolve.metal.recipe import RecipeError
from tests.test_metal_child_process import invoke,inventory
from tests.test_metal_parent_budget import configured,retain,budget


def child_options(options):
    return {k:v for k,v in dict(options,allowance_bytes=1_000_000).items() if k!='scope'}


def test_serial_children_charge_parent_once_and_reopen_exact_results(tmp_path):
    values,options=configured(tmp_path);materialize=p.materialized_parent_inputs
    with patch.object(p,'materialized_parent_inputs',wraps=materialize) as expanded:
        with retain(values,options) as retained:
            info=retained.storage_budget;results=[]
            for name in ('first','second'):
                result=invoke(tmp_path,values,name,retained_parent=retained,storage_budget=child_options(options))
                results.append(result)
                assert result['status']=='COMPLETED' and result['storage_budget']['state']=='SETTLED'
                assert budget(options)['outstanding_by_scope']=={'retained_parent':options['allowance_bytes'],'child':0}
                record=records.read_record(tmp_path/name/'storage-admission.json')
                assert record['schema_version']==2 and record['grant']['parent_reservation_id']==info['reservation_id']
                assert record['parent_scope']==result['outcome']['parent_scope']
                assert record['parent_scope']['scope_id']==retained.scope_id
            assert expanded.call_count==1
    assert info['state']=='SETTLED' and budget(options)['outstanding_bytes']==0
    before=inventory(tmp_path)
    moved=tmp_path.with_name(tmp_path.name+'-'+info['reservation_id'][:12]+'-moved');tmp_path.rename(moved)
    assert not tmp_path.exists() and inventory(moved)==before
    assert b.inspect_budget(moved,budget_id=options['budget_id'])['settled_count']==3
    for name,result in zip(('first','second'),results):
        reopened=c.inspect_child(moved/name,request_id=values[2]['request_id'])
        assert reopened['outcome']==result['outcome']


@pytest.mark.parametrize('mode',['uncertain','missing-outcome','prelaunch-interrupt'])
def test_failed_child_keeps_own_charge_after_parent_closes(tmp_path,mode):
    values,options=configured(tmp_path);write=records.write_record
    def interrupted(path,value,**kwargs):
        if path.name=='outcome.json':raise OSError('Missing outcome')
        return write(path,value,**kwargs)
    target='nasolve.campaign_process._group_alive' if mode=='uncertain' else 'nasolve.campaign_records.write_record' if mode=='missing-outcome' else 'nasolve.metal.child_process.ChildProcesses'
    kwargs={'return_value':None} if mode=='uncertain' else {'side_effect':interrupted if mode=='missing-outcome' else OSError('Interrupted owner')}
    with retain(values,options) as retained:
        info=retained.storage_budget
        with patch(target,**kwargs):
            if mode=='uncertain':
                result=invoke(tmp_path,values,retained_parent=retained,storage_budget=child_options(options))
                assert result['status']=='STOP_UNCERTAIN' and result['storage_budget']['state']=='HELD'
            else:
                with pytest.raises(OSError):invoke(tmp_path,values,retained_parent=retained,storage_budget=child_options(options))
        assert budget(options)['outstanding_bytes']==options['allowance_bytes']+1_000_000
    assert info['state']=='SETTLED' and budget(options)['outstanding_by_scope']=={'retained_parent':0,'child':1_000_000}
    assert (tmp_path/'attempt/storage-admission.json').exists()


@pytest.mark.parametrize('defect',['unbudgeted-parent','wrong-store','substituted-info','changed-opening','opening-version','declaration-version','too-small','no-capacity'])
def test_retained_child_denial_precedes_new_read_or_launch(tmp_path,defect):
    values,options=configured(tmp_path)
    outer=p.retained_parent_inputs(values[1],values[2]['parent_manifest_sha256']) if defect=='unbudgeted-parent' else retain(values,options)
    with outer as retained:
        choice=child_options(options);restore=None
        if defect=='wrong-store':
            other=tmp_path/'foreign';other.mkdir();cfg=b.create_budget(other,quota_bytes=1024**3,free_space_reserve_bytes=0,include_retained_parents=True)
            choice.update(directory=other,budget_id=cfg['record_sha256'])
        elif defect=='substituted-info':
            restore=retained.storage_budget;retained.storage_budget=dict(restore,reservation_id='0'*64)
        elif defect in {'changed-opening','opening-version','declaration-version'}:
            path=tmp_path/'parent-one'/('declaration.json' if defect=='declaration-version' else 'opened.json')
            restore=path.read_bytes();changed=records.read_record(path)
            if defect=='changed-opening':changed['parent_scope']['scope_id']='0'*64
            else:changed['schema_version']=99
            records.write_record(path,changed,replace=True)
            if defect=='declaration-version':
                opening=tmp_path/'parent-one/opened.json';opening_restore=opening.read_bytes();value=records.read_record(opening)
                value['declaration_id']=records.read_record(path)['record_sha256'];records.write_record(opening,value,replace=True)
        elif defect=='too-small':choice['allowance_bytes']=1
        elif defect=='no-capacity':choice['allowance_bytes']=2*1024**3
        before=budget(options)['held_count']
        try:
            with patch.object(p,'read_parent_inputs',side_effect=AssertionError('No new read')),patch('subprocess.Popen',side_effect=AssertionError('No launch')):
                with pytest.raises((RecipeError,ValueError)):
                    invoke(tmp_path,values,retained_parent=retained,storage_budget=choice)
            assert not (tmp_path/'attempt').exists() and budget(options)['held_count']==before
        finally:
            if defect=='substituted-info':retained.storage_budget=restore
            elif defect in {'changed-opening','opening-version','declaration-version'}:
                path.write_bytes(restore)
                if defect=='declaration-version':opening.write_bytes(opening_restore)
