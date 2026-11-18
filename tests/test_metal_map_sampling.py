"""One bounded sampler; phase/data eligibility remains with its callers."""
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest
from nasolve.metal import map_diagnostics as maps, anomalous_maps


class Cell:
    """Nonorthogonal a=(10,0,0), b=(5,8,0), c=(0,0,12)."""
    def fractionalize(self, xyz):
        x,y,z=xyz
        return ((x-5*y/8)/10,y/8,z/12)


class PeriodicGrid:
    def __init__(self): self.calls=0
    def eight_point_interpolation(self, xyz):
        self.calls+=1
        x,y,z=xyz
        return math.sin(2*math.pi*x)+2*math.cos(2*math.pi*y)+.5*math.sin(2*math.pi*z)


def test_nonorthogonal_periodicity_and_distinct_own_common_positions():
    grid=PeriodicGrid();cell=Cell();own=[9.8,-.2,11.9];before=list(own)
    r=maps.sample_grid(grid,cell,own,radius_A=1.5,spacing_A=.5)
    assert own==before and r['samples']==123 and grid.calls==124
    assert r['center_sigma']==pytest.approx(PeriodicGrid().eight_point_interpolation(cell.fractionalize(own)))
    # Translate by a-b+2c, including negative fractional coordinates.
    shifted=[own[0]+5,own[1]-8,own[2]+24]
    other=maps.sample_grid(grid,cell,shifted,radius_A=1.5,spacing_A=.5)
    assert other==pytest.approx(r,abs=2e-14)
    common=maps.sample_grid(grid,cell,[0,0,0],radius_A=1.5,spacing_A=.5)
    assert common['center_sigma']==2 and common['center_sigma']!=pytest.approx(r['center_sigma'])


def test_affine_grid_symmetric_sphere_has_known_mean_and_extrema():
    class Identity:
        def fractionalize(self,xyz): return xyz
    class Affine:
        def eight_point_interpolation(self,xyz): return 3+2*xyz[0]
    r=maps.sample_grid(Affine(),Identity(),[4,2,-1],radius_A=1.5,spacing_A=.5)
    assert r==dict(center_sigma=11.,sphere_min_sigma=8.,sphere_max_sigma=14.,sphere_mean_sigma=11.,samples=123)
    tiny=maps.sample_grid(Affine(),Identity(),[4,2,-1],radius_A=.25,spacing_A=1.)
    assert tiny==dict(center_sigma=11.,sphere_min_sigma=11.,sphere_max_sigma=11.,sphere_mean_sigma=11.,samples=1)


def test_legacy_offsets_and_capture_policy_fingerprints_are_unchanged():
    assert maps._digest(maps._offsets())=='d6976ac638fe36db7047c4f94dd9d0e25ee9fefade6f22059ecd71c3eb9a09f9'
    assert maps.sphere_offsets(1.5,.5)==maps._offsets()
    assert maps._digest(maps.request())=='18a11b7763305680ddbcecd13f46b132c3766468a01df9fe9371158d3337547c'
    assert maps._digest(anomalous_maps.request())=='4ac565055bcf54dd33319eb6d54c72bdb1adab66893ad7052a27c93189ba5fdb'
    assert len(maps.sphere_offsets(1.,1.))==7


@pytest.mark.parametrize('radius,spacing',[(0,.5),(-1,.5),(1.5,0),(1.5,-1),
    (True,.5),(1.5,False),(float('nan'),.5),(1.5,float('inf')),
    (1e100,1e-300),(1.,.00001)])
def test_invalid_or_excessive_sampling_fails_before_grid_work(radius,spacing):
    grid=PeriodicGrid()
    with pytest.raises(ValueError):maps.sample_grid(grid,Cell(),[0,0,0],radius_A=radius,spacing_A=spacing)
    assert grid.calls==0


@pytest.mark.parametrize('xyz',[[],[1,2],[1,2,3,4],[True,0,0],[float('nan'),0,0],[0,float('inf'),0],None,'123'])
def test_invalid_coordinates_fail_before_sampling(xyz):
    grid=PeriodicGrid()
    with pytest.raises(ValueError):maps.sample_grid(grid,Cell(),xyz,radius_A=1.5,spacing_A=.5)
    assert grid.calls==0


@pytest.mark.parametrize('at',[1,124])
def test_nonfinite_neighborhood_or_center_is_refused(at):
    class Broken(PeriodicGrid):
        def eight_point_interpolation(self,xyz):
            value=super().eight_point_interpolation(xyz)
            return float('nan') if self.calls==at else value
    with pytest.raises(ValueError):maps.sample_grid(Broken(),Cell(),[0,0,0],radius_A=1.5,spacing_A=.5)


def test_native_bare_module_import_without_nasolve_package():
    folder=Path(maps.__file__).parent
    code="""import sys,json
sys.path.insert(0,sys.argv[1])
import map_diagnostics as m
import anomalous_maps as a
assert not any(n=='nasolve' or n.startswith('nasolve.')for n in sys.modules)
assert a.common is m
class Cell:
 def fractionalize(self,x):return x
class Grid:
 def eight_point_interpolation(self,x):return 2.5
print(json.dumps(m.sample_grid(Grid(),Cell(),[0,0,0],radius_A=1.5,spacing_A=.5)))
"""
    done=subprocess.run([sys.executable,'-I','-B','-c',code,str(folder)],capture_output=True,text=True,timeout=10)
    assert done.returncode==0,done.stderr
    assert json.loads(done.stdout)==dict(center_sigma=2.5,sphere_min_sigma=2.5,sphere_max_sigma=2.5,sphere_mean_sigma=2.5,samples=123)
