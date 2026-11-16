"""Captured chemistry must not depend on resource order when definitions disagree."""
import pytest
from nasolve.metal.chemistry import dictionaries
from nasolve.metal.recipe import RecipeError


def component(order="DOUBLE", charge="0", *, block="DF"):
    return f"""data_{block}
loop_
_chem_comp_atom.comp_id
_chem_comp_atom.atom_id
_chem_comp_atom.type_symbol
_chem_comp_atom.charge
DF C2 C 0
DF S1 S {charge}
loop_
_chem_comp_bond.atom_id_1
_chem_comp_bond.atom_id_2
_chem_comp_bond.type
C2 S1 {order}
""".encode()


@pytest.mark.parametrize("change", ["order", "charge"])
@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_component_metadata_is_never_last_file_wins(change, reverse):
    first = component()
    second = component(order="SINGLE") if change == "order" else component(charge="-1")
    resources = [("source.cif", first), ("other.cif", second)]
    if reverse:
        resources.reverse()
    with pytest.raises(RecipeError, match="Conflicting.*DF"):
        dictionaries(resources)


def test_conflicting_blocks_in_one_file_are_also_rejected():
    with pytest.raises(RecipeError, match="Conflicting.*DF"):
        dictionaries([("bundle.cif", component(block="one") + component("SINGLE", block="two"))])


@pytest.mark.parametrize("alias", ["DOUB", "2"])
def test_equivalent_bond_order_spellings_remain_usable(alias):
    result = dictionaries([("a.cif", component()), ("b.cif", component(alias))])
    assert result["DF"]["graph"]["edges"] == [("C2", "S1")]
    assert result["DF"]["bond_orders"]['["C2","S1"]'] == alias


def test_conflicting_duplicate_edge_order_is_not_collapsed():
    raw = component() + b"S1 C2 SINGLE\n"
    with pytest.raises(RecipeError, match="Conflicting.*bond"):
        dictionaries([("duplicate.cif", raw)])


def test_absent_bond_order_is_not_evidence_of_a_known_order():
    incomplete = component().replace(b"_chem_comp_bond.type\n", b"").replace(b"C2 S1 DOUBLE", b"C2 S1")
    assert dictionaries([("graph.cif", incomplete)])["DF"]["bond_orders"] == {}
    with pytest.raises(RecipeError, match="Conflicting.*DF"):
        dictionaries([("known.cif", component()), ("graph.cif", incomplete)])


@pytest.mark.parametrize("second,conflict", [("SINGLE", True), ("DOUB", False)])
def test_two_order_columns_must_agree_without_precedence(second, conflict):
    raw = component().replace(b"_chem_comp_bond.type\n", b"_chem_comp_bond.type\n_chem_comp_bond.value_order\n")
    raw = raw.replace(b"C2 S1 DOUBLE", ("C2 S1 DOUBLE " + second).encode())
    if conflict:
        with pytest.raises(RecipeError, match="Conflicting.*columns"):
            dictionaries([("columns.cif", raw)])
    else:
        assert dictionaries([("columns.cif", raw)])["DF"]["bond_orders"]


def test_missing_charge_does_not_silently_replace_declared_charge():
    raw = component().replace(b"_chem_comp_atom.charge\n", b"").replace(b"DF C2 C 0", b"DF C2 C").replace(b"DF S1 S 0", b"DF S1 S")
    assert dictionaries([("unknown.cif", raw)])["DF"]["charges"] == {}
    with pytest.raises(RecipeError, match="Conflicting.*DF"):
        dictionaries([("known.cif", component()), ("unknown.cif", raw)])


@pytest.mark.parametrize("first,second", [("0", "0.000"), ("1", "+1"), ("-1", "-1.0")])
def test_equal_numeric_charge_spellings_do_not_create_false_conflicts(first, second):
    result = dictionaries([("a.cif", component(charge=first)), ("b.cif", component(charge=second))])
    assert result["DF"]["charges"]["S1"] == second
