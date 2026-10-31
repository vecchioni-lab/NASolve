"""Synthetic graph/geometry regressions; no installed native tools."""
from copy import deepcopy
import pytest

from tests.test_cif_captured_geometry import native as scalar_native

SCAFFOLD = ["P", "OP1", "OP2", "O5'", "C5'", "C4'", "O4'", "C1'", "C2'", "C3'", "O3'"]
EDGES = [("P", "OP1"), ("P", "OP2"), ("P", "O5'"), ("O5'", "C5'"),
         ("C5'", "C4'"), ("C4'", "O4'"), ("O4'", "C1'"), ("C1'", "C2'"),
         ("C2'", "C3'"), ("C3'", "C4'"), ("C3'", "O3'")]


def fixture(tmp_path, anchor='NX', element='N'):
    names = SCAFFOLD + [anchor, 'C2', 'QZ']
    points = [(5.7,1.1,.3),(6.4,2.4,.5),(6.4,0.,.7),(4.5,.9,.2),(3.4,.5,.3),
              (2.1,.9,.5),(1.4,0.,0.),(0.,0.,0.),(0.,1.5,0.),(1.4,2.,.3),
              (1.5,3.4,.2),(.2,.3,1.4),(-.8,.3,2.3),(-.5,1.4,2.7)]
    elements = [('P' if a=='P' else 'O' if a.startswith('O') else 'C') for a in names]
    elements[-3] = element
    target = [(round(-y+10,3),round(x+20,3),round(z+30,3)) for x,y,z in points]
    baseline = list(target)
    baseline[-2] = (16.,24.,39.)  # Wrong same-name parent copy, deliberately distorted.
    def write(path, xyz, code='ZZZ'):
        lines = [f'HETATM{i:5d} {a:>4} {code:>3} Z{9:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  0.75 17.00          {el:>2}\n'
                 for i,(a,(x,y,z),el) in enumerate(zip(names,xyz,elements),1)]
        path.write_text(''.join(lines)+'END\n');return path
    raw=write(tmp_path/'raw.pdb',points);model=write(tmp_path/'baseline.pdb',baseline)
    parent=write(tmp_path/'parent.pdb',baseline,code='DC')
    n=scalar_native();n['atoms']=[]
    for i,(a,xyz,el) in enumerate(zip(names,baseline,elements)):
        n['atoms'].append({'i_seq':i,'atom_id':a,'label':f'ZZZ Z9 {a}', 'element':el,
            'xyz':list(xyz),'occupancy':.75,'atom_name_field':f'{a:>4}',
            'identity':{'chain_id':'Z','resseq':'9','icode':'','altloc':'','model_id':'','resname':'ZZZ'}})
    n['atom_count']=len(names);n['geometry']['sites_cart_exact']=[list(p) for p in baseline]
    for kind in n['geometry']['proxy_details']:n['geometry']['proxy_details'][kind]=[];n['geometry']['proxy_counts'][kind]=0
    definition={'atoms':[{'atom_id':a,'type_symbol':el} for a,el in zip(names,elements)],
                'bonds':[{'atom_id_1':a,'atom_id_2':b,'type':'single'} for a,b in EDGES+[("C1'",anchor),(anchor,'C2'),('C2','QZ')]]}
    n['monomer_mappings']={'rows':[{'site':'Z:9','resname':'ZZZ','metadata':{'effective_definition':definition}}]}
    return raw,model,parent,n,{a:p for a,p in zip(names,target)}


@pytest.mark.parametrize(('anchor','element'), [('NX','N'),('CX','C'),('MIS','C')])
def test_attached_fragment_moves_rigidly_without_same_name_parent_base_copies(tmp_path,anchor,element):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration
    raw,model,parent,n,expected=fixture(tmp_path,anchor,element)
    before={p:p.read_bytes() for p in (raw,model,parent)}
    out=tmp_path/'candidate.pdb'
    r=prepare_fragment_restoration(raw,model,out,n,{'Z:9':parent})
    rows={l[12:16].strip():l for l in out.read_text().splitlines() if l.startswith('HETATM')}
    for a in (anchor,'C2','QZ'):
        actual=[float(rows[a][i:i+8]) for i in (30,38,46)]
        assert actual==list(expected[a])
    old={l[12:16].strip():l for l in model.read_text().splitlines() if l.startswith('HETATM')}
    for a in SCAFFOLD:assert rows[a]==old[a]
    for a in rows:assert rows[a][:30]+rows[a][54:]==old[a][:30]+old[a][54:]
    assert all(p.read_bytes()==data for p,data in before.items())
    assert r['status']=='REVIEW' and r['automatic_adoption'] is False
    assert r['sites'][0]['attachment_atom']==anchor
    assert r['sites'][0]['max_fragment_distance_change']<=.002
    assert r['sites'][0]['rotation_determinant']==pytest.approx(1.)
    assert r['changed_atom_count']==1 and r['transported_atom_count']==3 and r['scaffold_preserved']


@pytest.mark.parametrize('defect',['multi_attachment','disconnected','sugar_bond','element','duplicate','parent_mismatch','frame','altloc'])
def test_unsupported_graph_or_correspondence_is_refused_before_output(tmp_path,defect):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path)
    d=n['monomer_mappings']['rows'][0]['metadata']['effective_definition']
    if defect=='multi_attachment':d['bonds'].append({'atom_id_1':'QZ','atom_id_2':"C2'",'type':'single'})
    if defect=='disconnected':d['bonds'].pop()
    if defect=='sugar_bond':d['bonds'].pop(0)
    if defect=='element':d['atoms'][-1]['type_symbol']='N'
    if defect=='duplicate':raw.write_text(raw.read_text()+raw.read_text().splitlines(keepends=True)[0])
    if defect=='parent_mismatch':parent.write_text(parent.read_text().replace('  10.000  20.000  30.000','  19.000  20.000  30.000'))
    if defect=='frame':raw.write_text(raw.read_text().replace('   0.000   1.500   0.000','   2.000   0.000   0.000'))
    if defect=='altloc':
        lines=raw.read_text().splitlines(keepends=True);lines[0]=lines[0][:16]+'A'+lines[0][17:];raw.write_text(''.join(lines))
    output=tmp_path/'candidate.pdb'
    with pytest.raises(ValueError):prepare_fragment_restoration(raw,model,output,n,{'Z:9':parent})
    assert not output.exists()


def test_existing_output_is_never_replaced(tmp_path):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path);output=tmp_path/'candidate.pdb';output.write_text('PRESERVE')
    with pytest.raises(FileExistsError):prepare_fragment_restoration(raw,model,output,n,{'Z:9':parent})
    assert output.read_text()=='PRESERVE'


def test_shared_component_unselected_site_and_all_its_records_stay_unchanged(tmp_path):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path)
    original=model.read_text()
    extra=''.join(line[:22]+f'{10:4d}'+line[26:] for line in original.splitlines(keepends=True) if line.startswith('HETATM'))
    model.write_text(original+extra)
    copies=deepcopy(n['atoms'])
    for a in copies:
        a['i_seq']+=len(n['atoms']);a['identity']['resseq']='10';a['label']=a['label'].replace('Z9','Z10')
    n['atoms']+=copies;n['atom_count']=len(n['atoms'])
    n['geometry']['sites_cart_exact'] += deepcopy(n['geometry']['sites_cart_exact'])
    other=deepcopy(n['monomer_mappings']['rows'][0]);other['site']='Z:10';n['monomer_mappings']['rows'].append(other)
    output=tmp_path/'candidate.pdb';prepare_fragment_restoration(raw,model,output,n,{'Z:9':parent})
    assert output.read_text().endswith(extra)


def test_rigid_reorientation_of_the_entire_raw_component_gives_the_same_candidate(tmp_path):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path);first=tmp_path/'first.pdb'
    prepare_fragment_restoration(raw,model,first,n,{'Z:9':parent})
    lines=[]
    for line in raw.read_text().splitlines(keepends=True):
        if line.startswith('HETATM'):
            x,y,z=[float(line[i:i+8]) for i in (30,38,46)]
            line=line[:30]+''.join(f'{v:8.3f}' for v in (z+7,-x+11,-y+13))+line[54:]
        lines.append(line)
    raw.write_text(''.join(lines));second=tmp_path/'second.pdb'
    prepare_fragment_restoration(raw,model,second,n,{'Z:9':parent})
    assert first.read_bytes()==second.read_bytes()


def test_aromatic_sugar_is_explicitly_unsupported_and_not_reinterpreted(tmp_path):
    from nasolve.cif_fragment_restoration import assess_fragment_contexts, prepare_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path)
    definition=n['monomer_mappings']['rows'][0]['metadata']['effective_definition']
    definition['bonds'][7]['type']='aromatic'
    r=assess_fragment_contexts(n,model,{'Z:9':parent})
    assert r['supported_sites']==[] and r['unsupported_sites'][0]['site']=='Z:9'
    assert r['unsupported_sites'][0]['reason']=='Unsupported DNA scaffold bond type'
    with pytest.raises(ValueError,match='scaffold bond type'):
        prepare_fragment_restoration(raw,model,tmp_path/'candidate.pdb',n,{'Z:9':parent})


def test_native_checks_detect_target_and_coordinate_tampering_and_keep_review(tmp_path):
    from nasolve.cif_fragment_restoration import prepare_fragment_restoration, qualify_fragment_restoration
    raw,model,parent,n,_=fixture(tmp_path);output=tmp_path/'candidate.pdb'
    preparation=prepare_fragment_restoration(raw,model,output,n,{'Z:9':parent})
    after=deepcopy(n)
    points=[[float(l[i:i+8]) for i in (30,38,46)] for l in output.read_text().splitlines() if l.startswith('HETATM')]
    after['geometry']['sites_cart_exact']=points
    for a,point in zip(after['atoms'],points):a['xyz']=point
    q=qualify_fragment_restoration(n,after,output,preparation)
    assert all(c['status']=='PASS' for c in q['checks']) and q['status']=='REVIEW'
    after['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['type']='double'
    q=qualify_fragment_restoration(n,after,output,preparation)
    assert any(c['status']=='REVIEW' for c in q['checks'])
    after=deepcopy(n);after['geometry']['sites_cart_exact'][0][0]+=1;after['atoms'][0]['xyz'][0]+=1
    q=qualify_fragment_restoration(n,after,output,preparation)
    assert any(c['check']=='exact-candidate-coordinates' and c['status']=='REVIEW' for c in q['checks'])
