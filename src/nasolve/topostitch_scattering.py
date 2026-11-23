"""Independent sampled scattering observations for registered image previews.

Use Gemmi's complete crystal-image direct sum, not the graph-edge arithmetic.
This is an in-memory diagnostic, with no coordinate writer or acceptance policy.
"""
from __future__ import annotations

from hashlib import sha256
import importlib
import math
from pathlib import Path

from .topostitch_preview import _atom_identity
from .topostitch_recut import preview_registered_relabel
from .topostitch_registration import _fingerprint


def _reflections(hkls):
    if not isinstance(hkls,(list,tuple)) or not 1<=len(hkls)<=4096:
        raise ValueError('Require 1-4096 explicit Miller indices')
    values=[]
    for hkl in hkls:
        if (not isinstance(hkl,(list,tuple)) or len(hkl)!=3
                or any(type(v) is not int or abs(v)>10000 for v in hkl)):
            raise ValueError('Miller indices must be bounded integer triples')
        values.append(tuple(hkl))
    if len(set(values))!=len(values):raise ValueError('Duplicate Miller indices')
    return values


def _structure(data, orbit):
    import gemmi
    lines=data.decode('ascii').splitlines()
    atom_lines=[line for line in lines if line[:6].strip() in ('ATOM','HETATM')]
    identities={_atom_identity(line):i for i,line in enumerate(atom_lines)}
    if len(identities)!=len(atom_lines):raise ValueError('Ambiguous scattering atom identities')
    anisou={}
    for line in lines:
        if line.startswith('ANISOU'):
            key=_atom_identity(line)
            if key not in identities or key in anisou:
                raise ValueError('Orphan, mismatched or duplicate ANISOU record')
            try:values=[int(line[a:a+7])*1e-4 for a in (28,35,42,49,56,63)]
            except ValueError as exc:raise ValueError('Malformed ANISOU tensor') from exc
            tensor=gemmi.SMat33d(*values)
            if not tensor.nonzero() or min(tensor.calculate_eigenvalues())<0:
                raise ValueError('ANISOU tensor must be nonzero and positive semidefinite')
            anisou[key]=values
    structure=gemmi.read_pdb_string(data.decode('ascii'))
    if len(structure)!=1:raise ValueError('Require exactly one scattering model')
    if structure.ncs or any(line.startswith('MTRIX') for line in lines):
        raise ValueError('NCS image expansion is outside the representative scattering scope')
    atoms=[cra for cra in structure[0].all()]
    if len(atoms)!=len(atom_lines) or len(atoms)!=len(orbit['atoms']):
        raise ValueError('Scattering parser changed the source atom count')
    for i,(cra,line,observed) in enumerate(zip(atoms,atom_lines,orbit['atoms'])):
        a=cra.atom;identity=observed['identity']
        actual=dict(chain=cra.chain.name,residue_number=cra.residue.seqid.num,
                    insertion_code=cra.residue.seqid.icode.strip(),residue_code=cra.residue.name,
                    atom_name=a.name,altloc=a.altloc.replace('\x00','').strip())
        if actual!=identity or list(a.pos)!=observed['position_angstrom']:
            raise ValueError('Scattering parser changed source atom identity/order or coordinates')
        explicit_element=line[76:78].strip()
        if not explicit_element or gemmi.Element(explicit_element).atomic_number==0 or a.element!=gemmi.Element(explicit_element) or a.element.it92 is None:
            raise ValueError('Require explicit recognized elements with available X-ray scattering coefficients')
        try:occupancy=float(line[54:60]);b_iso=float(line[60:66])
        except ValueError as exc:raise ValueError('Require explicit occupancy and displacement parameters') from exc
        if not math.isfinite(occupancy) or not 0<=occupancy<=1 or not math.isfinite(b_iso) or b_iso<0:
            raise ValueError('Unsupported occupancy or isotropic displacement parameter')
        if not all(math.isfinite(x) for x in (a.occ,a.b_iso,*a.aniso.elements_pdb())):
            raise ValueError('Nonfinite parsed scattering parameter')
        # PDB integer scaling and Atom storage both round to float32 in Gemmi.
        if _atom_identity(line) in anisou and any(abs(a-b)>abs(b)*2**-22+2**-149
                for a,b in zip(a.aniso.elements_pdb(),anisou[_atom_identity(line)])):
            raise ValueError('Scattering parser changed an anisotropic tensor beyond float32 readback')
        if a.aniso.nonzero()!=(_atom_identity(line) in anisou):
            raise ValueError('Scattering parser changed anisotropic displacement inventory')
    structure.setup_cell_images()
    return structure,atoms,len(anisou)


def observe_registered_relabel_scattering(model,discovery,registration,*,node_images,
        expected_registered_graph_sha256,hkls,extra_edges=(),backbone_continuations=(),
        coincidence_tolerance_angstrom=.01,max_atom_tests=2_000_000,
        max_structure_factor_terms=5_000_000):
    """Observe unrefined complex Fcalc at explicit reflections before/after a cut.

    Rebuild the existing registered preview against exact source inputs. Apply
    its coordinates in memory and rotate Cartesian U by Gemmi's independent
    cell-operator matrix. The complete crystal-image direct sum includes every
    present atom; missing content/special-position multiplicity remain unqualified.
    No numerical acceptance threshold or physical approval is inferred.
    """
    indices=_reflections(hkls)
    if type(max_structure_factor_terms) is not int or not 1<=max_structure_factor_terms<=100_000_000:
        raise ValueError('Require a bounded positive structure-factor work budget')
    paths=[Path(p) for p in (model,discovery,registration)]
    originals={p:p.read_bytes() for p in paths}
    preview=preview_registered_relabel(*paths,node_images=node_images,
        expected_registered_graph_sha256=expected_registered_graph_sha256,extra_edges=extra_edges,
        backbone_continuations=backbone_continuations,
        coincidence_tolerance_angstrom=coincidence_tolerance_angstrom,max_atom_tests=max_atom_tests)
    import gemmi
    source,source_atoms,anisou_count=_structure(originals[paths[0]],preview['source_orbit_observation'])
    group=source.find_spacegroup();operations=group.operations()
    if not any(any(h) and not operations.is_systematically_absent(h) for h in indices):
        raise ValueError('Include at least one allowed nonzero reflection; F000/absences alone cannot test a cut')
    if len(source.cell.images)+1!=len(operations):
        raise ValueError('Scattering image inventory differs from the declared crystal group')
    terms=2*len(source_atoms)*len(operations)*len(indices)
    if terms>max_structure_factor_terms:raise ValueError('Structure-factor work budget exceeded')
    proposed=source.clone();target_atoms=[cra.atom for cra in proposed[0].all()]
    for atom,point in zip(target_atoms,preview['proposed_points_angstrom']):atom.pos=gemmi.Position(*point)
    transported=[]
    for row in preview['atom_image_groups']:
        transform=source.cell.op_as_transform(gemmi.Op(row['operator_xyz']))
        for i in row['atom_indices']:
            atom=target_atoms[i]
            if atom.aniso.nonzero():
                before=list(atom.aniso.elements_pdb())
                atom.aniso=atom.aniso.transformed_by(transform.mat)
                transported.append(dict(atom_index=i,operator_xyz=row['operator_xyz'],
                    before_u_cart_angstrom_squared=before,
                    after_u_cart_angstrom_squared=list(atom.aniso.elements_pdb())))
    def signature(atom):
        return (atom.name,atom.altloc,atom.element.name,atom.charge,atom.occ,atom.b_iso)
    fixed=set(preview['fixed_atom_indices'])
    for i,(cra,atom) in enumerate(zip(source_atoms,target_atoms)):
        if signature(cra.atom)!=signature(atom):raise ValueError('Scattering metadata changed during representative preview')
        if i in fixed and (list(cra.atom.pos)!=list(atom.pos) or cra.atom.aniso.elements_pdb()!=atom.aniso.elements_pdb()):
            raise ValueError('Fixed context changed during scattering preview')
    # Gemmi's IT92 charge switch and coefficient table are process-global.
    # Observe their state; never change another caller's scattering policy.
    def coefficients():
        if not gemmi.IT92_get_ignore_charge():
            raise ValueError('Scattering observation requires the neutral IT92 charge policy')
        return {element:dict(a=gemmi.Element(element).it92.a,b=gemmi.Element(element).it92.b,
                             c=gemmi.Element(element).it92.c)
                for element in sorted({cra.atom.element.name for cra in source_atoms})}
    factors=coefficients()
    calc=gemmi.StructureFactorCalculatorX(source.cell)
    rows=[]
    for hkl in indices:
        before=calc.calculate_sf_from_model(source[0],hkl)
        after=calc.calculate_sf_from_model(proposed[0],hkl)
        if not all(math.isfinite(v) for v in (before.real,before.imag,after.real,after.imag)):
            raise ValueError('Nonfinite calculated structure factor')
        rows.append(dict(hkl=list(hkl),systematically_absent=operations.is_systematically_absent(hkl),
            before_complex=[before.real,before.imag],after_complex=[after.real,after.imag],
            absolute_complex_difference=abs(after-before)))
    if coefficients()!=factors:raise ValueError('Scattering factor policy changed during observation')
    norm=math.hypot(*(abs(complex(*row['before_complex'])) for row in rows))
    delta=math.hypot(*(row['absolute_complex_difference'] for row in rows))
    kernel=Path(importlib.import_module('gemmi.gemmi_ext').__file__)
    report=dict(schema_version=1,kind='topostitch-registered-relabel-scattering-observation',
        status='OBSERVED_REVIEW_REQUIRED',source_model_sha256=preview['source_model_sha256'],
        registered_graph_sha256=expected_registered_graph_sha256,preview_sha256=preview['preview_sha256'],
        form_factor_coefficients=factors,form_factor_sha256=_fingerprint(factors),
        gemmi_version=gemmi.__version__,gemmi_kernel_sha256=sha256(kernel.read_bytes()).hexdigest(),
        crystal=preview['registered_graph']['periodic_graph']['crystal'],atom_count=len(source_atoms),
        anisou_count=anisou_count,transported_anisou=transported,space_group_image_count=len(operations),
        structure_factor_terms=terms,max_structure_factor_terms=max_structure_factor_terms,
        reflections=rows,maximum_absolute_complex_difference=max(row['absolute_complex_difference'] for row in rows),
        relative_l2_complex_difference=delta/norm if norm else None,
        source_orbit_status=preview['source_orbit_observation']['assessment'],
        source_bytes_verified=True,unrefined=True,coordinates_materialized=False,scattering_invariance_validated=False,
        scientific_acceptance=False,runtime_authority=False,
        policy=dict(scattering='Gemmi neutral-atom X-ray direct sum; no anomalous addends, bulk solvent or scale fit',
            anisotropic_transport='Cartesian U rotated in memory; Gemmi Atom stores SMat33f float32 values',
            isotropic_parameters='Unchanged; nonzero anisotropic U takes precedence in Gemmi',
            reflection_coverage='Explicit sampled reflections only; not all reciprocal space',
            numerical_acceptance_threshold=None),
        limitations=['All present atoms retained; missing atoms and special-position/occupancy/molecular identity remain unresolved',
            'No PDB rounding/serialization, symmetry restraint, refinement, GUI approval or editable topology mutation'])
    if any(p.read_bytes()!=value for p,value in originals.items()):raise ValueError('Scattering source inputs changed during observation')
    report['report_sha256']=_fingerprint(report)
    return report


def _parsed_identity(cra):
    return dict(chain=cra.chain.name, residue_number=cra.residue.seqid.num,
        insertion_code=cra.residue.seqid.icode.strip(), residue_code=cra.residue.name,
        atom_name=cra.atom.name, altloc=cra.atom.altloc.replace('\x00','').strip())


def _serialized_structure(data, coordinate_format):
    """Read explicit scattering fields; never accept parser-filled missing values."""
    import gemmi
    try:
        text = data.decode('ascii')
        if coordinate_format == 'pdb':
            parsed = gemmi.read_pdb_string(text)
            if len(parsed) != 1: raise ValueError('Require exactly one serialized model')
            orbit = dict(atoms=[dict(identity=_parsed_identity(c), position_angstrom=list(c.atom.pos))
                               for c in parsed[0].all()])
            return _structure(data, orbit)[0]
        if coordinate_format != 'mmcif':
            raise ValueError('Require an explicit pdb or mmcif coordinate format')
        document = gemmi.cif.read_string(text)
        if len(document) != 1: raise ValueError('Require exactly one coordinate CIF block')
        block = document.sole_block()
        table = block.find_mmcif_category('_atom_site.')
        required = ('id','group_PDB','type_symbol','label_atom_id','label_comp_id',
                    'auth_asym_id','auth_seq_id','Cartn_x','Cartn_y','Cartn_z','occupancy','B_iso_or_equiv')
        tags = list(table.tags)
        if not len(table) or any('_atom_site.'+t not in tags for t in required):
            raise ValueError('Require explicit serialized atom identity and scattering fields')
        columns = {t:tags.index('_atom_site.'+t) for t in required}
        ids=[];identities=[]
        for row in table:
            values={t:gemmi.cif.as_string(row[i]) for t,i in columns.items()}
            if any(row[columns[t]] in ('.','?') for t in required):
                raise ValueError('Missing serialized atom identity or scattering field')
            if values['group_PDB'] not in ('ATOM','HETATM'):
                raise ValueError('Unsupported serialized record type')
            numbers = [float(values[t]) for t in ('Cartn_x','Cartn_y','Cartn_z','occupancy','B_iso_or_equiv')]
            if not all(math.isfinite(v) for v in numbers) or not 0<=numbers[3]<=1 or numbers[4]<0:
                raise ValueError('Invalid serialized scattering parameters')
            ids.append(values['id'])
            identities.append((values['auth_asym_id'],int(values['auth_seq_id']),
                               values['label_comp_id'],values['label_atom_id'],values['group_PDB']))
        id_set=set(ids)
        if len(id_set)!=len(ids): raise ValueError('Duplicate serialized atom-site identifiers')
        adp = block.find_mmcif_category('_atom_site_anisotrop.');aniso_ids=set()
        if len(adp):
            names=['_atom_site_anisotrop.id']+['_atom_site_anisotrop.U'+s for s in
                ('[1][1]','[2][2]','[3][3]','[1][2]','[1][3]','[2][3]')]
            if any(n not in list(adp.tags) for n in names):
                raise ValueError('Require explicit six-component Cartesian U in coordinate CIF')
            indices=[list(adp.tags).index(n)for n in names]
            for row in adp:
                key=gemmi.cif.as_string(row[indices[0]])
                if key not in id_set or key in aniso_ids:
                    raise ValueError('Orphan or duplicate serialized anisotropic tensor')
                values=[float(row[i])for i in indices[1:]]
                if not all(math.isfinite(v)for v in values) or not any(values) or min(gemmi.SMat33d(*values).calculate_eigenvalues())<0:
                    raise ValueError('Invalid serialized Cartesian anisotropic tensor')
                aniso_ids.add(key)
        structure=gemmi.make_structure_from_block(block)
        if len(structure)!=1 or len(list(structure[0].all()))!=len(ids):
            raise ValueError('Coordinate CIF parser changed model or atom multiplicity')
        if structure.ncs or len(block.find_mmcif_category('_struct_ncs_oper.')):
            raise ValueError('NCS expansion is outside serialized representative scope')
        for cra,key,expected in zip(structure[0].all(),ids,identities):
            actual=(cra.chain.name,cra.residue.seqid.num,cra.residue.name,cra.atom.name,
                    'ATOM' if cra.residue.het_flag=='A' else 'HETATM')
            if actual!=expected or cra.atom.aniso.nonzero()!=(key in aniso_ids):
                raise ValueError('Coordinate CIF parser changed ordered identity or ADP inventory')
        return structure
    except (RuntimeError,UnicodeError,OverflowError,TypeError) as exc:
        raise ValueError('Unsupported or malformed serialized coordinate model') from exc


def _observe_serialized_relabel(source_data, export_data, *, preview, frame,
        coordinate_format, coordinate_bound, u_bound):
    """Compare the complete labelled exported state with the represented Gemmi state."""
    import gemmi
    for value in (coordinate_bound,u_bound):
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('Require explicit finite nonnegative serialization precision bounds')
    source,source_atoms,anisou_count=_structure(source_data,preview['source_orbit_observation'])
    exported=_serialized_structure(export_data,coordinate_format)
    if (exported.cell.parameters!=source.cell.parameters or exported.find_spacegroup() is None
            or exported.find_spacegroup().hall!=source.find_spacegroup().hall):
        raise ValueError('Serialized crystal cell or group differs from the source frame')
    actual=list(exported[0].all());keys=[_fingerprint(_parsed_identity(c))for c in actual]
    expected_keys=[_fingerprint(atom['identity'])for atom in preview['source_orbit_observation']['atoms']]
    if len(keys)!=len(expected_keys) or len(set(keys))!=len(keys) or set(keys)!=set(expected_keys):
        raise ValueError('Serialized atom identity or multiplicity differs from complete source')
    lookup={key:i for i,key in enumerate(keys)};order=[lookup[k]for k in expected_keys]
    actual=[actual[i]for i in order]
    def metadata(cra):
        a=cra.atom
        return cra.residue.het_flag,a.element.name,a.charge,a.occ,a.b_iso,a.aniso.nonzero()
    if any(metadata(a)!=metadata(b)for a,b in zip(source_atoms,actual)):
        raise ValueError('Serialized element, record type, charge, B/Q or ADP mode changed')
    kwargs=dict(source_labels=frame.source_labels,context_sha256=frame.context_sha256)
    expected_xyz=frame.to_representatives([list(c.atom.pos)for c in source_atoms],**kwargs)
    # State precision is explicit: source Atom and rotated target Atom U are float32.
    expected_u=[list(gemmi.SMat33f(*u).elements_pdb())for u in frame.tensors_to_representatives(
        [list(c.atom.aniso.elements_pdb())for c in source_atoms],**kwargs)]
    actual_xyz=[list(c.atom.pos)for c in actual];actual_u=[list(c.atom.aniso.elements_pdb())for c in actual]
    if not all(math.isfinite(v)for rows in (actual_xyz,actual_u)for row in rows for v in row):
        raise ValueError('Nonfinite serialized coordinate or displacement tensor')
    coordinate_errors=[max(abs(x-y)for x,y in zip(a,b))for a,b in zip(actual_xyz,expected_xyz)]
    u_errors=[max(abs(x-y)for x,y in zip(a,b))for a,b in zip(actual_u,expected_u)]
    return dict(atom_count=len(actual),anisou_count=anisou_count,
        identity_mapping=dict(source_order_retained=order==list(range(len(order))),source_to_export_indices=order),
        maximum_coordinate_component_error_angstrom=max(coordinate_errors),
        maximum_u_component_error_angstrom_squared=max(u_errors),
        atoms_exceeding_coordinate_bound=sum(x>coordinate_bound for x in coordinate_errors),
        atoms_exceeding_u_bound=sum(x>u_bound for x in u_errors),
        within_requested_precision=max(coordinate_errors)<=coordinate_bound and max(u_errors)<=u_bound,
        precision=dict(max_coordinate_component_error_angstrom=coordinate_bound,
                       max_u_component_error_angstrom_squared=u_bound,
                       state='Represented Gemmi float32 Atom U; not full-precision native scattering state'),
        annotations=dict(parsed_connection_count=len(exported.connections),declared_graph_verified_in_file=False),
        crystal=preview['registered_graph']['periodic_graph']['crystal']),actual_xyz
