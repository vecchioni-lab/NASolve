"""Distinguish one source-proven native resource query from unknown child calls.

This is a scoped call classification, not instrumentation of child completion or
all native internals. It does not execute source snapshots or shell commands.
"""
import ast
from hashlib import sha256
from pathlib import Path

POLICY_ID='cif-readyset-native-resource-query-v1'
RESOURCE_MODULES=('libtbx/easy_run.py','libtbx/introspection.py','scitbx/cubicle_neighbors.py')
MAC_MEMORY_COMMAND='DYLD_LIBRARY_PATH=  exec /usr/sbin/system_profiler SPHardwareDataType'


def _name(node):
    if isinstance(node,ast.Name):return node.id
    if isinstance(node,ast.Attribute):return _name(node.value)+'.'+node.attr
    return ''


def _one(values):
    if len(values)!=1:raise ValueError('Native resource-query source shape differs')
    return values[0]


def _calls(node,name):
    return [n for n in ast.walk(node) if isinstance(n,ast.Call) and _name(n.func)==name]


def _proof(sources,directory,installation,library):
    trees={};fingerprints=[]
    for module in RESOURCE_MODULES:
        relative=str(Path(library)/module)
        row=_one([v for v in sources['sources'] if v['path']==relative])
        ref=row['snapshot'];name=ref['path']
        if (ref.get('anchor')!='readyset_audit_directory' or not isinstance(name,str)
                or name.startswith('/') or ':' in name or '\\' in name or any(p in {'','.','..'} for p in name.split('/'))):
            raise ValueError('Unsafe native resource-query snapshot')
        path=Path(directory)/name
        if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Unsafe native resource-query snapshot')
        data=path.read_bytes()
        if row.get('anchor')!='phenix_installation' or len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Native resource-query snapshot differs')
        trees[module]=ast.parse(data.decode('utf-8'));fingerprints.append({k:row[k] for k in ['anchor','path','size','sha256']})
    intro=trees['libtbx/introspection.py']
    query=_one([n for n in intro.body if isinstance(n,ast.FunctionDef) and n.name=='get_mac_os_x_memory_total'])
    cmd=_one([n for n in ast.walk(query) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cmd' for t in n.targets)])
    if not isinstance(cmd.value,ast.Constant) or cmd.value.value!='/usr/sbin/system_profiler':raise ValueError('Native resource-query program differs')
    buffered=_one(_calls(query,'easy_run.fully_buffered'))
    if buffered.args or len(buffered.keywords)!=1 or buffered.keywords[0].arg!='command':raise ValueError('Native resource-query arguments differ')
    value=buffered.keywords[0].value
    if not (isinstance(value,ast.BinOp) and isinstance(value.op,ast.Add) and _name(value.left)=='cmd'
            and isinstance(value.right,ast.Constant) and value.right.value==' SPHardwareDataType'):
        raise ValueError('Native resource-query arguments differ')
    memory=_one([n for n in intro.body if isinstance(n,ast.ClassDef) and n.name=='machine_memory_info'])
    initializer=_one([n for n in memory.body if isinstance(n,ast.FunctionDef) and n.name=='__init__'])
    get_memory=_one(_calls(initializer,'get_mac_os_x_memory_total'))
    easy=trees['libtbx/easy_run.py']
    wrapper=_one([n for n in easy.body if isinstance(n,ast.ClassDef) and n.name=='fully_buffered_subprocess'])
    wrapper_init=_one([n for n in wrapper.body if isinstance(n,ast.FunctionDef) and n.name=='__init__'])
    popen=_one(_calls(wrapper_init,'subprocess.Popen'))
    keywords={v.arg:v.value for v in popen.keywords}
    if popen.args or _name(keywords.get('args'))!='command' or _name(keywords.get('shell'))!='use_shell_in_subprocess':
        raise ValueError('Native process wrapper differs')
    neighbors=trees['scitbx/cubicle_neighbors.py']
    grid=_one([n for n in neighbors.body if isinstance(n,ast.FunctionDef) and n.name=='__cubicles_max_memory_allocation_set'])
    machine=_one(_calls(grid,'machine_memory_info'))
    invoke=_one([n.value for n in neighbors.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
        and _name(n.value.func)=='__cubicles_max_memory_allocation_set'])
    def role(module,function,node):
        return {'source':str(Path(installation)/library/module),'function':function,'first_line':node.lineno,'last_line':node.end_lineno}
    return [role('libtbx/easy_run.py','__init__',popen),role('libtbx/introspection.py',query.name,buffered),
        role('libtbx/introspection.py','__init__',get_memory),role('scitbx/cubicle_neighbors.py',grid.name,machine),
        role('scitbx/cubicle_neighbors.py','<module>',invoke)],fingerprints


def classify_subprocesses(trace,sources,directory,installation,library):
    """Recognize the exact resource query only with verified native caller spans."""
    total=trace.get('subprocess_calls');events=[v for v in trace.get('events',[]) if v.get('kind')=='subprocess']
    complete=(type(total) is int and total>=0 and total==len(events) and trace.get('truncated') is False
        and trace.get('process_observation_schema_version')==1)
    result={'policy_id':POLICY_ID,'complete':complete,'recognized_resource_queries':0,
        'unclassified_subprocess_calls':0,'events':[],'source_fingerprints':[],
        'scope':'EXACT_CCTBX_MAC_MEMORY_QUERY_CALL; NO_CHILD_COMPLETION_OR_EXHAUSTIVE_NATIVE_INTERNALS_PROOF'}
    roles=[]
    if events:
        try:roles,result['source_fingerprints']=_proof(sources,directory,installation,library)
        except (ValueError,KeyError,TypeError,SyntaxError,UnicodeError,OSError) as exc:result['source_review']=str(exc)
    for index,event in enumerate(events):
        p=event.get('process',{});callers=p.get('callers',[])
        known=(bool(roles) and complete and event.get('function')=='__init__'
            and p.get('args')==MAC_MEMORY_COMMAND and p.get('shell') is True
            and p.get('executable') is None and p.get('cwd') is None
            and p.get('parameters_complete') is True and p.get('truncated') is False
            and p.get('environment')=='NOT_CAPTURED' and len(callers)>=len(roles)
            and all(v.get('source')==r['source'] and v.get('function')==r['function'] and type(v.get('line')) is int
                and r['first_line']<=v['line']<=r['last_line'] for v,r in zip(callers,roles)))
        result['events'].append({'event_index':index,'classification':'CCTBX_MAC_MEMORY_QUERY' if known else 'UNCLASSIFIED_SUBPROCESS',
            'caller_prefix_complete':bool(known),'full_caller_stack_truncated':p.get('callers_truncated')})
        result['recognized_resource_queries' if known else 'unclassified_subprocess_calls']+=1
    if not complete:result['unclassified_subprocess_calls']=max(1,result['unclassified_subprocess_calls'],total if type(total) is int else 1)
    result['accepted']=complete and result['unclassified_subprocess_calls']==0
    return result
