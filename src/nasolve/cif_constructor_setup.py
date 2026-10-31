"""Explicit native input-coordinate setup for the isolated constructor diagnostic.

Use the installed builder's preparation method, not replacement chiral targets.
This does not execute the complete builder or certify assembled stereochemistry.
"""
from inspect import getsource
import math

POLICY_ID='cif-native-input-coordinate-setup-v1'
REFERENCE_PATH='elbow/command_line/builder.py'


def native_setup_reference(text):
    """Recognize an unconditional same-object Setup preceding Chiralise."""
    import ast
    tree=ast.parse(text);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='builder']
    if len(functions)!=1:raise ValueError('Missing native builder setup reference')
    body=functions[0].body
    def call(s,name):
        return (isinstance(s,ast.Expr) and isinstance(s.value,ast.Call) and isinstance(s.value.func,ast.Attribute)
            and isinstance(s.value.func.value,ast.Name) and s.value.func.value.id=='molecule' and s.value.func.attr==name)
    setups=[(i,s) for i,s in enumerate(body) if call(s,'Setup')]
    constructors=[(i,s) for i,s in enumerate(body) if call(s,'Chiralise')]
    if len(setups)!=1 or not constructors:raise ValueError('Unsupported native builder setup sequence')
    i,s=setups[0];j,c=constructors[0]
    if i>=j or s.value.args or s.value.keywords or any(isinstance(n,ast.Name) and n.id=='molecule' and isinstance(n.ctx,ast.Store)
            for statement in body[i+1:j] for n in ast.walk(statement)):
        raise ValueError('Unsupported native builder setup reference')
    return {'function':'builder','setup_line':s.lineno,'constructor_line':c.lineno,'arguments':[]}


def input_coordinate_snapshot(molecule):
    """Capture cache values rather than relying on their attribute presence."""
    import math
    rows=[]
    for atom in molecule:
        value=getattr(atom,'input_xyz',None)
        try:
            xyz=[float(value.x),float(value.y),float(value.z)]
            if any(not math.isfinite(x) for x in xyz):xyz='NONFINITE'
        except (AttributeError,TypeError,ValueError):xyz=None
        rows.append({'atom':atom.name.strip(),'input_xyz':xyz,'aliases_current_xyz':value is getattr(atom,'xyz',None)})
    return rows


def prepare_native_setup(molecule,spec,result):
    """Call the selected original Setup once, proving an unchanged component."""
    from pathlib import Path
    from hashlib import sha256
    import importlib.util,inspect
    root=Path(spec['installation_root']).resolve(strict=True)
    reference=spec['setup_sources'][0];data=(root/reference['path']).read_bytes()
    if sha256(data).hexdigest()!=reference['sha256'] or len(data)!=reference['size']:raise ValueError('Native setup reference changed')
    control={'policy_id':'cif-native-input-coordinate-setup-v1','status':'STARTED','reference':native_setup_reference(data),
        'before':native_inventory(molecule),'before_format':molecule.GetOriginalFormat(),'input_before':input_coordinate_snapshot(molecule)}
    result['setup_control']=control
    method=molecule.Setup
    if not inspect.ismethod(method) or method.__self__ is not molecule:raise ValueError('Unsupported native Setup method')
    module=inspect.getmodule(method);path=Path(module.__file__).absolute();resolved=path.resolve(strict=True)
    row=next(r for r in spec['sources'] if r['module']=='elbow.chemistry.SimpleMoleculeClass')
    found=importlib.util.find_spec(module.__name__)
    if (path!=resolved or resolved!=Path(row['installed']).resolve(strict=True) or module.__name__!=row['module']
            or found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=resolved
            or sha256(resolved.read_bytes()).hexdigest()!=row['sha256']):raise ValueError('Unselected native Setup source')
    control['method']={'module':module.__name__,'path':resolved.relative_to(root).as_posix(),'sha256':row['sha256'],
        'definition_line':method.__func__.__code__.co_firstlineno,'selected_source':True}
    inspect.signature(method).bind();method()
    control.update(after=native_inventory(molecule),after_format=molecule.GetOriginalFormat(),input_after=input_coordinate_snapshot(molecule))
    if control['before']!=control['after'] or control['before_format']!=control['after_format']:
        raise ValueError('Native Setup changed component state')
    if ({r['atom']:r['input_xyz'] for r in control['input_after']}!={r['atom']:r['xyz'] for r in control['before']['atoms']}):
        raise ValueError('Native Setup did not retain exact input coordinates')
    control['status']='NATIVE_SOURCE_SETUP_PASS'


def qualify_setup_evidence(result):
    """Replay preparation independently from local/final chemical qualification."""
    c=result.get('setup_control',{});method=c.get('method',{});reference=c.get('reference',{})
    rows=c.get('input_after',[]);atoms=c.get('before',{}).get('atoms',[])
    valid=(bool(rows) and len(rows)==len(atoms) and len({r.get('atom') for r in rows})==len(rows)
        and all(isinstance(r.get('input_xyz'),list) and len(r['input_xyz'])==3
            and all(type(x) in (int,float) and math.isfinite(x) for x in r['input_xyz']) for r in rows)
        and {r['atom']:r['input_xyz'] for r in rows}=={r['atom']:r['xyz'] for r in atoms})
    checks={'policy':c.get('policy_id')==POLICY_ID,'setup_completed':c.get('status')=='NATIVE_SOURCE_SETUP_PASS',
        'native_reference':reference.get('function')=='builder' and type(reference.get('setup_line')) is int
            and type(reference.get('constructor_line')) is int and 0<reference['setup_line']<reference['constructor_line'] and reference.get('arguments')==[],
        'selected_method':method.get('selected_source') is True and method.get('module')=='elbow.chemistry.SimpleMoleculeClass'
            and method.get('path','').endswith('/elbow/chemistry/SimpleMoleculeClass.py')
            and type(method.get('definition_line')) is int and method['definition_line']>0,
        'unchanged_component':bool(atoms) and c.get('before')==c.get('after')==result.get('constructor',{}).get('promoted')
            and c.get('before_format')==c.get('after_format')==result.get('constructor',{}).get('promoted_format'),
        'exact_source_coordinate_cache':valid}
    endpoint=c.get('input_after_constructor',[])
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'NATIVE_SOURCE_SETUP_PASS' if all(checks.values()) else 'REVIEW',
        'checks':checks,'checks_pass':all(checks.values()),'cached_input_coordinates_preserved_after_constructor':bool(endpoint)
            and [{k:v for k,v in r.items() if k!='aliases_current_xyz'} for r in endpoint]==[{k:v for k,v in r.items() if k!='aliases_current_xyz'} for r in rows],
        'absolute_cip_assignment':'NOT_RUN','whole_builder_replay':'NOT_RUN','automatic_adoption':False}


def source_setup_worker(base):
    """Keep historical worker bytes unchanged unless this preparation is explicit."""
    token="        result['constructor'].update(status='STARTED',native_class="
    end="Path('constructor_result.json').write_text("
    if base.count(token)!=1 or base.count(end)!=1:raise ValueError('Constructor setup insertion differs')
    base=base.replace(token,"        prepare_native_setup(molecule,spec,result)\n"+token)
    base=base.replace(end,"if 'setup_control' in result:result['setup_control']['input_after_constructor']=input_coordinate_snapshot(molecule)\n"+end)
    return getsource(native_setup_reference)+'\n'+getsource(input_coordinate_snapshot)+'\n'+getsource(prepare_native_setup)+'\n'+base
