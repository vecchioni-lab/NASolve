"""Selected-runtime continuation uses the shared campaign process protocol."""
from .cif_repair_process import _ProcessScope, _OwnedProcesses, _inspect_owned_processes

POLICY_ID = 'cif-runtime-continuation-process-v1'
_SCOPE = _ProcessScope(POLICY_ID, 'continuation_directory', 'inputs',
    'continuation.json', 'inputs', 'input_files', 'continuation_sha256',
    r'native-(baseline|endpoint|ordered)|readyset',
    'SELECTED_RUNTIME_CONTINUATION_WORKERS_ONLY; NO_RETRY_OR_CHEMISTRY_AUTHORITY',
    fixed_paths=(('readyset', 'readyset/readyset', 'readyset/readyset/observer.log'),))


class RuntimeContinuationProcesses(_OwnedProcesses):
    """Own fresh ReadySet/native phases; an enclosing request owns any recovery."""
    _scope = _SCOPE


def inspect_runtime_continuation_processes(root):
    """Read stopped/live/unknown evidence without locks, signalling or retry."""
    return _inspect_owned_processes(root, _SCOPE)
