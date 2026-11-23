"""Explicit native-cell binding preserves CRYST1 precision and strict defaults."""
from dataclasses import dataclass
from types import SimpleNamespace
import math
import pytest
from nasolve.topostitch_native_recipe import _native_crystal_binding

@dataclass(frozen=True)
class Group:
    hall: str
    def type(self): return SimpleNamespace(hall_symbol=lambda: self.hall)

class Crystal:
    def __init__(self, cell, hall=" R 3"):
        self.cell=cell; self.group=Group(hall)
    def unit_cell(self): return SimpleNamespace(parameters=lambda: self.cell)
    def space_group(self): return self.group

SOURCE=(105.148,105.148,94.504,90.,90.,120.)
NATIVE=(105.14800262451169,105.14800262451169,94.50399780273438,90.,90.,119.99999999999999)

def test_real_mtz_cell_keeps_all_precision_and_records_source():
    source=Crystal(SOURCE); native=Crystal(NATIVE)
    proof=_native_crystal_binding(source,native)
    assert proof["source_cell_parameters"]==list(SOURCE)
    assert proof["native_cell_parameters"]==list(NATIVE)
    assert proof["space_group_hall_symbol"]==" R 3"
    assert proof["source_precision"]==[3,3,3,2,2,2]
    assert source.cell==SOURCE and native.cell==NATIVE
    assert proof["reflection_authentication"]=="CALLER_OWNED"

@pytest.mark.parametrize("axis,value",[(0,105.1486),(2,94.5034),(5,119.994),(0,106.)])
def test_different_serialized_cell_refuses(axis,value):
    changed=list(NATIVE);changed[axis]=value
    with pytest.raises(ValueError,match="CRYST1"):
        _native_crystal_binding(Crystal(SOURCE),Crystal(changed))

@pytest.mark.parametrize("axis,inside,outside",[(0,105.1484999,105.1485001),(5,120.0049999,120.0050001)])
def test_rounding_edge_is_format_compatibility_not_a_distance_tolerance(axis,inside,outside):
    cell=list(NATIVE);cell[axis]=inside
    assert _native_crystal_binding(Crystal(SOURCE),Crystal(cell))["native_cell_parameters"]==cell
    cell[axis]=outside
    with pytest.raises(ValueError,match="CRYST1"):
        _native_crystal_binding(Crystal(SOURCE),Crystal(cell))

def test_same_cell_different_group_refuses():
    with pytest.raises(ValueError,match="space group"):
        _native_crystal_binding(Crystal(SOURCE),Crystal(NATIVE," P 1"))

@pytest.mark.parametrize("bad",[(),(1,2,3),(*NATIVE[:5],float("nan")),(float("inf"),*NATIVE[1:]),(True,*NATIVE[1:]),(-1.,*NATIVE[1:]),(*NATIVE[:5],180.)])
def test_invalid_cells_refuse(bad):
    with pytest.raises(ValueError):_native_crystal_binding(Crystal(SOURCE),Crystal(bad))

def test_missing_source_crystal_is_not_inferred():
    with pytest.raises(ValueError):_native_crystal_binding(None,Crystal(NATIVE))
