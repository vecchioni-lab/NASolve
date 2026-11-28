"""Production parent-context regressions with synthetic coordinates and graphs."""
from pathlib import Path
import shutil

import pytest

from nasolve.postmr import MutationAction,construct_postmr_model
from tests.helpers import pdb_record

SCAFFOLD={"P":(0.,0.,0.),"OP1":(-.5,1.4,0.),"OP2":(-.5,-.7,1.212),"O5'":(1.6,0.,0.),
 "C5'":(2.9,0.,0.),"C4'":(3.7,1.2,0.),"O4'":(3.,2.,0.),"C1'":(3.4,2.1,1.),
 "C2'":(4.8,2.3,1.),"C3'":(4.2,0.,1.2),"O3'":(5.,0.,0.)}
BASE={'NX':(3.4,3.4,1.3),'C2':(3.4,4.5,1.7),'QZ':(4.8,4.8,2.)}
EDGES=[('P','OP1'),('P','OP2'),('P',"O5'"),('P','OP3'),("O5'","C5'"),("C5'","C4'"),
 ("C4'","O4'"),("O4'","C1'"),("C1'","C2'"),("C2'","C3'"),("C3'","C4'"),("C3'","O3'"),
 ("C1'",'NX'),('NX','C2'),('C2','QZ')]


def fixture(tmp_path):
    def atom(serial,name,code,resid,point):
        element='P' if name=='P' else 'O' if name.startswith('O') else 'N' if name=='NX' else 'C'
        return pdb_record('HETATM',serial,name,code,'Z',resid,element=element,x=point[0],y=point[1],z=point[2])
    outside=[atom(1,"O3'",'DT',8,(-.53,-.76,-1.308)),atom(2,"C3'",'DT',8,(-1.8,-.76,-1.308))]
    tail=[atom(80,'P','DC',10,(6.6,0.,0.)),'CONECT    1    2\n','CONECT    2    1\n','END\n']
    parent=tmp_path/'parent.pdb';raw=tmp_path/'raw.pdb';source=tmp_path/'source.cif'
    parent.write_text('HEADER parent\n'+''.join(outside+[atom(i,n,'DG',9,p) for i,(n,p) in enumerate({**SCAFFOLD,**BASE}.items(),10)]+tail))
    points={**SCAFFOLD,**BASE,'OP3':(-.5,-.9,-1.2)}
    raw.write_text('HEADER parent\n'+''.join(outside+[atom(i,n,'ZZZ',9,(-p[1]+15,p[0]+20,p[2]))for i,(n,p)in enumerate(points.items(),1)]+tail))
    source.write_text('data_ZZZ\n_chem_comp.id ZZZ\n_chem_comp.type "DNA LINKING"\nloop_\n'
        '_chem_comp_atom.comp_id\n_chem_comp_atom.atom_id\n_chem_comp_atom.type_symbol\n'
        +''.join(f'ZZZ "{n}" {"P"if n=="P"else"O"if n.startswith("O")else"N"if n=="NX"else"C"}\n'for n in points)
        +'#\nloop_\n_chem_comp_bond.atom_id_1\n_chem_comp_bond.atom_id_2\n_chem_comp_bond.value_order\n'
        +''.join(f'"{a}" "{b}" SING\n'for a,b in EDGES)+'#\n')
    action=MutationAction('Z:9','DG','ZZZ','coot-parent-overlap',parent_code='DG')
    return raw,parent,source,action


def run_shared(tmp_path,monkeypatch,**kwargs):
    raw,parent,source,action=fixture(tmp_path)
    def coot(model,output,actions,executable,directory,environment,dictionaries,parents,**unused):
        shutil.copyfile(raw,output);shutil.copyfile(parent,parents['Z:9'])
        log=directory/'coot.log';log.write_text('controlled native Coot output')
        return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    result=construct_postmr_model(parent,(action,),{'ZZZ':source},tmp_path/'constructed.pdb',coot_executable=tmp_path/'coot',**kwargs)
    return result,(raw,parent,source,action)


def test_ordinary_construction_uses_verified_internal_context_to_reach_graph_transport(tmp_path,monkeypatch):
    result,(raw,parent,source,action)=run_shared(tmp_path,monkeypatch)
    assert result['coordinate_restoration']['Z:9']['status']=='GRAPH_FRAGMENT_RESTORED'
    assert result['context_receipt']['status']=='CONTEXT_PREPARED'
    assert result['raw_model'].read_bytes()==raw.read_bytes()
    assert result['restoration_input']!=result['raw_model']
    assert result['context_receipt']['removed_atoms'][0]['atom']=='OP3'
    assert result['context_receipt']['serial_repairs']
    assert result['context_receipt']['final_sanitizer_recheck']['checked'][0]['incoming_site']=='Z:8'


def prepare(tmp_path,*,problem=None,allow=(),passthrough=()):
    from nasolve.postmr_context import prepare_construction_context
    raw,parent,source,action=fixture(tmp_path)
    if problem=='different_conect':raw.write_text(raw.read_text().replace('CONECT    1    2','CONECT    1    3'))
    if problem=='selected_endpoint':
        for p in (raw,parent):p.write_text(p.read_text().replace('CONECT    1    2','CONECT   10   11'))
    if problem=='duplicate_reference_serial':parent.write_text(parent.read_text().replace('HETATM   10','HETATM    1'))
    if problem=='unselected_coordinate':raw.write_text(raw.read_text().replace('  -0.530  -0.760  -1.308','  -0.630  -0.760  -1.308'))
    if problem=='missing_incoming':
        for p in (raw,parent):p.write_text(''.join(l for l in p.read_text().splitlines(keepends=True) if not(l.startswith('HETATM')and l[22:26].strip()=='8')))
    if problem=='bridge':source.write_text(source.read_text().rstrip('#\n')+'\nQZ "C2\'" SING\n#\n')
    if problem in {'alternate_op3','wrong_op3_element'}:
        lines=[]
        for l in raw.read_text().splitlines(keepends=True):
            if l.startswith('HETATM')and l[12:16].strip()=='OP3':
                l=l[:16]+'A'+l[17:] if problem=='alternate_op3' else l[:76]+' C'+l[78:]
            lines.append(l)
        raw.write_text(''.join(lines))
    if problem=='unique_serials':
        raw.write_text(''.join(l[:6]+f'{int(l[6:11])+100:5d}'+l[11:] if l.startswith('HETATM')and l[22:26].strip()=='9' else l for l in raw.read_text().splitlines(keepends=True)))
    result=prepare_construction_context(raw,parent,(action,),{'ZZZ':source},{'Z:9':parent},tmp_path/'context.pdb',allow_op3_sites=allow,passthrough_sites=passthrough)
    return result,(raw,parent,source,action)


def atom_rows(path):
    return {(l[21],l[22:27].strip(),l[16],l[12:16].strip()):l for l in path.read_text().splitlines(keepends=True)if l.startswith(('ATOM  ','HETATM'))}


def test_context_transfers_only_verified_deletion_and_selected_serials(tmp_path):
    result,(raw,parent,source,action)=prepare(tmp_path)
    before,after,shadow=map(atom_rows,(raw,result['model'],result['shadow']))
    removed=set(before)-set(after)
    assert removed=={('Z','9',' ','OP3')}
    assert result['receipt']['status']=='CONTEXT_PREPARED'
    assert result['receipt']['serial_authority']['status']=='ORIGINAL_CONECT_AUTHORITY_PASS'
    for key,line in after.items():
        assert line[11:]==before[key][11:], 'XYZ and all nonserial metadata must remain original raw'
        if key[1]!='9':assert line==before[key]
    assert len({l[6:11]for l in after.values()})==len(after)
    assert shadow[('Z','9',' ','OP3')][30:54]==before[('Z','9',' ','OP3')][30:54]
    assert shadow[('Z','9',' ','NX')][30:54]==before[('Z','9',' ','NX')][30:54]
    assert shadow[('Z','9',' ','P')][30:54]==atom_rows(parent)[('Z','9',' ','P')][30:54]
    assert [l for l in result['model'].read_text().splitlines()if l.startswith('CONECT')]==[l for l in raw.read_text().splitlines()if l.startswith('CONECT')]
    row=result['receipt']['removed_atoms'][0]
    assert row['old_serial']!=row['new_serial'] and row['serial']==row['new_serial']
    assert shadow[('Z','9',' ','OP3')][6:11].strip()==str(row['new_serial'])


@pytest.mark.parametrize('problem',['different_conect','selected_endpoint','duplicate_reference_serial','unselected_coordinate','missing_incoming','alternate_op3','wrong_op3_element'])
def test_unproved_authority_or_phosphate_context_retains_exact_raw_model(tmp_path,problem):
    result,(raw,*_)=prepare(tmp_path,problem=problem)
    assert result['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes()==raw.read_bytes()
    assert result['receipt']['serial_repairs']==[] and result['receipt']['removed_atoms']==[]
    assert result['receipt']['reason'] and result['receipt']['requires_cif_review'] is False


def test_unsupported_source_graph_has_no_context_edit(tmp_path):
    result,(raw,*_)=prepare(tmp_path,problem='bridge')
    assert result['receipt']['status']=='NO_CONTEXT_CHANGE'
    assert result['model'].read_bytes()==raw.read_bytes()
    assert result['receipt']['skipped_sites'] and not result['receipt']['removed_atoms']


def test_unique_raw_serials_do_not_require_repair(tmp_path):
    result,_=prepare(tmp_path,problem='unique_serials')
    assert result['receipt']['status']=='CONTEXT_PREPARED'
    assert result['receipt']['serial_repairs']==[]
    assert result['receipt']['serial_authority']['status']=='NOT_REQUIRED'


def test_frozen_terminal_phosphate_intent_is_never_overridden(tmp_path):
    result,(raw,*_)=prepare(tmp_path,allow=('Z:9',))
    assert result['receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['model'].read_bytes()==raw.read_bytes()
    assert 'conflicts with an internal' in result['receipt']['reason']


def test_frozen_passthrough_excludes_context_and_parent_restoration(tmp_path,monkeypatch):
    result,(raw,*_)=run_shared(tmp_path,monkeypatch,passthrough_sites=('Z:9',))
    assert result['context_receipt']['status']=='NO_CONTEXT_CHANGE'
    assert result['model'].read_bytes()==raw.read_bytes()
    assert result['coordinate_restoration']['Z:9']['status']=='RAW_SITE_RETAINED'
    assert not result['context_receipt']['removed_atoms']


def test_final_phosphate_recheck_rolls_back_the_entire_construction_transaction(tmp_path,monkeypatch):
    from nasolve.phosphate import PhosphateError
    def fail(*args,**kwargs):raise PhosphateError('Synthetic final-gate regression')
    monkeypatch.setattr('nasolve.postmr.sanitize_phosphates',fail)
    result,(raw,*_)=run_shared(tmp_path,monkeypatch)
    assert result['model'].read_bytes()==raw.read_bytes()
    assert result['restoration_input']==result['raw_model']
    assert result['context_receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['context_receipt']['removed_atoms']==[] and result['context_receipt']['serial_repairs']==[]
    assert result['context_receipt']['attempted_removed_atoms']
    assert result['context_receipt']['attempted_serial_repairs']
    assert result['context_rechecked_model'] is None
    assert result['coordinate_restoration']['Z:9']['status']=='RAW_SITE_RETAINED'


def test_context_refuses_existing_outputs_and_preserves_all_inputs(tmp_path):
    from nasolve.postmr_context import prepare_construction_context
    raw,parent,source,action=fixture(tmp_path);snapshots={p:p.read_bytes()for p in(raw,parent,source)}
    out=tmp_path/'context.pdb';out.write_text('KEEP')
    with pytest.raises(FileExistsError):prepare_construction_context(raw,parent,(action,),{'ZZZ':source},{'Z:9':parent},out)
    assert out.read_text()=='KEEP' and all(p.read_bytes()==v for p,v in snapshots.items())


def test_failed_context_preserves_existing_curated_and_canonical_restoration(tmp_path,monkeypatch):
    from nasolve.phosphate import PhosphateError
    raw,parent,source,graph_action=fixture(tmp_path)
    # Unique raw serials isolate the final-gate rollback from the independent
    # inherited-CONECT serial authority rule.
    raw.write_text(''.join(l[:6]+f'{int(l[6:11])+1000:5d}'+l[11:] if l.startswith('HETATM')and l[22:26].strip()=='9' else l for l in raw.read_text().splitlines(keepends=True)))
    def atom(serial,name,code,chain,resid,point,element):
        return pdb_record('HETATM',serial,name,code,chain,resid,element=element,x=point[0],y=point[1],z=point[2])
    clean=[];changed=[]
    for i,(name,p)in enumerate(SCAFFOLD.items(),200):
        element='P'if name=='P'else'O'if name.startswith('O')else'C'
        clean.append(atom(i,name,'DT','R',4,(p[0]+200,p[1],p[2]),element))
        changed.append(atom(i,name,'DF','R',4,(p[0]+205,p[1],p[2]),element))
    clean += [atom(220,'C2','DT','R',4,(210,0,0),'C'),atom(221,'O2','DT','R',4,(211,0,0),'O')]
    changed += [atom(220,'C2','DF','R',4,(250,0,0),'C'),atom(221,'S1','DF','R',4,(250,2,0),'S')]
    clean += [atom(300,'P','DA','Q',1,(100,0,0),'P'),atom(301,"C1'",'DA','Q',1,(103,0,0),'C'),atom(302,'N9','DA','Q',1,(104,0,0),'N')]
    changed += [atom(300,'P','DG','Q',1,(110,0,0),'P'),atom(301,"C1'",'DG','Q',1,(113,0,0),'C'),atom(302,'N9','DG','Q',1,(114,0,0),'N')]
    parent.write_text(parent.read_text().replace('END\n','')+''.join(clean)+'END\n')
    raw.write_text(raw.read_text().replace('END\n','')+''.join(changed)+'END\n')
    curated=tmp_path/'DF.cif';curated.write_text('data_DF\n')
    actions=(graph_action,MutationAction('R:4','DT','DF','coot-parent-overlap',parent_code='DT'),MutationAction('Q:1','DA','DG','coot-mutate-base'))
    def coot(model,output,actions,executable,directory,environment,dictionaries,parents,**unused):
        shutil.copyfile(raw,output)
        for path in parents.values():shutil.copyfile(parent,path)
        log=directory/'coot.log';log.write_text('controlled mixed Coot')
        return directory/'mutate.py',log
    monkeypatch.setattr('nasolve.postmr._run_coot',coot)
    def fail(*args,**kwargs):raise PhosphateError('Synthetic final context mismatch')
    monkeypatch.setattr('nasolve.postmr.sanitize_phosphates',fail)
    result=construct_postmr_model(parent,actions,{'ZZZ':source,'DF':curated},tmp_path/'constructed.pdb',coot_executable=tmp_path/'coot')
    rows=atom_rows(result['model']);raw_rows=atom_rows(raw)
    def x(chain,resid,atom):return float(rows[(chain,resid,' ',atom)][30:38])
    assert result['context_receipt']['status']=='RAW_CONTEXT_RETAINED'
    assert result['context_receipt']['attempted_removed_atoms'], 'The final check, not preflight, triggered rollback'
    assert rows[('Z','9',' ','P')]==raw_rows[('Z','9',' ','P')]
    assert x('R','4','P')==200 and x('R','4','S1')==212
    assert x('Q','1','P')==100 and x('Q','1','N9')==114
    assert result['coordinate_restoration']['R:4']['status']=='CURATED_DECLARED_PLACEMENT'
    assert result['coordinate_restoration']['Q:1']['source']=='pre-Coot input model'
    assert result['restoration_input']==result['raw_model']
    assert result['geometry_model'].name.endswith('_context_rollback_geometry.pdb')
