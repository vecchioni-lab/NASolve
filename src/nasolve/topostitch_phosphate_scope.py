"""Explicit coupled-sugar scope; Cedar retains geometry arithmetic and forces."""
from contextlib import contextmanager
from hashlib import sha256
import math
from pathlib import Path

from .topostitch_endpoint import _native_atom_order
from .topostitch_recipe import model_atom_rows

_SUGAR = ("O5'", "C5'", "C4'", "O4'", "C3'", "O3'", "C2'", "C1'")
_CENTERS = ("C1'", "C3'", "C4'")


def _need(value, message):
    if not value:
        raise ValueError(message)


def _points(raw):
    return [[float(line[a:b]) for a,b in ((30,38),(38,46),(46,54))]
            for line in raw.splitlines() if line[:6] in (b'ATOM  ', b'HETATM')]


def prepare_coupled_sugars(source, inspection, native, *, native_owner, fixed_owner, include_bases=False):
    """Bind two canonical sugars, optionally releasing their complete bases.

    The caller authenticates the complete native reference and source bytes.
    Ordered native chirality signs are source-relative, not absolute CIP labels.
    This describes a scope, never physical feasibility or scientific acceptance.
    """
    _need(type(include_bases) is bool, "include_bases must be Boolean")
    rows=model_atom_rows(source);points=_points(source)
    order,_=_native_atom_order(native,source,native_owner)
    sites={row[0]:row[1] for row in (inspection['phosphate'],inspection['o3'])}
    _need(len(sites)==2 and all(c in ('DA','DT','DG','DC') for c in sites.values()),
          'Coupled sugars require two distinct canonical DNA residues')
    acceptor,donor=inspection['phosphate'][0],inspection['o3'][0]
    lookup={}
    atom_lines=[line for line in source.splitlines() if line[:6] in (b'ATOM  ',b'HETATM')]
    elements=[line[76:78].decode('ascii').strip().upper() for line in atom_lines]
    for i,row in enumerate(rows):
        site=(row['chain'] or '_')+':'+str(row['residue_number'])
        key=(site,row['atom_name'])
        _need(key not in lookup,'Ambiguous source atom in coupled scope')
        lookup[key]=i
        if site in sites:
            _need(row['residue_code']==sites[site] and not row['altloc']
                  and float(atom_lines[i][54:60])==1. and elements[i] not in ('H','D'),
                  'Coupled sugars require full-occupancy canonical heavy atoms without alternates')
    def atom(site,name):
        _need((site,name) in lookup,'Missing coupled-sugar atom: '+site+' '+name)
        i=lookup[site,name]
        _need(elements[i]==name[0],'Incorrect coupled-sugar atom element')
        return i
    selected=sorted([atom(acceptor,n) for n in ('P','OP1','OP2',*_SUGAR)]
                    +[atom(donor,n) for n in _SUGAR])
    _need(len(set(selected))==19,'Require exactly 19 distinct coupled-sugar atoms')
    base_indices=set();base_by_site={};base_map=None
    if include_bases:
        # Reuse the established canonical NARestraints role inventory; this
        # supplies names only, never pairing, topology or new native forces.
        from .topostitch_recipe import _library, recipe_digest
        _,maps,_,_=_library()
        base_map={code:maps[code] for code in sorted(set(sites.values()))}
        for site,code in sites.items():
            names=set(maps[code].values())
            expected=names|set(_SUGAR)|{'P','OP1','OP2'}
            _need({name for s,name in lookup if s==site}==expected,
                  'Endpoint base release requires the complete canonical heavy-atom inventory')
            base_by_site[site]={atom(site,name) for name in names}
            base_indices.update(base_by_site[site])
        selected=sorted(set(selected)|base_indices)
    scalar=fixed_owner.review_fixed_coordinates(native,[points[i] for i in order])
    centers={atom(s,n) for s in sites for n in _CENTERS}
    hands=[]
    for row in scalar['measurements']['chirality']:
        ids=[order[i] for i in row['i_seqs']]
        if ids[0] in centers:
            _need(row['status']=='MEASURED' and row.get('both_signs') is False
                  and row['sign_agreement'] is True and row['weight']>0,
                  'Coupled sugar has unqualified source handedness')
            hands.append(dict(source_indices=ids,target=row['target'],observed=row['observed']))
    _need(len(hands)==6 and {r['source_indices'][0] for r in hands}==centers,
          'Require one recorded signed proxy for each of six sugar centres')
    bonds={}
    for row in native['geometry']['proxy_details']['bond_simple']:
        pair=tuple(sorted(order[i] for i in row['i_seqs']))
        if row.get('symmetry_operation') in (None,'x,y,z') and row['weight']>0:
            bonds.setdefault(pair,[]).append(row)
    local=[]
    def bond(a,b):
        pair=tuple(sorted((a,b)))
        _need(len(bonds.get(pair,[]))==1,'Require one positive same-image bond at each sugar/attachment boundary')
        local.append(list(pair))
    ring=("C1'","C2'","C3'","C4'","O4'")
    for site,code in sites.items():
        for a,b in zip(ring,ring[1:]+ring[:1]):bond(atom(site,a),atom(site,b))
        for a,b in (("O5'","C5'"),("C5'","C4'"),("C3'","O3'")):
            bond(atom(site,a),atom(site,b))
        bond(atom(site,"C1'"),atom(site,'N9' if code in ('DA','DG') else 'N1'))
    for name in ('OP1','OP2',"O5'"):bond(atom(acceptor,'P'),atom(acceptor,name))
    bond(atom(donor,'P'),atom(donor,"O5'"))
    outgoing=atom(acceptor,"O3'")
    neighbors=[j for pair,definitions in bonds.items() if outgoing in pair and len(definitions)==1
               for j in pair if j!=outgoing and rows[j]['atom_name']=='P' and j not in selected]
    _need(len(neighbors)==1,'Require one held outer phosphate beyond the acceptor sugar')
    outer=neighbors[0];bond(outgoing,outer)
    outer_site=(rows[outer]['chain'] or '_')+':'+str(rows[outer]['residue_number'])
    anchors=[atom(site,name) for site in (donor,outer_site) for name in ('P','OP1','OP2')]
    _need(not set(anchors)&set(selected),'Outer phosphate anchors must remain held')
    c1={atom(site,"C1'") for site in sites};planes=[];monomers=[]
    for family in ('planarity','parallelity'):
        for ordinal,row in enumerate(native['geometry']['proxy_details'][family]):
            ids=[order[i] for i in row['i_seqs']+row.get('j_seqs',[])]
            if set(ids)&set(selected):
                _need(set(ids)&set(selected)<=c1|base_indices,'Unexpected moving atom in coupled base planes')
                if family=='planarity':
                    weights=row['weights']
                    _need(len(ids)>=4 and len(weights)==len(ids) and all(math.isfinite(w) and w>0 for w in weights),
                          'Unqualified C1-dependent monomer plane')
                    if len({(rows[i]["chain"],rows[i]["residue_number"]) for i in ids})==1:
                        monomers.extend(set(ids)&c1)
                        if include_bases:
                            plane_site=(rows[ids[0]]['chain'] or '_')+':'+str(rows[ids[0]]['residue_number'])
                            _need(base_by_site.get(plane_site,set())<=set(ids),
                                  'Endpoint base release requires its complete positive native monomer plane')
                planes.append(dict(family=family,ordinal=ordinal,source_indices=ids))
    _need(sorted(monomers)==sorted(c1),'Require one native C1-dependent monomer plane per sugar')
    result=dict(schema_version=1,kind='topostitch-coupled-sugar-scope',source_sha256=sha256(source).hexdigest(),
        movable_indices=selected,sites=[dict(site=s,component=c) for s,c in sorted(sites.items())],
        native_to_source=list(order),local_bonds=local,sugar_hands=hands,
        fixed_phosphate_indices=anchors,c1_dependent_planes=planes,scientific_acceptance=False)
    if include_bases:
        result.update(movement_scope='coupled-endpoints',base_indices=sorted(base_indices),
                      canonical_base_roles=base_map,canonical_base_roles_sha256=recipe_digest(base_map))
    return result


def review_coupled_geometry(scope, reference, initial, returned, points, *, fixed_owner, proxy_owner):
    """Compare actual live definitions, then measure hands with the existing owner."""
    counts={}
    for family in reference['geometry']['proxy_details']:
        old=proxy_owner._proxy_subset(reference,set(),family)
        first=proxy_owner._proxy_subset(initial,set(),family)
        last=proxy_owner._proxy_subset(returned,set(),family)
        _need(not old-first and first==last,'Coupled native proxy definitions changed: '+family)
        extra=sum((first-old).values());expected={'angle':4,'bond_asu':1,'dihedral':3}.get(family,0)
        _need(extra==expected,'Unexpected added coupled native definitions: '+family)
        counts[family]=dict(original=sum(old.values()),active=sum(first.values()),added=extra)
    measured=fixed_owner.review_fixed_coordinates(reference,[points[i] for i in scope['native_to_source']])
    expected={tuple(row['source_indices']):row['target'] for row in scope['sugar_hands']}
    hands=[]
    for row in measured['measurements']['chirality']:
        ids=tuple(scope['native_to_source'][i] for i in row['i_seqs'])
        if ids in expected:
            _need(row['target']==expected[ids] and row['sign_agreement'] is True
                  and row['status']=='MEASURED' and row.get('both_signs') is False,
                  'Returned coupled sugar lost its source-relative hand')
            hands.append(dict(source_indices=list(ids),observed=row['observed'],target=row['target']))
    _need(len(hands)==6,'Incomplete returned sugar-hand observation')
    return dict(status='NATIVE_SCOPE_REVIEWED',proxy_counts=counts,sugar_hands=hands,
                absolute_stereochemistry='UNASSESSED',packing_acceptance='UNASSESSED',scientific_acceptance=False)


@contextmanager
def observe_coupled_native(collector, *, phase, root, save, read):
    """Retain the actual interpretation and observe it without a second parser."""
    from functools import wraps
    from unittest.mock import patch
    from mmtbx.model import manager as Model
    from phenix.refinement.driver import refine as Driver
    retained=[];initialized=[];geometry_path=[];finished=[]
    unset=Model.unset_processed_pdb_file;before=Driver.write_before_run_outputs
    @wraps(unset)
    def remember(model):
        if model._processed_pdb_file is not None:retained.append(model._processed_pdb_file)
        return unset(model)
    def capture(model):
        processed=model._processed_pdb_file
        if processed is None:
            matches={id(p):p for p in retained if p.all_chain_proxies.pdb_hierarchy is model.get_hierarchy()}
            _need(len(matches)==1,'Cannot bind coupled manager to its exact original interpretation')
            processed=next(iter(matches.values()))
        return collector(model,processed=processed)
    @wraps(before)
    def observe(refined,*a,**kw):
        _need(not initialized,'Repeated coupled native initialization')
        observed=capture(refined.model);initialized.append(observed)
        save(Path('coupled-initial.json'),observed)
        if phase=='fit':
            prior=read((root/'preflight/coupled-initial.json').read_bytes())
            _need(observed['native_view']['geometry']['proxy_details']==prior['native_view']['geometry']['proxy_details'],
                  'Coupled fit starts with different native definitions from preflight')
        # Phenix writes initial and final geometry to distinct declared outputs.
        extension='_final.geo' if phase=='fit' else '.geo'
        geo=Path(refined.ofm.get_file_name(ext=extension)).absolute()
        _need(geo.is_relative_to(Path.cwd()),'Native geometry output leaves the owned phase')
        geometry_path.append(geo)
        return before(refined,*a,**kw)
    def finish(refined):
        _need(len(initialized)==1 and not finished,'Missing or repeated coupled native return')
        finished.append(True)
        observed=capture(refined.model)
        _need(observed['native_view']['geometry']['proxy_details']==initialized[0]['native_view']['geometry']['proxy_details'],
              'Coupled native definitions changed during execution')
        save(Path('coupled-returned.json'),observed)
        geo=geometry_path[0]
        _need(geo.is_file() and not geo.is_symlink(),'Missing exact native geometry output')
        return dict(anchor='phase',path=str(geo.relative_to(Path.cwd())),sha256=sha256(geo.read_bytes()).hexdigest())
    with patch.object(Model,'unset_processed_pdb_file',remember),patch.object(Driver,'write_before_run_outputs',observe):
        yield finish
        _need(Model.unset_processed_pdb_file is remember and Driver.write_before_run_outputs is observe,
              'Coupled native observation hooks changed during execution')
        _need(len(finished)==1,'Coupled native return was not observed')
    _need(Model.unset_processed_pdb_file is unset and Driver.write_before_run_outputs is before,
          'Coupled native observation hooks not restored')


def observe_post_exit_packing(model, *, runtime, capture, policy_snapshot, state_snapshot):
    """Raw Cedar ASU capture after restoration, not full-capture authentication.

    This performs two additional energy evaluations and may update native caches.
    The phosphate runtime has released its temporary angle/torsion terms; the
    reported total target is therefore not the refinement objective. Fixed
    nonbonded policy and returned scientific state must remain unchanged.
    """
    geo=model.restraints_manager.geometry
    _need(runtime.restored is True and geo in runtime.owned,
          'Packing observation requires the restored owner of this returned manager')
    before=state_snapshot();policy_before=policy_snapshot(geo)
    points=[[float(v) for v in p] for p in model.get_sites_cart()]
    raw=capture(geo,points)
    policy_after=policy_snapshot(geo)
    _need(before==state_snapshot(),'Post-exit packing observation changed model or observations')
    _need(policy_before['policy_sha256']==policy_after['policy_sha256'],
          'Post-exit packing observation changed fixed nonbonded policy')
    _need(raw.get('evaluation_calls')==2 and len(raw.get('snapshots',()))==2,
          'Unexpected post-exit packing evaluation count')
    return dict(schema_version=1,kind='topostitch-raw-post-exit-packing',
        raw_native=raw,policy_before=policy_before,policy_after=policy_after,
        extra_evaluation_calls=2,model_and_observations_unchanged=True,
        packing_acceptance='UNASSESSED',scientific_acceptance=False,
        limitations=[
            'Separate evaluations after runtime exit; native caches may change.',
            'Temporary phosphate angle/torsion terms have been released; total energy is not the refinement objective.',
            'Raw directed-pair observation only; no full native capture authentication, packing acceptance or independent neighbor enumeration.'])
