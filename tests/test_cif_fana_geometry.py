"""Source sugar hands remain separate from optimizer convergence or energy."""
from copy import deepcopy
import pytest
from tests.test_cif_fana_junction import fixture


def source_case(tmp_path):
    from nasolve.cif_fana_junction import _bind
    paths,n=fixture(tmp_path);placement,values,_=_bind(paths[0],paths[1],n)
    selected=[a['i_seq'] for a in n['atoms'] if a['identity']['resseq']=='2'];points=deepcopy(n['geometry']['sites_cart_exact'])
    return values,n,placement['context']['site'],selected,points


def test_all_four_source_hands_are_required_in_full_and_serialized_models(tmp_path):
    from nasolve.cif_fana_geometry import review_fana_coordinates
    values,n,site,selected,points=source_case(tmp_path)
    q=review_fana_coordinates(values,n,site,selected,points,points)
    assert q['four_sugar_hands_preserved'] and len(q['sugar_hands'])==4 and q['fixed_coordinates_preserved']
    reflected=deepcopy(points)
    for i in selected:reflected[i][0]=-reflected[i][0]
    assert not review_fana_coordinates(values,n,site,selected,reflected,points)['four_sugar_hands_preserved']
    assert not review_fana_coordinates(values,n,site,selected,points,reflected)['four_sugar_hands_preserved']


@pytest.mark.parametrize('defect',['partial','reordered','flank','missing_centre','degenerate'])
def test_coordinate_review_cannot_lose_a_source_centre_or_move_flanks(tmp_path,defect):
    from nasolve.cif_fana_geometry import review_fana_coordinates
    values,n,site,selected,points=source_case(tmp_path)
    if defect=='partial':selected=selected[:-1]
    if defect=='reordered':selected=selected[::-1]
    if defect=='flank':points[0][0]+=1
    if defect=='missing_centre':
        i=next(i for i in selected if n['atoms'][i]['atom_id']=="C2'");n['atoms'][i]['atom_id']='absent'
    if defect=='degenerate':
        i=next(i for i in selected if n['atoms'][i]['atom_id']=="C2'");j=next(i for i in selected if n['atoms'][i]['atom_id']=="C3'");points[i]=points[j][:]
    if defect in ('missing_centre','degenerate'):
        assert not review_fana_coordinates(values,n,site,selected,points,points)['four_sugar_hands_preserved']
    else:
        with pytest.raises(ValueError):review_fana_coordinates(values,n,site,selected,points,points)


def test_native_coordinate_roundoff_is_separate_from_exact_full_precision_flanks(tmp_path):
    from nasolve.cif_fana_geometry import review_fana_coordinates
    values,n,site,selected,points=source_case(tmp_path);rounded=deepcopy(points)
    rounded[0][0]+=1e-14
    assert review_fana_coordinates(values,n,site,selected,points,rounded)['native_fixed_coordinate_roundoff_max_angstrom']<1e-9
    rounded[0][0]+=1e-8
    with pytest.raises(ValueError):review_fana_coordinates(values,n,site,selected,points,rounded)
