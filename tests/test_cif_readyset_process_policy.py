from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import pytest
from tests.test_cif_postmr_readyset import setup


def install_query_fixture(installation):
    site=installation.root/'lib/python3.11/site-packages'
    sources={
        'libtbx/__init__.py':'',
        'libtbx/easy_run.py':'''import subprocess
class fully_buffered_subprocess:
    def __init__(self, command, use_shell_in_subprocess=True):
        command='DYLD_LIBRARY_PATH=  exec '+command
        self.stdout_lines=[]
        process=subprocess.Popen(args=command,shell=use_shell_in_subprocess,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        process.communicate()
fully_buffered=fully_buffered_subprocess
''',
        'libtbx/introspection.py':'''from libtbx import easy_run
def get_mac_os_x_memory_total():
    cmd='/usr/sbin/system_profiler'
    for line in easy_run.fully_buffered(command=cmd+' SPHardwareDataType').stdout_lines:
        pass
    return None
class machine_memory_info:
    def __init__(self):
        self.memory=get_mac_os_x_memory_total()
    def memory_total(self):return self.memory
''',
        'scitbx/__init__.py':'',
        'scitbx/cubicle_neighbors.py':'''from libtbx.introspection import machine_memory_info
def __cubicles_max_memory_allocation_set():
    memory=machine_memory_info().memory_total()
__cubicles_max_memory_allocation_set()
'''}
    for name,data in sources.items():
        path=site/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
    ready=site/'elbow/command_line/ready_set.py'
    ready.write_text('from scitbx import cubicle_neighbors\n'+ready.read_text())
    return site


def observed_control(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    source,dictionary,model,installation,consumer=setup(tmp_path,monkeypatch)
    site=install_query_fixture(installation)
    report=audit_readyset_consumption(source,dictionary,model,'Q17',installation,consumer,tmp_path/'control')
    return report,installation,site


def test_known_native_memory_query_is_separate_from_chemistry_processes(tmp_path,monkeypatch):
    report,installation,site=observed_control(tmp_path,monkeypatch)
    assert report['status']=='READYSET_CACHED_INPUT_PASS'
    assert report['trace']['subprocess_calls']==1 and report['trace']['builder_calls']==0
    assert report['checks']['no_unclassified_subprocess_calls'] is True and all(report['checks'].values())
    classified=report['process_classification']
    assert classified['recognized_resource_queries']==1 and classified['unclassified_subprocess_calls']==0
    assert classified['events'][0]['classification']=='CCTBX_MAC_MEMORY_QUERY'
    assert classified['events'][0]['caller_prefix_complete'] is True
    assert report['trace']['argument_overrides']=='NONE'


@pytest.mark.parametrize('defect',['extra_command','other_program','other_argument','nonempty_dyld','non_shell',
    'explicit_shell','cwd','incomplete_parameters','truncated_parameters','missing_prefix','wrong_function',
    'wrong_source','wrong_line','missing_event','extra_child','truncated_trace','changed_snapshot','escaped_snapshot','no_sources'])
def test_memory_query_requires_exact_command_and_verified_native_callers(tmp_path,monkeypatch,defect):
    from nasolve.cif_readyset_process_policy import classify_subprocesses
    report,installation,site=observed_control(tmp_path,monkeypatch)
    trace=deepcopy(report['trace']);sources=deepcopy(report['source_evidence']);event=trace['events'][0];process=event['process']
    if defect=='extra_command':process['args']+='; phenix.elbow unwanted'
    if defect=='other_program':process['args']=process['args'].replace('/usr/sbin/system_profiler','/tmp/system_profiler')
    if defect=='other_argument':process['args']=process['args'].replace('SPHardwareDataType','SPSoftwareDataType')
    if defect=='nonempty_dyld':process['args']=process['args'].replace('DYLD_LIBRARY_PATH= ','DYLD_LIBRARY_PATH=/tmp ')
    if defect=='non_shell':process['shell']=False
    if defect=='explicit_shell':process['executable']='/bin/sh'
    if defect=='cwd':process['cwd']='/tmp'
    if defect=='incomplete_parameters':process['parameters_complete']=False
    if defect=='truncated_parameters':process['truncated']=True
    if defect=='missing_prefix':process['callers']=process['callers'][:3]
    if defect=='wrong_function':process['callers'][1]['function']='build_dictionary'
    if defect=='wrong_source':process['callers'][1]['source']='/tmp/libtbx/introspection.py'
    if defect=='wrong_line':process['callers'][1]['line']=1
    if defect=='missing_event':trace['events']=[]
    if defect=='extra_child':trace['subprocess_calls']=2;trace['events'].append({'kind':'subprocess','function':'__init__','source':'elsewhere'})
    if defect=='truncated_trace':trace['truncated']=True
    if defect in {'changed_snapshot','escaped_snapshot'}:
        row=next(v for v in sources['sources'] if v['path'].endswith('/libtbx/introspection.py'))
        if defect=='changed_snapshot':(tmp_path/'control/source_evidence'/row['snapshot']['path']).write_text('CHANGED')
        else:row['snapshot']['path']='../outside.py'
    if defect=='no_sources':sources['sources']=[]
    result=classify_subprocesses(trace,sources,tmp_path/'control/source_evidence',installation.root,site.relative_to(installation.root))
    assert result['accepted'] is False
    assert result['unclassified_subprocess_calls']>0 or result['complete'] is False


def test_literal_memory_query_from_another_caller_still_requires_review(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import audit_readyset_consumption
    source,dictionary,model,installation,consumer=setup(tmp_path,monkeypatch)
    site=install_query_fixture(installation)
    ready=site/'elbow/command_line/ready_set.py'
    ready.write_text(ready.read_text().replace('from scitbx import cubicle_neighbors\n','').replace("print('No unknown residues')",
        "from libtbx import easy_run; easy_run.fully_buffered(command='/usr/sbin/system_profiler SPHardwareDataType'); print('No unknown residues')"))
    report=audit_readyset_consumption(source,dictionary,model,'Q17',installation,consumer,tmp_path/'control')
    assert report['status']=='REVIEW' and report['process_classification']['unclassified_subprocess_calls']==1


def test_prefix_can_be_complete_when_deeper_import_frames_are_truncated(tmp_path,monkeypatch):
    from nasolve.cif_readyset_process_policy import classify_subprocesses
    report,installation,site=observed_control(tmp_path,monkeypatch)
    trace=deepcopy(report['trace']);trace['events'][0]['process']['callers_truncated']=True
    result=classify_subprocesses(trace,report['source_evidence'],tmp_path/'control/source_evidence',installation.root,site.relative_to(installation.root))
    assert result['accepted'] and result['recognized_resource_queries']==1


@pytest.mark.parametrize('defect',['program','argument','constructor','wrapper','grid'])
def test_matching_paths_and_hashes_are_not_sufficient_without_source_shape(tmp_path,monkeypatch,defect):
    from nasolve.cif_readyset_process_policy import classify_subprocesses
    report,installation,site=observed_control(tmp_path,monkeypatch);sources=deepcopy(report['source_evidence'])
    suffix={'program':'libtbx/introspection.py','argument':'libtbx/introspection.py','constructor':'libtbx/introspection.py',
        'wrapper':'libtbx/easy_run.py','grid':'scitbx/cubicle_neighbors.py'}[defect]
    row=next(v for v in sources['sources'] if v['path'].endswith('/'+suffix))
    path=tmp_path/'control/source_evidence'/row['snapshot']['path'];text=path.read_text()
    before,after={
        'program':("cmd='/usr/sbin/system_profiler'","cmd='/tmp/system_profiler'"),
        'argument':("cmd+' SPHardwareDataType'","cmd+' SPSoftwareDataType'"),
        'constructor':('self.memory=get_mac_os_x_memory_total()','self.memory=0'),
        'wrapper':('shell=use_shell_in_subprocess','shell=True'),
        'grid':('memory=machine_memory_info().memory_total()','memory=0')}[defect]
    assert text.count(before)==1;path.write_text(text.replace(before,after))
    data=path.read_bytes();row['size']=len(data);row['sha256']=sha256(data).hexdigest()
    result=classify_subprocesses(report['trace'],sources,tmp_path/'control/source_evidence',installation.root,site.relative_to(installation.root))
    assert not result['accepted'] and result['unclassified_subprocess_calls']==1


def test_legacy_readback_retains_its_original_strict_policy_and_review(tmp_path,monkeypatch):
    from nasolve.cif_postmr_readyset import read_readyset_consumption,LEGACY_POLICY_ID
    report,installation,site=observed_control(tmp_path,monkeypatch)
    legacy=deepcopy(report);legacy['policy_id']=LEGACY_POLICY_ID;legacy['status']='REVIEW'
    legacy['checks'].pop('no_unclassified_subprocess_calls');legacy['checks']['no_observed_subprocess_calls']=False
    legacy.pop('process_classification')
    (tmp_path/'control/readyset_consumption.json').write_text(json.dumps(legacy))
    assert read_readyset_consumption(tmp_path/'control')['report']==legacy
