"""Synthetic printed-log cases, not committed crystallographic observations."""
import hashlib
import json
from unittest.mock import patch
import pytest
from nasolve.refinement_final_scaling import parse_final_scaling, describe_b_frame, read_final_scaling

FINAL = "==================================== Final ===================================="
ROWS = [
 "start: r(all,work,free)=0.3010 0.3000 0.3500 n_refl.: 1000",
 "re-set all scales: r(all,work,free)=0.3300 0.3300 0.3400 n_refl.: 1000",
 "overall B=80.00 to atoms: r(all,work,free)=0.3900 0.4000 0.3100 n_refl.: 1000",
 "bulk-solvent and scaling: r(all,work,free)=0.2810 0.2800 0.3000 n_refl.: 1000",
]
def log(rows=None):return "Earlier cycles\n"+ROWS[2]+"\n"+FINAL+"\n\n"+"\n".join(ROWS if rows is None else rows)+"\nOther final summaries\n"

def test_final_rows_are_distinct_from_earlier_cycles_and_keep_exact_evidence():
 text=log();r=parse_final_scaling(text)
 assert r['status']=='OBSERVED' and r['b_transfer_A2']==80
 assert [x['stage'] for x in r['stages']]==['before_scaling','scales_reset','b_transferred','solvent_scaled']
 assert r['stages'][0]['r_work']==.3 and r['stages'][-1]['r_work']==.28
 assert r['stages'][2]['printed_line']==ROWS[2]
 assert text.splitlines()[r['stages'][2]['line_number']-1]==ROWS[2]
 assert r['source']['sha256']==hashlib.sha256(text.encode()).hexdigest()
 assert r['native_execution_performed'] is False and r['scientific_acceptance']=='NOT_ASSESSED'

@pytest.mark.parametrize('shift',[0,-3.83,80.0])
def test_explicit_zero_negative_and_positive_transfer(shift):
 rows=ROWS.copy();rows[2]=rows[2].replace('80.00',str(shift));r=parse_final_scaling(log(rows));assert r['status']=='OBSERVED' and r['b_transfer_A2']==shift

@pytest.mark.parametrize('rows',[ROWS[:i]+ROWS[i+1:] for i in range(4)])
def test_missing_stage_never_supplies_a_transfer_or_assumes_zero(rows):
 r=parse_final_scaling(log(rows));assert r['status']=='INCOMPLETE_FINAL_SCALING' and r['b_transfer_A2'] is None
 frame=describe_b_frame(log(rows),{'Hg':120.});assert frame['offset_adjusted_A2'] is None and frame['frame_status']=='UNAVAILABLE'

@pytest.mark.parametrize('rows',[ROWS+ROWS,ROWS[::-1],ROWS[:2]+[ROWS[1]]+ROWS[2:]])
def test_duplicate_or_reordered_sequences_are_not_silently_selected(rows):
 r=parse_final_scaling(log(rows));assert r['status']!='OBSERVED' and r['b_transfer_A2'] is None

@pytest.mark.parametrize('text',["\n".join(ROWS),"no final record",log()+"\n"+FINAL+"\n"+"\n".join(ROWS)])
def test_missing_or_repeated_final_boundary_is_unavailable(text):
 r=parse_final_scaling(text);assert r['status'] in {'NO_FINAL_SECTION','AMBIGUOUS_FINAL_SECTION'} and r['b_transfer_A2'] is None

@pytest.mark.parametrize('bad',['nan','inf','-inf','1e9999','1e-9999','unknown','true'])
def test_malformed_or_nonrepresentable_values_refuse_evidence(bad):
 rows=ROWS.copy();rows[2]=rows[2].replace('80.00',bad);r=parse_final_scaling(log(rows));assert r['status']=='UNSUPPORTED_FINAL_SCALING' and r['b_transfer_A2'] is None

@pytest.mark.parametrize('field,bad',[('0.3010','-0.1'),('1000','0'),('1000','3.5')])
def test_invalid_R_or_reflection_count(field,bad):
 rows=ROWS.copy();rows[0]=rows[0].replace(field,bad);assert parse_final_scaling(log(rows))['status']=='UNSUPPORTED_FINAL_SCALING'

def test_changed_reflection_count_is_not_a_matched_final_stage():
 rows=ROWS.copy();rows[-1]=rows[-1].replace('1000','999');r=parse_final_scaling(log(rows));assert r['status']=='INCONSISTENT_REFLECTION_COUNT' and r['b_transfer_A2'] is None

def test_B_frame_names_written_offset_and_invariant_contrasts_without_mutation():
 values={'base_a':100.,'base_b':140.,'Hg':125.};before=values.copy()
 r=describe_b_frame(log(),values,reference_labels=['base_a','base_b'])
 assert values==before and r['written_A2']==values
 assert r['offset_adjusted_A2']=={'base_a':20.,'base_b':60.,'Hg':45.}
 assert r['relative_to_equal_reference_mean_A2']['Hg']==5.
 assert r['reference_labels']==['base_a','base_b']
 assert r['frame_status']=='APPROXIMATE_FINAL_OFFSET_ONLY' and r['model_binding']=='CALLER_VALUES_NOT_VERIFIED'
 assert 'not an exact pre-scaling state' in ' '.join(r['limitations'])

@pytest.mark.parametrize('values,refs',[({'Hg':True},[]),({'Hg':float('nan')},[]),({'Hg':float('inf')},[]),({},[]),({'Hg':1},['missing']),({'Hg':1},['Hg','Hg']),({'Hg':1},'Hg'),({'':1},[])])
def test_B_summary_refuses_ambiguous_values_and_reference_membership(values,refs):
 with pytest.raises(ValueError):describe_b_frame(log(),values,reference_labels=refs)

def test_no_reference_labels_means_no_inferred_environment():
 r=describe_b_frame(log(),{'A':110,'B':120});assert r['relative_to_equal_reference_mean_A2'] is None

def test_explicit_file_read_is_bounded_pinned_and_relocatable(tmp_path):
 p=tmp_path/'arbitrary_name.txt';p.write_text(log());r=read_final_scaling(p);assert r['status']=='OBSERVED'
 assert read_final_scaling(p,expected_sha256=r['source']['sha256'])==r
 moved=tmp_path/'relocated';moved.mkdir();new=moved/'another_name.log';p.rename(new)
 assert not p.exists() and read_final_scaling(new)==r
 with pytest.raises(ValueError):read_final_scaling(new,expected_sha256='0'*64)
 with pytest.raises(ValueError):read_final_scaling(new,max_bytes=10)
 with pytest.raises(ValueError):parse_final_scaling(log(),max_bytes=10)

def test_cli_does_not_open_a_run_find_phenix_launch_or_write(tmp_path,capsys):
 from nasolve.cli import main
 p=tmp_path/'stage.log';p.write_text(log());before=p.read_bytes()
 with patch('subprocess.Popen',side_effect=AssertionError('No native job')),patch('nasolve.metal.cli.load_run_context',side_effect=AssertionError('No run')),patch('nasolve.metal.cli.discover_phenix',side_effect=AssertionError('No Phenix')):
  assert main(['metal','inspect-final-scaling',str(p),'--json'])==0
 assert json.loads(capsys.readouterr().out)['b_transfer_A2']==80
 assert p.read_bytes()==before and list(tmp_path.iterdir())==[p]
 assert main(['metal','inspect-final-scaling',str(p)])==0
 assert 'Printed final scaling' in capsys.readouterr().out
 p.write_text('no final block')
 assert main(['metal','inspect-final-scaling',str(p),'--json'])==2
 assert json.loads(capsys.readouterr().out)['b_transfer_A2'] is None
