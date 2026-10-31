"""Opt-in frozen dictionary preparation for explicitly declared model sites.

No cache search, native execution, coordinate editing or automatic PostMR
selection. Reading rederives the prepared files from their frozen authorities.
Native evidence is bound separately to exact ordered inputs and consumer pins.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_store import (
    _bytes, _hash, _json, recipe_representation_policy, resolve_dictionary_snapshot,
)
from .cif_linked_preparation import _model_inventory, prepare_linked_component
from .cif_postmr_cached_model import cached_preparation_replays, _consumer_matches
from .cif_terminal_preparation import load_terminal_recipe, prepare_terminal_component

POLICY_ID = 'cif-stored-dictionary-sites-v1'
CONTEXT_POLICY_ID = 'cif-stored-dictionary-sites-v2'
FULL_MODEL_POLICY_ID = 'cif-stored-dictionary-sites-v3'
SOURCE_NAMES_POLICY_ID = 'cif-stored-dictionary-sites-v4'
ANCHOR = 'dictionary_site_directory'
_SNAPSHOT_FILES = ('resolution.json', 'entry/manifest.json', 'entry/source.cif',
    'entry/dictionary.cif', 'entry/qualification.json', 'entry/provenance.json')


def _need(value, message):
    if not value: raise ValueError(message)


def _safe(relative):
    return (isinstance(relative,str) and bool(relative) and not relative.startswith('/')
        and ':' not in relative and '\\' not in relative
        and all(part not in {'','.','..'} for part in relative.split('/')))


def _read(path):
    path=Path(path).absolute()
    _need(not any(p.is_symlink() for p in (path,*path.parents)) and path.is_file(),
        'Require a regular site artifact without symlink traversal')
    return path.read_bytes()


def _ref(path, root):
    data=_read(path)
    return {'anchor':ANCHOR,'path':path.relative_to(root).as_posix(),
        'sha256':sha256(data).hexdigest(),'size':len(data)}


def _files(root):
    paths=sorted(root.rglob('*'))
    _need(not any(p.is_symlink() for p in paths), 'Symlinked site artifact')
    return [_ref(p,root) for p in paths if p.is_file() and p!=root/'site_receipt.json']


def _consumer(consumer):
    """Validate the captured implementation scope, without reading an installation."""
    from .cif_postmr_cache import _API, _ENERGY
    _need(isinstance(consumer,dict) and consumer.get('name')=='Phenix/CCTBX'
        and isinstance(consumer.get('version'),str) and bool(consumer['version'].strip())
        and consumer['version']!='unknown'
        and _hash(consumer.get('executable_sha256')), 'Incomplete native consumer identity')
    for field,names in [('api_sources',_API),('energy_sources',_ENERGY)]:
        rows=consumer.get(field,[])
        _need(isinstance(rows,list) and len(rows)==len(names), 'Incomplete native implementation pins')
        found=[]
        for row in rows:
            _need(isinstance(row,dict) and row.get('anchor')=='phenix_installation'
                and _safe(row.get('path')) and _hash(row.get('sha256')), 'Invalid native implementation pin')
            matches=[name for name in names if row['path'].endswith('/site-packages/'+name)]
            _need(len(matches)==1, 'Unexpected native implementation scope')
            found.extend(matches)
        _need(sorted(found)==sorted(names), 'Duplicate or missing native implementation pins')


def _resource(path, consumer):
    receipt=_json(_read(path))
    recipe=load_terminal_recipe(path)
    _need(receipt.get('phenix_version')==consumer['version']
        and receipt.get('executable_sha256')==consumer['executable_sha256'],
        'Terminal resources belong to another native consumer')
    pin=next(p for p in consumer['api_sources'] if p['path'].endswith('/mmtbx/monomer_library/server.py'))
    server=[p for p in recipe['api_sources'] if p.get('module')=='mmtbx.monomer_library.server']
    _need(len(server)==1 and server[0].get('sha256')==pin['sha256'], 'Terminal resource reader differs')
    return receipt


def _links(model, contexts, expected):
    sites=_model_inventory(model)
    _need(isinstance(expected,list), 'Require explicit complete model links')
    pairs=[]
    for pair in expected:
        _need(isinstance(pair,(list,tuple)) and len(pair)==2
            and all(isinstance(s,str) and s in sites for s in pair) and pair[0]!=pair[1],
            'Invalid declared model link')
        pairs.append(tuple(pair))
    _need(len(pairs)==len(set(pairs)), 'Duplicate declared model link')
    _need(len({p[0] for p in pairs})==len(pairs) and len({p[1] for p in pairs})==len(pairs),
        'Branched native backbone needs a separate adapter')
    for context in contexts:
        site=context['site']; incoming=context.get('incoming_site'); outgoing=context.get('outgoing_site')
        _need([a for a,b in pairs if b==site]==([] if incoming is None else [incoming])
            and [b for a,b in pairs if a==site]==([] if outgoing is None else [outgoing]),
            'Declared links disagree with exact site context')
    return [list(pair) for pair in pairs]


def _derive(root, controls, destination):
    saved=resolve_dictionary_snapshot(root/'snapshot'); manifest=saved['manifest']
    _need(saved['qualification_current'], 'Stored native evidence needs requalification')
    consumer=manifest['consumer']; _consumer(consumer)
    _need(_bytes(controls['consumer'])==_bytes(consumer), 'Consumer differs from frozen isolated qualification')
    if 'native_context' in controls:
        from .cif_native_context import validate_native_context
        validate_native_context(controls['native_context'])
    contexts=controls['contexts']; model=root/'inputs/model.pdb'
    links=_links(model,contexts,controls['expected_links'])
    policy=recipe_representation_policy(manifest['request']['recipe'])
    resource=controls['terminal_resource']
    terminal=any(c.get('five_prime_state')=='free_OH' for c in contexts)
    _need(terminal==(resource is not None), 'Exactly the free 5-prime OH sites require terminal resources')
    options=dict(code=manifest['request']['component'],native_qualification=saved['qualification'],
        bond_representation_policy=policy)
    if 'phosphate_atom_policy' in controls:
        from .cif_phosphate_names import POLICY_ID as names_policy
        _need(controls['phosphate_atom_policy']==names_policy
            and controls.get('native_context',{}).get('monomer_inventory')=='full_model',
            'Source-named preparation requires explicit current policy and full native context')
        _need(not terminal, 'Source-named terminal recipe is not qualified')
        options['phosphate_atom_policy']=controls['phosphate_atom_policy']
    if terminal:
        _need(_safe(resource) and resource.startswith('resources/'), 'Unsafe terminal resource reference')
        _resource(root/resource,consumer)
        preparation=prepare_terminal_component(saved['source'],saved['dictionary'],model,
            contexts,root/resource,destination,**options)
    else:
        preparation=prepare_linked_component(saved['source'],saved['dictionary'],model,contexts,destination,**options)
    if controls.get('native_context',{}).get('monomer_inventory')=='full_model':
        from .cif_native_monomers import FULL_MODEL_PHIL
        (destination/'native_interpretation.phil').write_text(FULL_MODEL_PHIL)
    return saved,preparation,links,policy


def _report(root, controls, saved, links, policy):
    site_policy=CONTEXT_POLICY_ID if 'native_context' in controls else POLICY_ID
    if controls.get('native_context',{}).get('monomer_inventory')=='full_model':site_policy=FULL_MODEL_POLICY_ID
    if 'phosphate_atom_policy' in controls:site_policy=SOURCE_NAMES_POLICY_ID
    return {'schema_version':1,'policy_id':site_policy,'status':'PREPARED_REVIEW',
        'entry_id':saved['entry_id'],'request_key':saved['manifest']['request_key'],
        'component':saved['manifest']['request']['component'],'bond_representation_policy':policy,
        **controls,'expected_links':links,'files':_files(root),'native_validation':'NOT_RUN',
        'scientific_qualification':'NOT_ASSESSED','phosphate_state_authority':'EXPLICIT_SOURCE_AND_SITE_CONTEXT',
        'automatic_adoption':False,'model_editing':'NOT_RUN','model_optimization':'NOT_RUN'}


def _inputs(root, controls):
    result={}
    for field,extension in [('supplementary_dictionaries','cif'),('supplementary_phils','phil')]:
        names=controls[field]
        _need(isinstance(names,list) and names==[
            'inputs/'+field+'/'+str(i).zfill(3)+'.'+extension for i in range(len(names))],
            'Supplementary input layout or order differs')
        result[field]=[root/name for name in names]
        for path in result[field]:_read(path)
    cifs=result['supplementary_dictionaries']; phils=result['supplementary_phils']
    full=controls.get('native_context',{}).get('monomer_inventory')=='full_model'
    policy=[root/'prepared/native_interpretation.phil'] if full else []
    return {'model':root/'inputs/model.pdb',
        'before_dictionaries':[root/'snapshot/entry/dictionary.cif',*cifs],
        'after_dictionaries':[root/'prepared/base_dictionary.cif',root/'prepared/site_modifications.cif',*cifs],
        'before_phils':[*phils,*policy],'after_phils':[*phils,root/'prepared/site_modifications.phil',*policy],
        **({'native_options':{'full_monomer_inventory':True}} if full else {})}


def prepare_dictionary_sites(snapshot, model, contexts, output, *, consumer, expected_links,
        terminal_resource=None, supplementary_dictionaries=(), supplementary_phils=(), native_context=None, phosphate_atom_policy=None):
    """Freeze only explicit inputs and publish a fresh, replayable preparation.

    Consumer must equal the saved isolated qualification. Changed installations
    need upstream requalification; this function never upgrades that evidence.
    All model sites sharing the component code need an explicit context. Links
    cover the complete model, including unchanged supplementary components.

    Optional native_context freezes the versioned end-state/custom-restraint
    contract. Omission preserves v1 preparation and qualification behavior.
    Context v2 additionally freezes full-model interpretation as the final PHIL
    input. Readback returns native_options for the maintained capture worker.
    """
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents), 'Unsafe preparation destination')
    snapshot=Path(snapshot).absolute()
    _need(output!=snapshot and snapshot not in output.parents, 'Cannot publish inside the frozen snapshot')
    resolve_dictionary_snapshot(snapshot); _consumer(consumer)
    controls={'consumer':consumer,'contexts':contexts,'expected_links':expected_links,
        'terminal_resource':None,'supplementary_dictionaries':[],'supplementary_phils':[]}
    if native_context is not None:
        from .cif_native_context import validate_native_context
        controls['native_context']=validate_native_context(native_context)
    if phosphate_atom_policy is not None:
        controls['phosphate_atom_policy']=phosphate_atom_policy
    original={}
    def freeze(source,target):
        source=Path(source); data=_read(source);original[source]=data
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='dictionary-sites-',dir=output.parent) as temporary:
        root=Path(temporary)/'bundle';root.mkdir(mode=0o700)
        for name in _SNAPSHOT_FILES:freeze(Path(snapshot)/name,root/'snapshot'/name)
        freeze(model,root/'inputs/model.pdb')
        if terminal_resource is not None:
            resource=Path(terminal_resource);record=_resource(resource,consumer)
            controls['terminal_resource']='resources/'+resource.name
            freeze(resource,root/controls['terminal_resource'])
            names=[]
            for ref in record['outputs']:
                name=ref['path'];_need(_safe(name) and ref['anchor']=='native_directory'
                    and name!=resource.name and name not in names, 'Unsafe or duplicate resource output')
                names.append(name);freeze(resource.parent/name,root/'resources'/name)
        for field,paths,ext in [('supplementary_dictionaries',supplementary_dictionaries,'cif'),
                               ('supplementary_phils',supplementary_phils,'phil')]:
            for i,path in enumerate(paths):
                name='inputs/'+field+'/'+str(i).zfill(3)+'.'+ext
                freeze(path,root/name);controls[field].append(name)
        # Normalize tuples and detach mutable caller containers before replay.
        controls=_json(_bytes(controls))
        saved,_,links,policy=_derive(root,controls,root/'prepared')
        report=_report(root,controls,saved,links,policy)
        (root/'site_receipt.json').write_bytes(_bytes(report))
        read_dictionary_sites(root)
        _need(all(_read(p)==data for p,data in original.items()), 'Input changed during site preparation')
        root.rename(output)
    return report


def read_dictionary_sites(output):
    """Read frozen inputs and rederive every generated file; never mutate the bundle."""
    root=Path(output).absolute();report=_json(_read(root/'site_receipt.json'))
    _need(type(report.get('schema_version')) is int and report['schema_version']==1
        and report.get('policy_id') in {POLICY_ID,CONTEXT_POLICY_ID,FULL_MODEL_POLICY_ID,SOURCE_NAMES_POLICY_ID}, 'Unknown site preparation schema/policy')
    _need(report.get('files')==_files(root), 'Site artifact inventory or checksum differs')
    controls={k:report[k] for k in ('consumer','contexts','expected_links','terminal_resource',
        'supplementary_dictionaries','supplementary_phils')}
    if report['policy_id'] in {CONTEXT_POLICY_ID,FULL_MODEL_POLICY_ID,SOURCE_NAMES_POLICY_ID}:
        _need('native_context' in report, 'Missing frozen native context')
        controls['native_context']=report['native_context']
    if 'phosphate_atom_policy' in report:
        controls['phosphate_atom_policy']=report['phosphate_atom_policy']
    inputs=_inputs(root,controls)
    allowed={'snapshot/'+name for name in _SNAPSHOT_FILES}|{'inputs/model.pdb'}
    allowed.update(controls['supplementary_dictionaries']);allowed.update(controls['supplementary_phils'])
    resource=controls['terminal_resource']
    if resource is not None:
        _need(_safe(resource) and resource.startswith('resources/'), 'Unsafe terminal resource reference')
        record=_resource(root/resource,controls['consumer'])
        allowed.add(resource)
        allowed.update('resources/'+row['path'] for row in record['outputs'])
    with TemporaryDirectory(prefix='dictionary-sites-read-') as temporary:
        replay=Path(temporary)/'prepared'
        saved,preparation,links,policy=_derive(root,controls,replay)
        allowed.update('prepared/'+p.name for p in replay.iterdir())
        _need({r['path'] for r in report['files']}==allowed, 'Unrequested site artifact')
        actual={p.name for p in (root/'prepared').iterdir()}
        _need(actual=={p.name for p in replay.iterdir()}, 'Prepared file membership differs')
        for path in replay.iterdir():
            original=_read(root/'prepared'/path.name)
            if path.name=='preparation_receipt.json':
                _need(cached_preparation_replays(_json(original),_json(path.read_bytes())),
                    'Preparation receipt does not replay')
            else:_need(original==path.read_bytes(), 'Prepared numerical or policy bytes do not replay')
    expected=_report(root,controls,saved,links,policy)
    _need(_bytes(report)==_bytes(expected), 'Site preparation claim differs from frozen evidence')
    return {'report':report,'snapshot':saved,'preparation':preparation,**inputs,
        'projections':{c['site']:(root/'prepared'/('projected_'+c['site'].replace(':','_')+'.cif'),
            report['component']) for c in controls['contexts']}}


def _bind_capture(record, consumer, model, dictionaries, phils):
    _consumer(consumer)
    _need(record.get('execution',{}).get('status')=='COMPLETED'
        and record['execution'].get('returncode')==0 and _consumer_matches(record,consumer,None),
        'Native capture consumer or completion differs')
    expected=[('model',model),*[('dictionary',p) for p in dictionaries],*[('phil',p) for p in phils]]
    pins=[(role,sha256(_read(path)).hexdigest(),path.stat().st_size) for role,path in expected]
    actual=[(r.get('role'),r.get('sha256'),r.get('size')) for r in record['inputs']]
    _need(actual==pins, 'Native capture did not consume the exact ordered prepared inputs')


def _cross_site_proxies(native, kind):
    from .cif_linked_qualification import _site
    from .cif_terminal_qualification import _proxy_subset
    atoms={a['i_seq']:a for a in native['atoms']}
    rows=[r for r in native['geometry']['proxy_details'][kind] if len({
        _site(atoms[i]) for i in r['i_seqs']+r.get('j_seqs',[])})>1]
    selected={**native,'geometry':{**native['geometry'],'proxy_details':{kind:rows}}}
    return _proxy_subset(selected,set(),kind)


def _port_elements(native, context):
    from .cif_linked_qualification import _site
    atoms={(_site(a),a['atom_id']):a['element'].strip().upper() for a in native['atoms']}
    expected={};site=context['site']
    if context.get('incoming_site') is not None:
        expected.update({(context['incoming_site'],"O3'"):'O',(site,'P'):'P'})
    if context.get('outgoing_site') is not None:
        expected.update({(site,"O3'"):'O',(context['outgoing_site'],'P'):'P'})
    return all(atoms.get(key)==element for key,element in expected.items())


def _site_native_checks(before, after, prepared):
    """Reuse per-site active checks without requiring a free end to have two links."""
    from itertools import combinations
    from math import isfinite
    from .cif_candidate_usability import energy_inventory_checks
    from .cif_construction_native import NATIVE_KINDS
    from .cif_fixed_geometry import _fixed_policy
    from .cif_linked_control import _heavy_proxy_checks
    from .cif_linked_preparation import atom_rows, component_values
    from .cif_linked_qualification import _site
    from .cif_terminal_qualification import _proxy_subset
    checks=[]
    def check(name, value, **evidence):
        checks.append({'check':name,'status':'PASS' if value else 'REVIEW',**evidence})
    try:
        for label,native in [('before',before),('after',after)]:
            for name,value in energy_inventory_checks(native).items():check(label+':'+name,value)
            check(label+':fixed-secondary-structure-policy',_fixed_policy(native))
            geometry=native['geometry'];details=geometry['proxy_details'];atoms=native['atoms']
            check(label+':complete-proxy-inventory',set(details)==NATIVE_KINDS and all(
                isinstance(rows,list) and type(geometry['proxy_counts'].get(k)) is int
                and geometry['proxy_counts'][k]==len(rows) for k,rows in details.items()))
            check(label+':consistent-bond-inventories',geometry['simple_bonds']==details['bond_simple']
                and geometry['asu_bonds']==details['bond_asu'])
            points=geometry['sites_cart_exact']
            check(label+':native-coordinate-roundtrip',len(points)==len(atoms) and all(
                len(p)==3 and all(type(x) in (int,float) and isfinite(x) and abs(x-y)<=1e-12
                    for x,y in zip(p,a['xyz'])) for p,a in zip(points,atoms)))
            finite=True
            for kind,rows in details.items():
                _proxy_subset(native,set(),kind)  # Validate named endpoints, including changed sites.
                for row in rows:
                    weights=row.get('weights',[row.get('weight')])
                    finite &= (kind!='planarity' or len(weights)==len(row['i_seqs'])) and all(
                        type(w) in (int,float) and isfinite(w) and (w>0 or
                            kind=='const_dihedral' and w==0 and row.get('periodicity')==0) for w in weights)
                    fields=[] if kind=='planarity' else ['distance_ideal'] if kind in {'bond_simple','bond_asu'} else [
                        'angle_ideal'] if kind in {'angle','dihedral','const_dihedral'} else [
                        'volume_ideal'] if kind=='chirality' else ['target_angle_deg']
                    finite &= all(type(row.get(f)) in (int,float) and isfinite(row[f]) for f in fields)
                    if kind=='chirality':finite &= type(row.get('both_signs')) is bool and abs(row['volume_ideal'])>0
            check(label+':finite-active-proxy-parameters',finite)
            rows=native['monomer_mappings']['rows'];sites=[r['site'] for r in rows]
            # The old dictionary may still demand precisely the leaving atoms
            # this declared preparation removes (notably OP3). Record that
            # deficit without requiring the pre-repair capture to be repaired.
            deleted={p['site']:set(p.get('deleted_atoms',[])) for p in prepared['preparation']['sites']}
            accounted=all(r.get('missing_non_hydrogen_atoms',{}).get('status')=='RECORDED'
                and r.get('unexpected_atoms')=={'status':'RECORDED','atom_ids':[]}
                and set(r['missing_non_hydrogen_atoms']['atom_ids']) <= (
                    deleted.get(r['site'],set()) if label=='before' else set()) for r in rows)
            check(label+':accounted-unique-monomer-sites',len(sites)==len(set(sites))
                and set(sites)=={_site(a) for a in atoms} and accounted)
        # This adapter changes component-local leaving groups, not declared
        # inter-site mechanics. Include soft pair/stack proxies as exact named
        # evidence; never infer new bonds or exempt a whole origin category.
        for kind in sorted(NATIVE_KINDS):
            check('preserved-cross-site-proxies:'+kind,
                _cross_site_proxies(before,kind)==_cross_site_proxies(after,kind))
        mappings={r['site']:r for r in after['monomer_mappings']['rows']}
        plans={r['site']:r for r in prepared['preparation']['sites']}
        atoms={r['i_seq']:r for r in after['atoms']};details=after['geometry']['proxy_details']
        for context in prepared['report']['contexts']:
            site=context['site'];path,code=prepared['projections'][site];plan=plans[site]
            check('exact-component:'+site,mappings[site]['resname'].strip()==code)
            source_atoms=atom_rows(component_values(path,code))
            check('exact-coordinate-elements:'+site,all(a['atom_id'] in source_atoms
                and a['element'].strip().upper()==source_atoms[a['atom_id']]['type_symbol'].upper()
                for a in atoms.values() if _site(a)==site))
            check('declared-native-port-elements:'+site,_port_elements(after,context))
            check('exact-site-modifier:'+site,mappings[site].get('chem_mod_ids')=={
                'status':'RECORDED','ids':[plan['modification_id']] if plan.get('modification_id') else []})
            for name,value in _heavy_proxy_checks(after,path,code,site).items():check(name+':'+site,value)
            terminal=(prepared['report'].get('native_context') is not None
                and context.get('five_prime_state')=='phosphate')
            if context.get('incoming_site') is not None or terminal:
                p=next(i for i,a in atoms.items() if _site(a)==site and a['atom_id']=='P')
                neighbors={next(i for i in r['i_seqs'] if i!=p) for r in details['bond_simple'] if p in r['i_seqs']}
                angles={min(tuple(r['i_seqs']),tuple(r['i_seqs'])[::-1]) for r in details['angle']}
                from .cif_phosphate_names import phosphate_names
                names=phosphate_names(component_values(path,code),leaving_required=terminal)
                expected={(site,names['OP3']) if terminal else (context['incoming_site'],"O3'"),
                    (site,"O5'"),(site,names['OP1']),(site,names['OP2'])}
                check(('terminal' if terminal else 'linked')+'-phosphate-tetrahedral-coverage:'+site,
                    {(_site(atoms[i]),atoms[i]['atom_id']) for i in neighbors}==expected
                    and all(min((a,p,b),(b,p,a)) in angles for a,b in combinations(neighbors,2)))
    except (KeyError,TypeError,ValueError,IndexError,StopIteration,ArithmeticError) as exc:
        check('complete-current-site-native-evidence',False,error=type(exc).__name__+': '+str(exc))
    return checks


def _diagnostic_continuation(qualification, native_checks):
    from .cif_effective_source_recovery import mechanics_can_continue
    # Both layers are mandatory. The shared policy admits only the existing
    # unavailable-formal-charge exception, never an input/proxy contradiction.
    allowed=bool(qualification.get('checks')) and bool(native_checks) and mechanics_can_continue(
        {'checks':[*qualification['checks'],*native_checks]})
    return {'status':'CONTINUE_WITH_NOTES' if allowed else 'BLOCKED','allowed':allowed,
        'scope':'SEPARATE_DIAGNOSTIC_PHASE_ONLY','automatic_adoption':False,
        'policy':'EXISTING_MECHANICS_CONTINUATION; UNAVAILABLE_FORMAL_CHARGE_ONLY'}


def inspect_dictionary_site_native(output, baseline_receipt, candidate_receipt):
    """Bind saved complete native captures, then apply existing terminal/site gates.

    This checks captured implementation identity, not a live installation. Missing
    formal-charge evidence remains UNSUPPORTED. The existing continuation policy
    may permit a separate diagnostic phase; no automatic adoption follows.
    """
    from .cif_attachment_native import _capture, _native_atoms
    from .cif_terminal_qualification import qualify_terminal_bundle
    prepared=read_dictionary_sites(output);report=prepared['report'];model=prepared['model']
    original_receipt=_read(Path(output)/'site_receipt.json')
    captures=[];pins=[];snapshots={}
    for label,path in [('before',baseline_receipt),('after',candidate_receipt)]:
        path=Path(path);receipt_bytes=_read(path)
        record,native,captured=_capture(path,_read(model))
        snapshots.update(captured)
        _bind_capture(record,report['consumer'],model,prepared[label+'_dictionaries'],prepared[label+'_phils'])
        if report.get('native_context',{}).get('monomer_inventory')=='full_model':
            from .cif_native_monomers import POLICY_ID as monomer_policy, review_full_monomers
            _need(record.get('full_monomer_inventory_policy')==monomer_policy,
                'Site context requires a maintained full native monomer capture')
            review_full_monomers(native)
        _native_atoms(native,_read(model))
        _need(native.get('status')=='REVIEW' and native.get('fatal_problems') is None
            and native.get('unused_definitions')==[] and native.get('unsupported_fields')==[],
            'Native interpretation contains unresolved failures or unused inputs')
        _need(_read(path)==receipt_bytes, 'Native receipt changed during inspection')
        captures.append(native);pins.append(sha256(receipt_bytes).hexdigest())
    before,after=captures
    _need(before['restraint_policy']==after['restraint_policy'], 'Native restraint policy changed')
    result=qualify_terminal_bundle(before,after,[prepared['preparation']],
        [tuple(p) for p in report['expected_links']],
        [c['site'] for c in report['contexts'] if c['five_prime_state']=='free_OH'],prepared['projections'],
        native_context=report.get('native_context'))
    native_checks=_site_native_checks(before,after,prepared)
    passed=result['status']=='TERMINAL_BUNDLE_MECHANICS_PASS' and all(r['status']=='PASS' for r in native_checks)
    _need(_read(Path(output)/'site_receipt.json')==original_receipt
        and _files(Path(output).absolute())==report['files'], 'Site evidence changed during native inspection')
    _need(all(_read(path)==data for path,data in snapshots.items()), 'Native capture changed during inspection')
    return {'schema_version':1,'policy_id':report['policy_id'],
        **({'native_context':report['native_context']} if 'native_context' in report else {}),
        'status':'STORED_SITE_NATIVE_MECHANICS_PASS' if passed else 'REVIEW',
        'native_checks':native_checks,'diagnostic_continuation':_diagnostic_continuation(result,native_checks),
        'preparation_sha256':sha256(_read(Path(output)/'site_receipt.json')).hexdigest(),
        'baseline_receipt_sha256':pins[0],'candidate_receipt_sha256':pins[1],
        'exact_capture_binding':True,'qualification':result,'native_execution':'NOT_RUN',
        'consumer_binding':'CAPTURED_IMPLEMENTATION; LIVE_INSTALLATION_NOT_CHECKED',
        'source_protonation':'NOT_ASSESSED','scientific_qualification':'NOT_ASSESSED',
        'automatic_adoption':False}
