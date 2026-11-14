"""Optional native evaluation of frozen canonical pair energies.

No native manager/callback is modified. A caller must compose this unnormalized
additive objective with a qualified native geometry/movement policy explicitly.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

from .topostitch_recipe import KIND, POLICY, model_atom_rows, recipe_digest
from .topostitch_transport import CartesianImage, IDENTITY_IMAGE, expand_sites, accumulate_image_gradients

CORRECTION_ID = 'native-parallelity-both-first-planes-v1'
_ALLOWED = {
    'bond': {'action','atom_selection_1','atom_selection_2','distance_ideal','sigma'},
    'angle': {'action','atom_selection_1','atom_selection_2','atom_selection_3','angle_ideal','sigma'},
    'planarity': {'action','atom_selection','sigma'},
    'parallelity': {'action','atom_selection_1','atom_selection_2','target_angle_deg','sigma'},
}


def native_atom_identities(hierarchy):
    rows = []
    for atom in hierarchy.atoms():
        label = atom.fetch_labels()
        rows.append({'chain': label.chain_id.strip(), 'residue_number': int(label.resseq),
            'insertion_code': label.icode.strip(), 'residue_code': label.resname.strip(),
            'atom_name': atom.name.strip(), 'altloc': label.altloc.strip()})
    return rows


def _positive(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Require finite positive recipe ideal/sigma')
    return value


class NativePairRecipe:
    """Bind one exact packet and model; evaluate under explicit atom ordering.

    `correction` is a caller-supplied trusted Cedar module, never captured text.
    Phenix imports are delayed until construction. No Gemmi/NARestraints import
    is required in the native interpreter because their effective recipe is frozen.
    """
    def __init__(self, packet, model_bytes, *, expected_recipe_sha256, correction):
        from iotbx import pdb, phil
        from mmtbx.command_line import pdb_interpretation
        from cctbx import geometry_restraints as gr, sgtbx
        from scitbx import matrix
        from scitbx.array_family import flex
        if recipe_digest(packet) != expected_recipe_sha256:
            raise ValueError('Recipe checksum mismatch')
        # Detach from mutable caller data before compiling or retaining it.
        packet = json.loads(json.dumps(packet, allow_nan=False))
        if (packet.get('schema_version') != 1 or type(packet['schema_version']) is not int
                or packet.get('kind') != KIND or packet.get('policy') != POLICY
                or packet.get('runtime_authority') is not False
                or packet.get('scientific_acceptance') is not False
                or packet.get('connection_capacity_validated') is not False):
            raise ValueError('Unsupported recipe schema or policy')
        if not isinstance(model_bytes, bytes) or sha256(model_bytes).hexdigest() != packet['source_model_sha256']:
            raise ValueError('Source model checksum mismatch')
        identities = model_atom_rows(model_bytes)
        if identities != packet['atom_identities'] or len(identities) != packet['atom_count']:
            raise ValueError('Recipe atom inventory differs from source model')
        effective = packet['library']['effective']
        if (recipe_digest(effective) != packet['library']['effective_sha256']
                or effective['emitted_recipes'] != [p['phil'] for p in packet['pairs']]):
            raise ValueError('Effective recipe library does not reproduce')
        if not 1 <= len(packet['pairs']) <= 1000:
            raise ValueError('Recipe pair budget exceeded')
        if correction.ORDER_CORRECTION_ID != CORRECTION_ID:
            raise ValueError('Require the qualified Cedar plane-order correction')
        self._gr, self._flex, self._correction = gr, flex, correction
        self._identities = identities
        self._count = len(identities)
        self._refs, self._terms = [], []
        self._bonds = gr.shared_bond_simple_proxy()
        self._angles = gr.shared_angle_proxy()
        self._planes = gr.shared_planarity_proxy()
        self._parallel = gr.shared_parallelity_proxy()
        native_input = pdb.input(source_info=None, lines=model_bytes.decode('ascii'))
        hierarchy = native_input.construct_hierarchy(sort_atoms=False)
        if native_atom_identities(hierarchy) != identities:
            raise ValueError('Native interpretation reordered or renamed source atoms')
        crystal = native_input.crystal_symmetry()
        if crystal is None or any(abs(a-b) > 1e-10 for a,b in
                zip(crystal.unit_cell().parameters(), packet['crystal']['cell_parameters'])):
            raise ValueError('Native crystal cell differs from the frozen recipe')
        from cctbx import crystal as crystal_module
        declared = crystal_module.symmetry(unit_cell=packet['crystal']['cell_parameters'],
                                          space_group_symbol=packet['crystal']['space_group'])
        if declared.space_group() != crystal.space_group():
            raise ValueError('Native crystal group differs from the frozen recipe')
        unit_cell = crystal.unit_cell()
        orth, frac = matrix.sqr(unit_cell.orthogonalization_matrix()), matrix.sqr(unit_cell.fractionalization_matrix())
        source_rows = [l for l in model_bytes.decode('ascii').splitlines() if l[:6] in ('ATOM  ','HETATM')]
        seen_ids, seen_edges, term_keys = set(), set(), set()
        for pair in packet['pairs']:
            if pair['pair_id'] in seen_ids:
                raise ValueError('Duplicate pair identifier')
            seen_ids.add(pair['pair_id'])
            op = sgtbx.rt_mx(pair['target_operator_xyz'])
            if op.mod_positive() not in crystal.space_group():
                raise ValueError('Recipe operator does not belong to source crystal')
            sites = pair['sites']
            site_keys = [tuple(site[k] for k in ('chain','residue_number','insertion_code')) for site in sites]
            edge = (tuple(site_keys),op.as_xyz())
            inverse = (tuple(reversed(site_keys)),op.inverse().as_xyz())
            if edge in seen_edges or inverse in seen_edges or len(sites) != 2 or site_keys[0] == site_keys[1]:
                raise ValueError('Duplicate or unsupported pair image')
            seen_edges.add(edge)
            rotation = orth*matrix.sqr(op.r().as_double())*frac
            image = CartesianImage(tuple(tuple(rotation[3*i+j] for j in range(3)) for i in range(3)),
                                   tuple(unit_cell.orthogonalize(op.t().as_double())))
            virtual, local_refs, expected_planes = [], [], []
            for role, site, transform in zip(('L','R'), sites, (IDENTITY_IMAGE,image)):
                indices = [i for i,row in enumerate(identities) if all(row[k] == site[k] for k in ('chain','residue_number','insertion_code'))]
                if not indices or indices != pair['role_indices'][role]:
                    raise ValueError('Pair role atom inventory differs from source model')
                codes = {identities[i]['residue_code'] for i in indices}
                if len(codes) != 1 or next(iter(codes)) not in ('DA','DT','DG','DC'):
                    raise ValueError('Require canonical residue roles')
                code = next(iter(codes))
                needed = set(effective['atom_roles'][code].values())
                names = {identities[i]['atom_name'] for i in indices}
                if not needed <= names:
                    raise ValueError('Incomplete canonical plane/contact atoms')
                expected_plane = set()
                for i in indices:
                    ref_id = None
                    if identities[i]['atom_name'] in needed:
                        ref = (i,transform)
                        if ref not in self._refs:
                            self._refs.append(ref)
                        ref_id = self._refs.index(ref)
                        expected_plane.add(ref_id)
                    local_refs.append(ref_id)
                    line = source_rows[i]
                    virtual.append(line[:21]+role+'   1 '+line[27:])
                expected_planes.append(expected_plane)
                virtual.append('TER')
            virtual.append('END')
            cache = pdb.input(source_info=None, lines='\n'.join(virtual)+'\n').construct_hierarchy(sort_atoms=False).atom_selection_cache()
            text = pair['phil']
            if sha256(text.encode()).hexdigest() != pair['phil_sha256']:
                raise ValueError('Pair PHIL checksum mismatch')
            scope = phil.parse(text)
            for definition in scope.all_definitions():
                path = definition.path.split('.')
                if len(path) != 4 or path[:2] != ['geometry_restraints','edits'] or path[2] not in _ALLOWED or path[3] not in _ALLOWED[path[2]]:
                    raise ValueError('Unsupported field in frozen pair PHIL')
            params, unused = pdb_interpretation.get_master_phil().fetch(sources=[scope], track_unused_definitions=True)
            if unused:
                raise ValueError('Unconsumed pair PHIL definition')
            edits = params.extract().geometry_restraints.edits
            counts = {k:0 for k in _ALLOWED}
            def selection(expression, minimum, maximum=None):
                ids = [local_refs[i] for i in cache.iselection(expression)]
                if None in ids or len(ids) < minimum or (maximum is not None and len(ids) > maximum) or len(set(ids)) != len(ids):
                    raise ValueError('Incomplete or ambiguous recipe atom selection')
                return ids
            for kind in _ALLOWED:
                for term in getattr(edits,kind):
                    first = getattr(term,'atom_selection' if kind == 'planarity' else 'atom_selection_1')
                    if first is None:
                        continue
                    if term.action != 'add':
                        raise ValueError('Only additive pair-energy terms are supported')
                    sigma = _positive(term.sigma)
                    record = {'kind':kind,'pair_id':pair['pair_id'],'purpose':pair['purpose'],'sigma':sigma}
                    if kind in ('bond','angle'):
                        n = 2 if kind == 'bond' else 3
                        ids = [selection(getattr(term,'atom_selection_'+str(k)),1,1)[0] for k in range(1,n+1)]
                        if len(set(ids)) != n:
                            raise ValueError('Degenerate recipe atom indices')
                        ideal = _positive(getattr(term,'distance_ideal' if kind == 'bond' else 'angle_ideal'))
                        if kind == 'angle' and ideal >= 180:
                            raise ValueError('Unsupported linear pair angle')
                        record.update(i_seqs=ids,ideal=ideal)
                        key = (kind,min(tuple(ids),tuple(reversed(ids))))
                        if kind == 'bond':
                            self._bonds.append(gr.bond_simple_proxy(i_seqs=ids,distance_ideal=ideal,weight=1/sigma**2))
                        else:
                            self._angles.append(gr.angle_proxy(i_seqs=ids,angle_ideal=ideal,weight=1/sigma**2))
                    elif kind == 'planarity':
                        ids = selection(first,6)
                        if set(ids) != set.union(*expected_planes):
                            raise ValueError('Planarity selection omits or adds canonical atoms')
                        record['i_seqs'] = ids
                        key = (kind,tuple(sorted(ids)))
                        self._planes.append(gr.planarity_proxy(i_seqs=ids,weights=flex.double(len(ids),1/sigma**2)))
                    else:
                        ids, other = selection(first,3), selection(term.atom_selection_2,3)
                        if {frozenset(ids),frozenset(other)} != {frozenset(p) for p in expected_planes}:
                            raise ValueError('Parallelity selections omit or add canonical atoms')
                        if term.target_angle_deg != 0:
                            raise ValueError('Only canonical parallel planes are supported')
                        record.update(i_seqs=ids,j_seqs=other,ideal=0.)
                        key = (kind,tuple(sorted((tuple(sorted(ids)),tuple(sorted(other))))))
                        self._parallel.append(gr.parallelity_proxy(i_seqs=ids,j_seqs=other,weight=1/sigma**2,
                            target_angle_deg=0.,slack=0.,limit=1.,top_out=False))
                    if key in term_keys:
                        raise ValueError('Duplicate native recipe term')
                    term_keys.add(key)
                    self._terms.append(record)
                    counts[kind] += 1
            if counts != pair['expected_counts'] or any(not value for value in counts.values()):
                raise ValueError('Incomplete canonical term inventory')
        self._refs = tuple(self._refs)
        self._report = {'schema_version':1,'kind':'topostitch-native-pair-binding',
            'recipe_sha256':expected_recipe_sha256,'source_model_sha256':packet['source_model_sha256'],
            'atom_count':self._count,'terms':self._terms,
            'references':[{'asu_index':i,'rotation':image.rotation,'translation':image.translation} for i,image in self._refs],
            'correction_policy':CORRECTION_ID,
            'correction_source_sha256':sha256(Path(correction.__file__).read_bytes()).hexdigest(),
            'policy':dict(POLICY),'scientific_acceptance':False}

    def binding_report(self):
        return json.loads(json.dumps(self._report,allow_nan=False))

    def evaluate(self, points, *, atom_identities, compute_gradients=True):
        """Return component energies and ASU gradients, with no native attachment."""
        if atom_identities != self._identities or type(compute_gradients) is not bool:
            raise ValueError('Native atom order/identity or gradient request changed')
        points = list(points)
        if len(points) != self._count:
            raise ValueError('Native coordinate count changed')
        gr, flex = self._gr, self._flex
        expanded = flex.vec3_double(expand_sites(points,self._refs))
        gradient = flex.vec3_double(len(expanded),(0,0,0)) if compute_gradients else flex.vec3_double()
        values = {}
        for name,fn,proxies in [('bond',gr.bond_residual_sum,self._bonds),
                ('angle',gr.angle_residual_sum,self._angles),('planarity',gr.planarity_residual_sum,self._planes),
                ('parallelity',gr.parallelity_residual_sum,self._parallel)]:
            values[name] = float(fn(sites_cart=expanded,proxies=proxies,gradient_array=gradient))
        pulled = None
        if compute_gradients:
            corrected = self._correction.correct_parallelity_gradient(gr,flex,self._parallel,list(expanded),
                list(gradient.as_double()),native_residual=values['parallelity'],plane_order_safe=True)
            corrected = flex.vec3_double(flex.double(corrected['gradient']))
            pulled = accumulate_image_gradients(self._count,self._refs,list(corrected))
        total = math.fsum(values.values())
        if any(not math.isfinite(v) for v in (*values.values(),total)):
            raise ValueError('Nonfinite native recipe energy')
        return {'target':total,'components':values,'gradients':pulled,'normalization':POLICY['normalization']}


class NativeMaskedObjective:
    """Direct, bounded composition of native geometry, pair energy and a tether.

    This does not own native interpretation, capture authentication, optimization
    or refinement. The caller supplies the trusted Cedar audit/correction owners
    and a manager constructed from the exact source model. Static-definition
    checks do not freeze native nonbonded neighbours or prove capture provenance.
    """
    def __init__(self, geometry, native_hierarchy, model_bytes, pair_binding, *,
                 movable_indices, expected_native_signature, correction, native_audit,
                 tether_sigma_angstrom, max_displacement_angstrom, max_evaluations):
        from iotbx import pdb
        from cctbx import geometry_restraints as gr
        from cctbx.geometry_restraints import flags
        from scitbx.array_family import flex
        from .topostitch_transport import CoordinateMask
        if not isinstance(pair_binding, NativePairRecipe):
            raise ValueError('Require a compiled complete pair recipe')
        if type(max_evaluations) is not int or not 1 <= max_evaluations <= 100000:
            raise ValueError('Require an evaluation budget from 1 to 100000')
        sigma = _positive(tether_sigma_angstrom)
        try:
            weight = 1/(sigma*sigma)
        except (OverflowError,ZeroDivisionError) as exc:
            raise ValueError('Tether weight exceeds finite range') from exc
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError('Tether weight exceeds finite range')
        binding = pair_binding.binding_report()
        if sha256(model_bytes).hexdigest() != binding['source_model_sha256']:
            raise ValueError('Masked objective source differs from pair binding')
        inp = pdb.input(source_info=None, lines=model_bytes.decode('ascii'))
        source = inp.construct_hierarchy(sort_atoms=False)
        identities = model_atom_rows(model_bytes)
        if native_atom_identities(native_hierarchy) != identities:
            raise ValueError('Native hierarchy order/identity differs from source model')
        points = tuple(source.atoms().extract_xyz())
        native_points = tuple(native_hierarchy.atoms().extract_xyz())
        roundoff = max(abs(a-b) for p,q in zip(points,native_points) for a,b in zip(p,q))
        if roundoff > 1e-10:
            raise ValueError('Native starting coordinates differ from source beyond roundoff')
        self._hierarchy_reference = native_points
        self._mask = CoordinateMask(points,movable_indices,max_displacement_angstrom)
        if (correction.ORDER_CORRECTION_ID != CORRECTION_ID
                or sha256(Path(correction.__file__).read_bytes()).hexdigest() != binding['correction_source_sha256']):
            raise ValueError('Native and pair corrections must use the same trusted source')
        self._geometry, self._hierarchy = geometry, native_hierarchy
        self._correction, self._audit = correction, native_audit
        self._gr, self._flex, self._flags = gr, flex, flags
        self._pairs, self._identities = pair_binding, identities
        self._signature = expected_native_signature
        self._crystal = inp.crystal_symmetry()
        self._tether_weight, self._max_calls, self._calls = weight,max_evaluations,0
        self._check_native(points)
        self._report = {'schema_version':1,'kind':'topostitch-masked-native-objective',
            'source_model_sha256':binding['source_model_sha256'],
            'pair_recipe_sha256':binding['recipe_sha256'],
            'native_static_definition_sha256':expected_native_signature,
            'correction_policy':CORRECTION_ID,
            'correction_source_sha256':binding['correction_source_sha256'],
            'native_audit_source_sha256':sha256(Path(native_audit.__file__).read_bytes()).hexdigest(),
            'movable_indices':list(self._mask.indices),
            'movable_atom_identities':[identities[i] for i in self._mask.indices],
            'native_starting_roundoff_angstrom':roundoff,
            'atom_count':len(points),'fixed_atom_count':len(points)-len(self._mask.indices),
            'tether_sigma_angstrom':sigma,'max_displacement_angstrom':self._mask.max_displacement_angstrom,
            'max_evaluations':max_evaluations,'normalization':'UNNORMALIZED_SUM',
            'component_weights':{'native':1.,'pair':1.,'tether':1.},
            'native_flags':'all ordinary geometry flags enabled',
            'native_bonded_tables_changed':False,'native_exclusions_changed':False,
            'native_callback_attached':False,'optimization':False,'scientific_acceptance':False,'runtime_authority':False,
            'limitations':['Caller owns trusted native construction and capture authentication',
                'Static-definition signature does not freeze nonbonded neighbours or qualify packing',
                'Explicit mask is not permission to move atoms or proof of complete chemistry',
                'No optimizer, manager rebuild, refinement or campaign lifecycle is qualified']}

    def _check_native(self, points):
        geo = self._geometry
        if native_atom_identities(self._hierarchy) != self._identities:
            raise ValueError('Native atom ordering changed after binding')
        if tuple(self._hierarchy.atoms().extract_xyz()) != self._hierarchy_reference:
            raise ValueError('Native reference hierarchy coordinates changed after binding')
        if geo.external_energy_function is not None:
            raise ValueError('An existing native external callback is unsupported')
        for name in ('reference_dihedral_manager','ncs_dihedral_manager','den_manager','ramachandran_manager'):
            if getattr(geo,name,None) is not None:
                raise ValueError('Unsupported auxiliary native geometry manager: '+name)
        if geo.reference_coordinate_proxies is not None and len(geo.reference_coordinate_proxies):
            raise ValueError('Native reference-coordinate proxies are unsupported')
        crystal = geo.crystal_symmetry
        if (crystal is None or crystal.space_group() != self._crystal.space_group()
                or any(abs(a-b)>1e-10 for a,b in zip(crystal.unit_cell().parameters(),self._crystal.unit_cell().parameters()))):
            raise ValueError('Native manager crystal differs from source model')
        table = geo.site_symmetry_table
        if (table is None or table.indices().size() != len(self._mask.reference)
                or len(table.special_position_indices())):
            raise ValueError('Require complete native identity without special-position constraints')
        if self._audit.fixed_signature(geo,self._flex.vec3_double(points)) != self._signature:
            raise ValueError('Native static definitions changed or differ from expected capture')

    def binding_report(self):
        return json.loads(json.dumps(self._report,allow_nan=False))

    def evaluate(self, displacements):
        """Evaluate only explicit displacement variables; every other atom stays fixed."""
        values = tuple(displacements)
        points = self._mask.expand(values)
        if self._calls >= self._max_calls:
            raise ValueError('Masked objective evaluation budget exhausted')
        self._calls += 1
        self._check_native(points)
        native = self._correction.evaluate_fixed_native(self._geometry,points,
            self._flags.flags(default=True),self._gr,self._flex,plane_order_safe=True)
        pair = self._pairs.evaluate(points,atom_identities=self._identities)
        full = tuple(tuple(native['gradient'][3*i+k]+pair['gradients'][i][k] for k in range(3))
                     for i in range(len(points)))
        tether = math.fsum(v*v*self._tether_weight for v in values)
        gradient = tuple(g+2*v*self._tether_weight for g,v in zip(self._mask.project(full),values))
        target = math.fsum((native['target'],pair['target'],tether))
        if not math.isfinite(target) or any(not math.isfinite(v) for v in gradient):
            raise ValueError('Nonfinite masked objective value or gradient')
        self._check_native(points)
        return {'target':target,'gradient':gradient,'points':points,
            'native_target':native['target'],'pair_target':pair['target'],'tether_target':tether,
            'native_components':native['terms'],'pair_components':pair['components'],
            'native_proxy_counts':native['proxy_counts'],'evaluation_calls':self._calls,
            'normalization':'UNNORMALIZED_SUM','fixed_coordinates_preserved':True}
