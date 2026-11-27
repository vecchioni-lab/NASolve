"""Native source binding must respect the writer's explicit unsorted atom order."""
from hashlib import sha256
from types import SimpleNamespace
import pytest


def test_native_source_binding_keeps_unsorted_nucleotide_atoms():
    pdb=pytest.importorskip('iotbx.pdb')
    from nasolve.refinement_parameter_native import bind_scope,capture_atoms
    names=["O5'",'P',"C5'"]
    source=('CRYST1   20.000   21.000   22.000  90.00  90.00  90.00 P 1           1\n'+
        ''.join(f'ATOM  {i:5d} {name:>4s}  DA A   1    {float(i):8.3f}{2.:8.3f}{3.:8.3f}{1.:6.2f}{200.:6.2f}          {name[0]:>2s}  \n'
                for i,name in enumerate(names,1))+'END\n').encode()
    inp=pdb.input(source_info='unsorted source',lines=source.decode().splitlines())
    hierarchy=inp.construct_hierarchy(sort_atoms=False);xs=inp.xray_structure_simple()
    atoms=capture_atoms(xs);refs=[{k:r[k] for k in ('label','scattering_type','f_prime','f_double_prime')} for r in atoms]
    model=SimpleNamespace(get_hierarchy=lambda:hierarchy,get_xray_structure=lambda:xs)
    result=bind_scope(source,model,expected_scattering=refs,xyz_indices=[0,1,2],adp_groups=[[0,1,2]]).record()
    assert result['source_model_sha256']==sha256(source).hexdigest()
    assert [r['label'] for r in result['initial_atoms']]==[r['label'] for r in atoms]
