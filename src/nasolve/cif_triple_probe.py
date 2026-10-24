"""Independent isolated-component controls for declared triple-bond mechanics."""
from hashlib import sha256
import json
from pathlib import Path
from .cif_triple_bond_audit import audit_triple_bonds,write_component_control_model
from .cif_installed_component import capture_installed_component,verify_component_capture
from .cif_native_validation import inspect_native_bundle


def _write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def run_triple_controls(sources,saved_candidates,output,*,phenix=None,api_sources=(),timeout_seconds=60):
    """Read installed lookup and explicit dictionaries at the same fixed seed.

    An absent ``phenix`` requests offline inspection only. No writer/generator,
    ReadySet, minimizer, pair inference or application to a scaffold is called.
    """
    output=Path(output).absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Require fresh triple-control output')
    sources={c:Path(p).resolve(strict=True) for c,p in sources.items()}
    candidates={c:Path(p).resolve(strict=True) for c,p in saved_candidates.items()}
    if not sources or not set(candidates)<=set(sources):raise ValueError('Require explicit sources for every saved candidate')
    inputs={p:p.read_bytes() for p in [*sources.values(),*candidates.values()]}
    if any(output.resolve().is_relative_to(p.parent) for p in inputs):raise ValueError('Triple-control output must be separate from all inputs')
    output.mkdir(parents=True)
    result={'schema_version':1,'status':'REVIEW','scope':'ISOLATED_SOURCE_SEED_NATIVE_COMPONENT_CONTROLS',
        'cases':{},'native_execution':'NOT_RUN','model_optimization':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'readyset':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'limitations':['Seed geometry is descriptive and is not independent chemical or experimental validation.',
            'Installed monomer lookup is not the complete ReadySet path and cannot locate a historical ReadySet failure.',
            'No experimental scaffold, links or diffraction data are used; all active terms remain review evidence.',
            'Saved candidate remains nonconverged and stereochemically unqualified; it is never adopted.',
            'Torsions containing an expected-linear axis require review; this does not establish optimizer causation.']}
    captures=[]
    for code,source in sources.items():
        case={'source_sha256':sha256(inputs[source]).hexdigest(),'offline':{},'native':{}}
        result['cases'][code]=case
        case['offline']['public_source']=audit_triple_bonds(source,code,dictionary=source)
        if code in candidates:case['offline']['saved_candidate']=audit_triple_bonds(source,code,dictionary=candidates[code])
        model=output/'models'/code/'source_seed.pdb'
        case['model_preparation']=write_component_control_model(source,code,model)
        policy=output/'policies'/code/'isolated_component.phil'
        policy.parent.mkdir(parents=True)
        policy.write_text('pdb_interpretation {\n secondary_structure.enabled = False\n}\n')
        before=model.read_bytes(),policy.read_bytes()
        _write(output/'offline'/(code+'.json'),case)
        if phenix is None:continue
        resource_dir=output/'resources'/code
        resource=capture_installed_component(phenix.root,phenix.executables['phenix.python'],api_sources,
            code,resource_dir,environment=phenix.environment,timeout_seconds=min(timeout_seconds,30))
        captures.append((resource,resource_dir));case['installed_resource']=resource
        print(code,'installed resource:',resource['result']['status'],flush=True)
        dictionaries={'installed_lookup':[]}
        if resource['result']['status']=='RECORDED':
            dictionaries['installed_snapshot']=[resource_dir/'installed_component.cif']
            try:case['offline']['installed_snapshot']=audit_triple_bonds(source,code,dictionary=resource_dir/'installed_component.cif')
            except ValueError as exc:case['offline']['installed_snapshot']={'status':'REVIEW','error':str(exc)}
        if code in candidates:dictionaries['saved_candidate']=[candidates[code]]
        for label,paths in dictionaries.items():
            native=inspect_native_bundle(model,paths,output/'native'/code/label,phenix.executables['phenix.python'],
                environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=min(timeout_seconds,60),
                phil_files=[policy],inventory_detail='linked',policy_inventory=True,installed_library_only=not paths)
            row={'directory':{'anchor':'triple_control_directory','path':Path(native['native_directory']).relative_to(output).as_posix()},
                 'interpretation':native,'triple_screen':{'status':'NOT_RUN','reason':'Native interpretation did not complete'}}
            case['native'][label]=row
            report=native.get('native_validation') or {}
            if native['status']=='REVIEW' and report.get('status')=='REVIEW':
                if report.get('restraint_policy',{}).get('secondary_structure_enabled') is not False:
                    raise ValueError('Isolated component enabled native secondary-structure inference')
                row['triple_screen']=audit_triple_bonds(source,code,native=report)
            print(code,label+':',row['triple_screen']['status'],flush=True)
        if {'installed_lookup','installed_snapshot'}<=set(case['native']):
            def terms(label):
                screen=case['native'][label]['triple_screen']
                return screen.get('triple_bonds'),screen.get('linear_axis_torsions')
            a,b=terms('installed_lookup'),terms('installed_snapshot')
            case['installed_lookup_snapshot_terms_match']=a==b if a[0] and b[0] else None
        if before!=(model.read_bytes(),policy.read_bytes()):raise ValueError('Isolated control model or policy changed')
        for capture,directory in captures:verify_component_capture(phenix.root,capture,directory)
    if any(p.read_bytes()!=data for p,data in inputs.items()):raise ValueError('Triple-control input changed')
    if phenix is not None:result['native_execution']='INSTALLED_COMPONENT_AND_TRIPLE_PROXY_CONTROLS'
    _write(output/'triple_control_receipt.json',result)
    return result
