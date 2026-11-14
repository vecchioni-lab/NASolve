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
        expected_registered_graph_sha256,hkls,extra_edges=(),
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
