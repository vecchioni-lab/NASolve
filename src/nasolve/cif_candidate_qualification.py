"""Process ownership for the existing two-seed isolated qualification protocol.

This is execution evidence only. The scientific callback must still qualify both
source/candidate coordinate seeds and compare covalent proxy signatures. There
is no acquisition lock, retry authority, shared budget or qualification claim in
this layer. Campaign primitives own cleanup; saved argv is never replayed.
"""
from .cif_repair_process import _ProcessScope, _OwnedProcesses, _inspect_owned_processes

POLICY_ID = 'cif-candidate-qualification-process-v1'
_SCOPE = _ProcessScope(POLICY_ID, 'qualification_directory', 'inputs',
    'qualification.json', 'inputs', 'input_files', 'qualification_sha256',
    r'native-00[01]', 'ISOLATED_QUALIFICATION_EXECUTION_ONLY; NOT_ACQUISITION_OR_CHEMISTRY')


class CandidateQualificationProcesses(_OwnedProcesses):
    """Freeze explicit inputs and own at most two fresh native invocations.

    The caller prepares inputs before construction, and uses native/000 and
    native/001 capture parents. No input basename discovery or saved command
    execution is performed. A stopped process does not imply usable chemistry.
    """
    _scope = _SCOPE


def inspect_candidate_qualification_processes(root):
    """Observe stopped/live/unknown without mutation, replay or retry authority."""
    return _inspect_owned_processes(root, _SCOPE)
