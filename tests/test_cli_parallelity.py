from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from nasolve.cli import build_parser,main
from nasolve.autorefine import AutoRefineError
from nasolve.refine_doctor import RefineDoctorError
from nasolve.config import AppConfig


def test_plane_force_option_is_explicit_and_default_is_unchanged():
    parser=build_parser()
    assert parser.parse_args(['autorefine']).checked_plane_forces is False
    parsed=parser.parse_args(['autorefine','/explicit/run','--checked-plane-forces','--from','refine-002'])
    assert parsed.checked_plane_forces and parsed.run==Path('/explicit/run') and parsed.from_checkpoint=='refine-002'


@pytest.mark.parametrize('command',['autorefine','refine-doctor'])
@pytest.mark.parametrize('enabled,python_available',[(False,False),(True,False),(True,True)])
def test_explicit_option_forwards_only_the_configured_native_python(enabled,python_available,capsys,command):
    executables={'phenix.refine':Path('/phenix/phenix.refine'),'phenix.mtz.dump':Path('/phenix/phenix.mtz.dump')}
    if python_available:executables['phenix.python']=Path('/phenix/phenix.python')
    installation=SimpleNamespace(version='2.2.1',executables=executables,environment={'PATH':'/phenix'})
    error=AutoRefineError if command=='autorefine' else RefineDoctorError
    target='nasolve.cli.execute_'+command.replace('-','_')
    with (
        patch('nasolve.cli.load_config',return_value=AppConfig()),
        patch('nasolve.cli._workspace_run',return_value=Path('/dataset/AutoMR/run_001')),
        patch('nasolve.cli.discover_phenix',return_value=installation),
        patch('nasolve.cli.remember_phenix'),patch('nasolve.cli.save_config'),
        patch(target,side_effect=error('sentinel')) as execute,
    ):
        assert main([command,'/explicit/run']+(['--checked-plane-forces'] if enabled else []))==2
    if enabled and not python_available:
        execute.assert_not_called();assert 'phenix.python' in capsys.readouterr().err
    else:
        assert execute.call_count==1
        if enabled:
            assert execute.call_args.kwargs['correct_native_parallelity'] is True
            assert execute.call_args.kwargs['phenix_python_executable']==executables['phenix.python']
        else:assert 'correct_native_parallelity' not in execute.call_args.kwargs
