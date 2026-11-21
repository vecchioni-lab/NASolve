"""One-shot coordinate-role ordering around a caller-qualified native builder.

Source-input binding delegates authentication to explicit trusted Cedar readers.
No native monkeypatch, process, force or execution policy lives here.
Cedar's builder owns the actual interpretation and chemistry/diffraction proof;
the enclosing worker owns input lifetime and disposal of every failed manager.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .topostitch_endpoint import NativeEndpointMapping, map_native_endpoint


class NativeEndpointPreparation:
    """Use exactly one bound parent interpretation and candidate transfer.

    ``initial_mapping`` must come from the trusted W198 admission join and name
    the actual initial candidate, not an arbitrary newly hashed proposal. Its
    source index basis is raw PDB record order. Native order may change during
    interpretation; no initial index is reused for the prepared manager.

    ``builder`` is trusted executable code, source-qualified by the outer worker,
    never loaded from an artifact. It exposes one stable ``model`` and methods:
      observe_atoms(model) -> maintained Cedar atom observation;
      interpret_parent(model, parent_bytes) -> None;
      verify_parent(model, parent_mapping) -> None or raise;
      set_candidate_sites(model, candidate_points) -> None;
      verify_candidate(model, parent_mapping, candidate_mapping) -> None or raise.

    The builder must prove exactly one qualified native interpretation, complete
    declared source chemistry/topology, unchanged candidate diffraction and
    protected crystal/scattering/ADPs. Its final verifier must prove retention
    through transfer on the same manager. Returning None is protocol completion,
    not independent scientific evidence: retain the builder's actual observations.
    This class only owns stage order and W198 identity/coordinate checks.
    All failure paths invalidate the result; the caller discards the manager.
    """
    def __init__(self, source, candidate, points, *, initial_mapping,
                 max_displacement_angstrom, native_owner, builder):
        if (type(source) is not bytes or type(candidate) is not bytes
                or not isinstance(initial_mapping, NativeEndpointMapping)
                or initial_mapping.native_model_role != 'candidate'
                or initial_mapping.source_index_basis != 'SOURCE_PDB_ATOM_RECORD_ORDER'):
            raise ValueError('Require bound bytes and an admitted initial candidate mapping')
        points=tuple(tuple(p) for p in points)
        order=initial_mapping.native_to_source
        ids=initial_mapping.movable_native_indices
        if (any(type(i) is not int for i in order) or sorted(order)!=list(range(len(points)))
                or any(type(i) is not int or not 0<=i<len(order) for i in ids)):
            raise ValueError('Invalid admitted source/native indices')
        methods=('observe_atoms','interpret_parent','verify_parent','set_candidate_sites','verify_candidate')
        if getattr(builder,'model',None) is None or not all(callable(getattr(builder,n,None)) for n in methods):
            raise ValueError('Require an explicit qualified native builder')
        self._source=source;self._candidate=candidate;self._points=points
        self._initial=initial_mapping;self._builder=builder;self._model=builder.model
        self._options=dict(movable_indices=tuple(order[i] for i in ids),
            max_displacement_angstrom=max_displacement_angstrom,
            expected_audit_sha256=initial_mapping.endpoint_audit_sha256,native_owner=native_owner)
        self._parent=None;self._candidate_mapping=None;self._closed=False
        self._record=dict(status='NEW',interpretation_requests=0,coordinate_transfers=0,
            endpoint_audit_sha256=initial_mapping.endpoint_audit_sha256,
            runtime_authority=False,scientific_acceptance=False,
            native_binding_cleanup_owned_by='OUTER_BUILDER',failed_manager_action='DISCARD')

    def _fail(self, error):
        self._record['status']='FAILED'
        self._record.setdefault('error',dict(type=type(error).__name__,message=str(error)))

    def _same_model(self):
        if self._record['status']=='FAILED':
            raise RuntimeError('Native preparation was invalidated; discard the manager')
        if self._builder.model is not self._model:
            raise ValueError('Native builder replaced the bound manager')

    def _observe(self, role):
        self._same_model()
        atoms=self._builder.observe_atoms(self._model)
        self._same_model()
        return map_native_endpoint(self._source,self._candidate,self._points,
            native=atoms,native_model_role=role,**self._options)

    def _call(self, method, *args):
        self._same_model()
        result=getattr(self._builder,method)(self._model,*args)
        self._same_model()
        if result is not None:
            raise ValueError('Native builder must raise on failure, not return a verdict: '+method)

    def __enter__(self):
        if self._closed or self._record['status']!='NEW':
            error=RuntimeError('Cannot reuse native preparation context');self._fail(error);raise error
        self._record['status']='ACTIVE'
        return self

    def prepare(self):
        """Build/check parent geometry once, then transfer rounded candidate sites."""
        try:
            if self._closed or self._record['status']!='ACTIVE':
                raise RuntimeError('Prepare must run exactly once inside its active context')
            self._record['status']='PREPARING'
            if self._observe('candidate')!=self._initial:
                raise ValueError('Initial native mapping changed before preparation')
            self._record['interpretation_requests']+=1
            self._call('interpret_parent',self._source)
            self._parent=self._observe('parent')
            self._call('verify_parent',self._parent)
            if self._observe('parent')!=self._parent:
                raise ValueError('Parent verification changed the bound native atoms')
            self._record['coordinate_transfers']+=1
            self._call('set_candidate_sites',self._parent.candidate_points)
            self._candidate_mapping=self._observe('candidate')
            if self._candidate_mapping.native_to_source!=self._parent.native_to_source:
                raise ValueError('Candidate transfer changed prepared atom order')
            self._record['status']='PREPARED'
        except BaseException as error:
            self._fail(error);raise

    def __exit__(self, kind, error, traceback):
        try:
            if kind is not None:
                self._fail(error)
                return False
            if self._record['status']!='PREPARED':
                raise RuntimeError('Native preparation did not complete; discard the manager')
            if self._observe('candidate')!=self._candidate_mapping:
                raise ValueError('Candidate changed before preparation closure')
            self._call('verify_candidate',self._parent,self._candidate_mapping)
            if self._observe('candidate')!=self._candidate_mapping:
                raise ValueError('Candidate verification changed the bound native atoms')
            self._record['status']='COMPLETE'
        except BaseException as failure:
            self._fail(failure);raise
        finally:
            self._closed=True
        return False

    def result(self):
        if not self._closed or self._record['status']!='COMPLETE':
            raise RuntimeError('No completed native preparation result')
        return self._candidate_mapping

    def statistics(self):
        return deepcopy(self._record)


@dataclass(frozen=True)
class NativePreparationInputs:
    """Detached typed source bytes, never a chemical or runtime permission.

    ``source_report_json`` preserves the complete original compiler report;
    its canonical digest is distinct from a raw JSON-file checksum. PHIL tuples
    preserve each role's byte order without wrapping, merging or editing them.
    A later Cedar consumer must revalidate its live scope and actual parameters.
    """
    parent_bytes: bytes
    source_report_json: bytes
    compiled_restraint_phils: tuple[bytes, ...]
    interpretation_control_phils: tuple[bytes, ...]
    reader_controls: tuple[tuple[str, bool], ...]
    reader_policy: str

    @property
    def report_sha256(self):
        return sha256(self.source_report_json).hexdigest()

    @property
    def model_sha256(self):
        return sha256(self.parent_bytes).hexdigest()

    @property
    def runtime_authority(self):
        return False

    @property
    def chemical_admission(self):
        return False


def bind_native_preparation_inputs(directory, parent_bytes, *, expected_report_sha256,
                                   compiler_owner, controls_owner):
    """Reopen typed source roles through explicit trusted Cedar owners.

    The expected digest comes from the authenticated compiler-report binding,
    not a newly inferred policy. Cedar's existing reader verifies the source
    artifact; this adapter binds it to exact current-parent bytes and returns
    immutable inputs for the later native service. Repeated checks are snapshot
    checks, not locks or retained-process authority. No native work occurs here.
    """
    policy='cif-captured-reader-control-handoff-v1'
    if type(parent_bytes) is not bytes or controls_owner.POLICY_ID!=policy:
        raise ValueError('Require exact parent bytes and the supported reader-control owner')
    directory=Path(directory)
    def read():
        value=compiler_owner._compiler_input('literal_na_inputs',directory,
                                            reader_control_policy=policy)
        report=value['report']
        payload=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if (report.get('policy_id')!='cif-typed-native-literal-inputs-v1'
                or sha256(payload).hexdigest()!=expected_report_sha256):
            raise ValueError('Typed source compiler report differs from the expected binding')
        restraints=tuple(Path(p).resolve() for p in value['compiled_restraint_phils'])
        controls=tuple(Path(p).resolve() for p in value['interpretation_control_phils'])
        model=Path(value['model']).resolve();paths=(model,*restraints,*controls)
        if (not restraints or not controls or len(set(paths))!=len(paths)
                or tuple(Path(p).resolve() for p in value['phils'])!=restraints):
            raise ValueError('Require separate unambiguous ordered restraint and control roles')
        return payload,model,restraints,controls
    payload,model,restraints,controls=read()
    snapshots={p:p.read_bytes() for p in (model,*restraints,*controls)}
    if snapshots[model]!=parent_bytes:
        raise ValueError('Typed source belongs to a different current parent')
    values={};seen=set()
    for p in controls:
        parsed,_=controls_owner.control_definitions(snapshots[p],seen)
        values.update(parsed)
    if (set(values)!=controls_owner.CONTROLS or len(values)!=4
            or any(v is not False for v in values.values())):
        raise ValueError('Require all four authenticated False reader controls')
    controls_owner.reject_shadow_controls(list(restraints))
    if (read()!=(payload,model,restraints,controls)
            or any(p.read_bytes()!=data for p,data in snapshots.items())):
        raise ValueError('Typed preparation inputs changed while binding')
    return NativePreparationInputs(parent_bytes,payload,
        tuple(snapshots[p] for p in restraints),tuple(snapshots[p] for p in controls),
        tuple(sorted(values.items())),policy)
