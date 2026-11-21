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
    source_native_json: bytes | None = None

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
                                   compiler_owner, controls_owner, include_source_native=False):
    """Reopen typed source roles through explicit trusted Cedar owners.

    The expected digest comes from the authenticated compiler-report binding,
    not a newly inferred policy. Cedar's existing reader verifies the source
    artifact; this adapter binds it to exact current-parent bytes and returns
    immutable inputs for the later native service. Repeated checks are snapshot
    checks, not locks or retained-process authority. No native work occurs here.
    Opt in to carrying the declared original native observation bytes for Cedar
    source-chemistry comparison; its native owner still validates them at use.
    """
    if type(include_source_native) is not bool:
        raise ValueError('Original native observation opt-in must be boolean')
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
        source_native=None
        if include_source_native:
            files=report.get('files')
            if not isinstance(files,list):
                raise ValueError('Missing original native observation declaration')
            records=[r for r in files if isinstance(r,dict)
                     and r.get('path')=='native/native_validation.json']
            if len(records)!=1 or records[0].get('anchor')!='literal_na_input_directory':
                raise ValueError('Require one declared original native observation role')
            record=records[0];path=(directory/record['path']).resolve()
            if not path.is_relative_to(directory.resolve()) or path in paths:
                raise ValueError('Original native observation escaped its source or aliases another role')
            if type(record.get('size')) is not int or record['size']<0:
                raise ValueError('Invalid original native observation size')
            source_native=(path,record.get('sha256'),record['size'])
        return payload,model,restraints,controls,source_native
    payload,model,restraints,controls,source_native=read()
    paths=(model,*restraints,*controls,*((source_native[0],) if source_native else ()))
    snapshots={p:p.read_bytes() for p in paths}
    if source_native:
        path,pin,size=source_native
        if len(snapshots[path])!=size or sha256(snapshots[path]).hexdigest()!=pin:
            raise ValueError('Original native observation bytes differ from the declared source')
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
    if (read()!=(payload,model,restraints,controls,source_native)
            or any(p.read_bytes()!=data for p,data in snapshots.items())):
        raise ValueError('Typed preparation inputs changed while binding')
    return NativePreparationInputs(parent_bytes,payload,
        tuple(snapshots[p] for p in restraints),tuple(snapshots[p] for p in controls),
        tuple(sorted(values.items())),policy,
        source_native_json=snapshots[source_native[0]] if source_native else None)


def _builder_step(method):
    """Preserve the first error and deny reuse of any failed native manager."""
    from functools import wraps
    @wraps(method)
    def call(self,*args,**kwargs):
        if self._failure is not None:
            raise RuntimeError('Parent builder failed; discard the manager')
        try:return method(self,*args,**kwargs)
        except BaseException as error:
            self._failure=dict(type=type(error).__name__,message=str(error))
            raise
    return call


class SourceBoundParentBuilder:
    """Concrete W200 builder; explicit trusted readers retain their native ownership.

    Construct after binding the W206 inputs and BEFORE native preparation. The
    Cedar service itself must have been created before any native worker hooks.
    The enclosing worker qualifies all supplied code and owns input/process
    lifetime, binding restoration and disposal on failure. No callbacks are read
    from an artifact. None of these observations grants runtime authority.

    ``geometry_reader(model, processed, payload)`` composes Cedar's live collector
    and topology reviewer, returning ``native_view`` and ``topology``. The latter
    must report MATCH. ``protected_reader(model)`` returns exactly two JSON roles:
    ``model_noncoordinate`` (atoms, scattering and crystal, in stable identity
    order, excluding XYZ) and ``fixed_geometry_inputs`` (None before geometry).
    It must include native ADPs/occupancies/charges, crystal/special positions and
    complete fixed nonbonded inputs through qualified existing readers.
    ``diffraction_reader()`` snapshots the original candidate F-model, including
    observations, flags, coefficients, scales and masks. It is never a parent
    F-model. ``coordinate_writer(model, points)`` only sets the supplied sites.
    These readers supply evidence, not verdict booleans. This class compares it;
    W200 still owns mapped atom correspondence, fixed coordinates and stage order.
    """
    def __init__(self, *, model, bound_inputs, expected_report_sha256,
                 candidate_bytes, service, process_options, atom_reader,
                 geometry_reader, protected_reader, diffraction_reader,
                 coordinate_writer):
        if (not isinstance(bound_inputs,NativePreparationInputs)
                or type(bound_inputs.source_native_json) is not bytes
                or not bound_inputs.source_native_json
                or bound_inputs.report_sha256!=expected_report_sha256
                or type(candidate_bytes) is not bytes or model is None):
            raise ValueError('Require source-bound parent, original native bytes and candidate')
        callbacks=(atom_reader,geometry_reader,protected_reader,diffraction_reader,coordinate_writer)
        if not all(callable(x)for x in callbacks)or not callable(getattr(service,'interpret',None)):
            raise ValueError('Require explicit trusted native readers, service and writer')
        self.model=model;self._model=model;self._bound=bound_inputs
        self._pin=expected_report_sha256;self._candidate=candidate_bytes
        self._service=service;self._options=dict(process_options)
        self._atoms=atom_reader;self._review=geometry_reader;self._protected_reader=protected_reader
        self._diffraction=diffraction_reader;self._writer=coordinate_writer
        self._interpretation=None;self._parent_review=None;self._written=False
        self._complete=False;self._failure=None;self._record=None

    @staticmethod
    def _snapshot(value):
        if not isinstance(value,dict)or not value:
            raise ValueError('Require a nonempty native evidence snapshot')
        return json.loads(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False))

    @staticmethod
    def _digest(value):
        return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

    def _same(self,model):
        if model is not self._model or self.model is not self._model:
            raise ValueError('Builder replaced the bound native manager')

    def _protected(self):
        value=self._snapshot(self._protected_reader(self._model))
        if (set(value)!={'model_noncoordinate','fixed_geometry_inputs'}
                or not isinstance(value['model_noncoordinate'],dict)
                or set(value['model_noncoordinate'])!={'atoms','scattering','crystal'}
                or not all(value['model_noncoordinate'].values())
                or value['fixed_geometry_inputs'] is not None
                   and not isinstance(value['fixed_geometry_inputs'],dict)):
            raise ValueError('Missing protected native state roles')
        return value

    def _unchanged_diffraction(self):
        if self._snapshot(self._diffraction())!=self._initial_diffraction:
            raise ValueError('Candidate diffraction changed during parent preparation')

    def _geometry(self,payload):
        view=self._snapshot(self._review(self._model,self._interpretation.processed,payload))
        if view['topology']['link_status']!='MATCH':
            raise ValueError('Declared parent topology did not match')
        geometry=view['native_view']['geometry']
        if not isinstance(geometry['proxy_details'],dict)or not isinstance(geometry['custom_proxy_requests'],list):
            raise ValueError('Missing retained native geometry definitions')
        return view

    @_builder_step
    def observe_atoms(self,model):
        self._same(model)
        return self._atoms(model)

    @_builder_step
    def interpret_parent(self,model,payload):
        self._same(model)
        if self._interpretation is not None or self._complete:
            raise RuntimeError('Cannot reuse a parent builder')
        if payload!=self._bound.parent_bytes:
            raise ValueError('Geometry parent differs from bound source bytes')
        self._initial_diffraction=self._snapshot(self._diffraction())
        self._initial_protected=self._protected()
        value=self._service.interpret(model,self._bound,expected_report_sha256=self._pin,
            process_options=self._options,source_native_json=self._bound.source_native_json)
        receipt=self._snapshot(value.receipt);chemistry=receipt['source_chemistry']
        if (receipt['policy_id']!='cif-native-parent-interpretation-v1'
                or receipt['source_report_sha256']!=self._pin
                or receipt['parent_sha256']!=self._bound.model_sha256
                or type(receipt['native_interpretations'])is not int or receipt['native_interpretations']!=1
                or chemistry['status']!='MATCH'
                or chemistry['source_native_sha256']!=sha256(self._bound.source_native_json).hexdigest()
                or chemistry['scientific_acceptance']is not False
                or receipt['chemical_admission']is not False or receipt['ordinary_handoff_allowed']is not False):
            raise ValueError('Require exact original source chemistry before transfer')
        self._interpretation=value;self._service_receipt=receipt
        self._unchanged_diffraction()

    @_builder_step
    def verify_parent(self,model,mapping):
        self._same(model)
        if self._interpretation is None or self._parent_review is not None:
            raise RuntimeError('Parent verification is out of order')
        self._geometry_object=model.restraints_manager.geometry
        if self._geometry_object is None:raise ValueError('Missing interpreted native geometry')
        self._parent_protected=self._protected()
        if (self._parent_protected['model_noncoordinate']!=self._initial_protected['model_noncoordinate']
                or self._parent_protected['fixed_geometry_inputs'] is None):
            raise ValueError('Parent interpretation changed protected native state')
        self._parent_review=self._geometry(self._bound.parent_bytes)
        if self._protected()!=self._parent_protected or model.restraints_manager.geometry is not self._geometry_object:
            raise ValueError('Parent observer changed protected state')
        self._unchanged_diffraction()

    @_builder_step
    def set_candidate_sites(self,model,points):
        self._same(model)
        if self._parent_review is None or self._written or self._complete:
            raise RuntimeError('Candidate transfer is out of order')
        if model.restraints_manager.geometry is not self._geometry_object or self._protected()!=self._parent_protected:
            raise ValueError('Prepared geometry or protected state changed before transfer')
        self._unchanged_diffraction();self._written=True
        if self._writer(model,points) is not None:
            raise ValueError('Coordinate writer must raise on failure, not return a verdict')

    @_builder_step
    def verify_candidate(self,model,parent_mapping,candidate_mapping):
        self._same(model)
        if not self._written or self._complete:raise RuntimeError('Candidate verification is out of order')
        if model.restraints_manager.geometry is not self._geometry_object or self._protected()!=self._parent_protected:
            raise ValueError('Transfer changed geometry or protected native state')
        current=self._geometry(self._candidate);previous=self._parent_review
        if self._protected()!=self._parent_protected or model.restraints_manager.geometry is not self._geometry_object:
            raise ValueError('Candidate observer changed protected state')
        if (current['topology']!=previous['topology']or any(
                current['native_view']['geometry'][key]!=previous['native_view']['geometry'][key]
                for key in ('proxy_details','custom_proxy_requests'))):
            raise ValueError('Transfer changed retained topology or restraint definitions')
        self._unchanged_diffraction()
        self._record=dict(status='COMPLETE',runtime_authority=False,scientific_acceptance=False,
            parent_sha256=self._bound.model_sha256,candidate_sha256=sha256(self._candidate).hexdigest(),
            service=self._service_receipt,topology=previous['topology'],
            parent_observation_sha256=self._digest(previous),candidate_observation_sha256=self._digest(current),
            protected_state_sha256=self._digest(self._parent_protected),
            unchanged_candidate_diffraction_sha256=self._digest(self._initial_diffraction))
        self._complete=True

    def result(self):
        if self._failure is not None or not self._complete:
            raise RuntimeError('No completed parent builder result; discard failed managers')
        return self._interpretation

    def evidence(self):
        self.result()
        return deepcopy(self._record)
