"""Source-bound assembly references and numerical crystal-image observation.

Curated and depositor operator IDs occupy separate namespaces. This observer
retains original rows and never writes assembly labels, coordinates or ADPs.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import math
from pathlib import Path
import re

from .topostitch_cif_annotations import _rows, _operations
from .topostitch_cif_fragments import observe_relabel_cif_fragments
from .topostitch_registration import _fingerprint
from .topostitch_transport import CartesianImage, crystallographic_image


def _cartesian(row):
    try:
        fields=[f'matrix[{i}][{j}]'for i in(1,2,3)for j in(1,2,3)]+[f'vector[{i}]'for i in(1,2,3)]
        if any(not isinstance(row.get(key),str)for key in fields):
            raise ValueError('CIF unknown/inapplicable is not a numeric zero')
        return CartesianImage([[float(row[f'matrix[{i}][{j}]'])for j in (1,2,3)]for i in (1,2,3)],
                              [float(row[f'vector[{i}]'])for i in (1,2,3)])
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Require complete finite proper Cartesian assembly operation') from exc


def _matches(image, cell, group, positions, declared, bounds):
    import gemmi
    result=[];frac=cell.frac.mat.tolist()
    fractional=[math.fsum(a*b for a,b in zip(row,image.translation))for row in frac]
    for base in group.operations():
        try:canonical=crystallographic_image(list(cell.parameters),group.xhm(),base.triplet())
        except ValueError:continue  # Improper images are outside the DNA transport owner.
        rotation_error=max(abs(a-b)for row,col in zip(image.rotation,canonical.rotation)for a,b in zip(row,col))
        if rotation_error>bounds['rotation_component']:continue
        shift=[int(round(a-b/base.DEN))for a,b in zip(fractional,base.tran)]
        op=base.translated([n*base.DEN for n in shift])
        exact=crystallographic_image(list(cell.parameters),group.xhm(),op.triplet())
        translation_error=max(abs(a-b)for a,b in zip(image.translation,exact.translation))
        if translation_error>bounds['translation_component_angstrom']:continue
        position_error=max((math.dist(image.apply(x),exact.apply(x))for x in positions),default=0.)
        if position_error>bounds['position_angstrom']:continue
        references=[]
        for identifier,original in declared.items():
            if original.rot==op.rot and all((a-b)%op.DEN==0 for a,b in zip(op.tran,original.tran)):
                references.append(dict(operation_id=identifier,lattice_shift_from_declared=[(a-b)//op.DEN for a,b in zip(op.tran,original.tran)]))
        result.append(dict(operator_xyz=op.triplet(),base_operator_xyz=base.triplet(),lattice_shift=shift,
            declared_operation_ids=[r['operation_id']for r in references],declared_operation_references=references,
            maximum_rotation_component_error=rotation_error,maximum_translation_component_error_angstrom=translation_error,
            maximum_source_position_error_angstrom=position_error))
    return result


def _inline_matrix(value, image, positions, bounds):
    if value in (None,False):return 'NOT_SUPPLIED'
    try:
        values=[float(v)for v in value.split()]
        if len(values)!=12:raise ValueError('Expected one three-by-four matrix')
        other=CartesianImage([values[i:i+3]for i in(0,4,8)],[values[i]for i in(3,7,11)])
        if (max(abs(a-b)for x,y in zip(image.rotation,other.rotation)for a,b in zip(x,y))>bounds['rotation_component']
                or max(abs(a-b)for a,b in zip(image.translation,other.translation))>bounds['translation_component_angstrom']
                or max((math.dist(image.apply(p),other.apply(p))for p in positions),default=0.)>bounds['position_angstrom']):
            return 'CONFLICT_OR_UNSUPPORTED'
    except (ValueError,AttributeError,TypeError,OverflowError):return 'CONFLICT_OR_UNSUPPORTED'
    return 'AGREES_WITH_OPERATOR'


def _counts(rows):return Counter(row.get('id')for row in rows)
def _known_id(value):return isinstance(value,str)and bool(value.strip())


def observe_relabel_cif_assemblies(directory, model, *, max_rotation_component_error,
        max_translation_component_error_angstrom, max_assembly_position_error_angstrom, **fragment_binding):
    """Observe simple assembly generators and retain every original namespace.

    Only single unparenthesized operator IDs are resolved. Lists, ranges, products,
    unknown and duplicate references remain explicit review items. Bounds describe
    declared matrix rounding, not permission to move a model or snap its values.
    Original Cartesian operations own the endpoint check; matching group operations
    are separately reported evidence, never substituted for the supplied matrices.
    """
    import gemmi
    from .topostitch_recut_bundle import _FILES
    from .topostitch_recut import _arithmetic_bound
    bounds=dict(rotation_component=max_rotation_component_error,
                translation_component_angstrom=max_translation_component_error_angstrom,
                position_angstrom=max_assembly_position_error_angstrom)
    limits=dict(rotation_component=1e-5,translation_component_angstrom=1e-3,position_angstrom=.01)
    if any(type(v)not in(int,float)or not math.isfinite(v)or not 0<=v<=limits[k]for k,v in bounds.items()):
        raise ValueError('Require explicit finite assembly rounding bounds within the supported precision limits')
    root=Path(directory);model=Path(model);manifest=root/'preview.json'
    frozen={p:p.read_bytes()for p in [model,manifest,*(root/n for n in _FILES.values())]}
    lineage=observe_relabel_cif_fragments(root,model,**fragment_binding)
    if any(p.read_bytes()!=data for p,data in frozen.items())or sha256(frozen[model]).hexdigest()!=lineage['original_model_sha256']:
        raise ValueError('Original CIF or preview changed during assembly observation')
    doc=gemmi.cif.read_string(frozen[model].decode('ascii'))
    block=next(b for b in doc if '_atom_site.'in b.get_mmcif_category_names())
    structure=gemmi.make_structure_from_block(block);cell=structure.cell;group=structure.find_spacegroup()
    if any(bounds['translation_component_angstrom']*sum(abs(v)for v in row)>=.5 for row in cell.frac.mat.tolist()):
        raise ValueError('Translation bound cannot distinguish integer lattice images in this cell')
    crystal=dict(cell_parameters=list(cell.parameters),space_group=group.xhm())
    atoms=_rows(block,'_atom_site.');points={a['id']:[float(a['Cartn_'+axis])for axis in 'xyz']for a in atoms}
    asym_rows=_rows(block,'_struct_asym.');asym_counts=_counts(asym_rows)
    sites={atom_id:(f['path_number'],s)for f in lineage['fragments']for s in f['sites']for atom_id in s['original_atom_ids']}
    raw={cat:_rows(block,cat)for cat in block.get_mmcif_category_names()
         if cat.startswith(('_pdbx_struct_assembly','_pdbx_struct_oper_list'))}
    try:declared,operation_issues=_operations(block,gemmi)
    except (RuntimeError,ValueError):declared={};operation_issues=['Malformed source symmetry operation table']
    for key,operation in list(declared.items()):
        try:crystallographic_image(**crystal,operator_xyz=operation.triplet())
        except ValueError:operation_issues.append('Source operation is outside supported proper crystal group: '+key)
    if operation_issues:declared={}
    namespaces={}
    for namespace,suffix in [('curated',''),('depositor','_depositor_info')]:
        ac='_pdbx_struct_assembly'+suffix+'.';gc='_pdbx_struct_assembly_gen'+suffix+'.';oc='_pdbx_struct_oper_list'+suffix+'.'
        assembly=raw.get(ac,[]);generators=raw.get(gc,[]);operators=raw.get(oc,[])
        assembly_counts=_counts(assembly);operator_counts=_counts(operators);observed=[];compiled={}
        for row in operators:
            key=row.get('id');issues=[];matches=[];image=None
            if not _known_id(key)or operator_counts[key]!=1:issues.append('Missing or duplicate operator ID in '+namespace)
            if row.get('full_matrix') not in (None,False):issues.append('Additional full_matrix declaration requires review')
            try:image=_cartesian(row)
            except ValueError as exc:issues.append(str(exc))
            if image is not None:
                expression=row.get('symmetry_operation')
                if expression not in (None,False):
                    try:
                        declared_image=crystallographic_image(**crystal,operator_xyz=expression)
                        inline=' '.join(str(v)for i,r in enumerate(declared_image.rotation)for v in (*r,declared_image.translation[i]))
                        if _inline_matrix(inline,image,points.values(),bounds)!='AGREES_WITH_OPERATOR':raise ValueError('Conflicting textual symmetry operation')
                    except (ValueError,TypeError):issues.append('Textual symmetry operation conflicts with the Cartesian matrix or is unsupported')
                try:matches=_matches(image,cell,group,points.values(),declared,bounds)
                except (ValueError,OverflowError,RuntimeError,TypeError):
                    issues.append('Assembly transform exceeds the supported numerical comparison range')
                if len(matches)!=1:issues.append('No unique crystal operation within declared rounding bounds')
            status='UNRESOLVED_REVIEW'if issues else'MATCH_WITHIN_DECLARED_BOUNDS'
            item=dict(raw_fields=row,status=status,issues=issues,symmetry_matches=matches)
            observed.append(item)
            if not issues:compiled[key]=(image,item)
        support=[dict(raw_fields=row,status='REFERENCE_RESOLVED_REVIEW_REQUIRED'if _known_id(row.get('assembly_id'))and assembly_counts[row['assembly_id']]==1 else'UNRESOLVED_REVIEW')for row in raw.get('_pdbx_struct_assembly_auth_evidence'+suffix+'.',[])]
        projected=[]
        for number,row in enumerate(generators,1):
            issues=list(operation_issues);assembly_id=row.get('assembly_id');expression=row.get('oper_expression')
            if not _known_id(assembly_id)or assembly_counts[assembly_id]!=1:issues.append('Missing or ambiguous assembly reference in '+namespace)
            if not isinstance(expression,str)or re.fullmatch(r'[A-Za-z0-9_]+',expression)is None:
                issues.append('Only one explicit unparenthesized operator ID is supported')
            elif expression not in compiled:issues.append('Unresolved operator reference in '+namespace)
            value=row.get('asym_id_list');chains=[]
            if not isinstance(value,str)or not value.strip():issues.append('Missing original label-asym membership')
            else:
                chains=[c.strip()for c in value.split(',')]
                if any(not c or asym_counts[c]!=1 for c in chains):issues.append('Unknown or ambiguous original label-asym reference')
                if len(set(chains))!=len(chains):issues.append('Duplicate original label-asym membership')
            selected=[a for a in atoms if a.get('label_asym_id')in chains];ids=[a['id']for a in selected]
            missing=[c for c in chains if not any(a.get('label_asym_id')==c for a in selected)]
            if missing:issues.append('Selected original label-asym has no observed atoms')
            unregistered=[a for a in ids if a not in sites]
            if unregistered:issues.append('Assembly includes atoms without registered fragment/image membership')
            if lineage['metadata_coverage_status']!='CONSISTENT_DECLARATIONS':issues.append('Original polymer declarations require review')
            inline_status='NOT_SUPPLIED'
            if expression in compiled:
                inline_status=_inline_matrix(row.get('full_matrices'),compiled[expression][0],points.values(),bounds)
                if inline_status=='CONFLICT_OR_UNSUPPORTED':issues.append('Inline generator matrix conflicts with its namespace operator or is unsupported')
            elif row.get('full_matrices')not in(None,False):inline_status='OPERATOR_UNRESOLVED'
            partitions=[];maximum=None
            if not issues:
                image,operator=compiled[expression];groups={}
                for atom in selected:
                    path,site=sites[atom['id']]
                    key=(path,atom['label_asym_id'],site['representative_operator_xyz'])
                    groups.setdefault(key,[]).append(atom['id'])
                maximum=0.
                for (path,original_asym,operation),members in groups.items():
                    representative=crystallographic_image(**crystal,operator_xyz=operation);inverse=representative.inverse()
                    rotation=[[math.fsum(a*b for a,b in zip(row,col))for col in zip(*inverse.rotation)]for row in image.rotation]
                    transformed=CartesianImage(rotation,image.apply(inverse.translation));error=0.
                    for atom_id in members:
                        point=points[atom_id];new=representative.apply(point);before=image.apply(point);after=transformed.apply(new)
                        delta=math.dist(before,after)
                        if delta>_arithmetic_bound(point,new,before,after):raise ValueError('Assembly transport changed an original physical endpoint')
                        error=max(error,delta)
                    maximum=max(maximum,error)
                    partitions.append(dict(path_number=path,original_label_asym_id=original_asym,
                        representative_image_xyz=operation,original_atom_ids=members,
                        proposed_cartesian_rotation=[list(r)for r in transformed.rotation],
                        proposed_cartesian_translation_angstrom=list(transformed.translation),
                        maximum_position_transport_error_angstrom=error))
            projected.append(dict(source_row_number=number,raw_fields=row,status='UNRESOLVED_REVIEW'if issues else'TRANSPORT_OBSERVED_REVIEW_REQUIRED',
                issues=issues,inline_matrix_status=inline_status,original_label_asym_ids=chains,member_atom_ids=ids,unregistered_atom_ids=unregistered,
                missing_coordinate_asym_ids=missing,partitions=partitions,maximum_position_transport_error_angstrom=maximum))
        namespaces[namespace]=dict(assembly_category=ac,generator_category=gc,operator_category=oc,
            assemblies=assembly,operators=observed,generators=projected,support_references=support)
    if any(p.read_bytes()!=data for p,data in frozen.items()):raise ValueError('Original CIF or preview changed during assembly observation')
    paths=[dict(path_number=f['path_number'],representative_images=sorted({s['representative_operator_xyz']for s in f['sites']}))for f in lineage['fragments']]
    report=dict(schema_version=1,kind='topostitch-original-cif-assembly-observation',status='OBSERVED_REVIEW_REQUIRED'if raw else'UNAVAILABLE',
        original_model_sha256=lineage['original_model_sha256'],preview_receipt_sha256=sha256(frozen[manifest]).hexdigest(),
        fragment_lineage_sha256=lineage['report_sha256'],crystal=crystal,rounding_bounds=bounds,
        original_categories=raw,original_symmetry_categories={cat:_rows(block,cat)for cat in ('_space_group_symop.','_symmetry_equiv.')if cat in block.get_mmcif_category_names()},
        source_operation_table_issues=operation_issues,namespaces=namespaces,
        paths=paths,mixed_image_path_numbers=[p['path_number']for p in paths if len(p['representative_images'])>1],
        coordinates_written=False,atom_adps_changed=False,output_identifiers_assigned=False,
        assembly_set_equivalence_proved=False,assembly_membership_physically_accepted=False,
        writer_authorized=False,runtime_authority=False,scientific_acceptance=False,
        limitations=['Only single unparenthesized operator IDs; lists/ranges/products retained for review',
            'Numerical proper crystal-image match does not authenticate author-defined biological assembly',
            'Original rounded Cartesian matrices own endpoint checks; matched exact crystal operations are not substituted',
            'Curated/depositor IDs remain separate; experimental support and all raw assembly rows remain unchanged',
            'Mixed-image paths need distinct instance corrections; no assembly-set equivalence or new oligomeric count inferred',
            'Transported ADPs, complete assembly multiplicity, output labels, native refinement and writer remain unqualified'])
    report['report_sha256']=_fingerprint(report)
    return report
