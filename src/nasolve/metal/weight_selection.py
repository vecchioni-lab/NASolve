"""Compact passive evidence of native XYZ weight selection, not a selector.

Read existing scorer arrays only. No geometry/target evaluation is performed.
Native bond and angle summaries retain their native (potentially mixed) scope.
The native worker imports this module directly, without importing NASolve.
"""
from functools import wraps
import hashlib
import inspect
import json
import math
from pathlib import Path
import re

PROTOCOL = 'metal-xyz-weight-selection-v1'
MAX_TRIALS = 4096
MAX_DECISIONS = 256
FIELDS = ('rw', 'rf', 'rfrw', 'b', 'a', 'clsc', 'rama', 'rota', 'cbet', 'w')
CRITERIA = ('r_free_range_width', 'r_free_r_work_gap', 'bond_rmsd', 'angle_rmsd')


def _hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _rows(scorer):
    columns = {name: list(getattr(scorer, name)) for name in FIELDS}
    n = len(columns['w'])
    if n > MAX_TRIALS or any(len(v) != n for v in columns.values()):
        raise ValueError('Invalid native weight trial inventory')
    if len(scorer.sites_frac_all) != n:
        raise ValueError('Native weight coordinates differ from trial inventory')
    return [dict({name: columns[name][i] for name in FIELDS},
                 sites_frac_sha256=_hash([list(x) for x in scorer.sites_frac_all[i]]))
            for i in range(n)]


class _Observer:
    def __init__(self, module, sources):
        self.module = module
        self.sources = sources
        self.decisions = []
        self.bindings = []
        self.active = None
        self.context = None
        self.entered = False
        self.complete = False
        self.restored = False

    def _install(self, owner, name, wrapper):
        self.bindings.append((owner, name, getattr(owner, name), wrapper))
        setattr(owner, name, wrapper)

    def __enter__(self):
        m = self.module
        if self.entered or hasattr(m, '_nasolve_weight_observer'):
            raise ValueError('Native weight observation already owned')
        self.entered = True
        original_run = m.run_all.__init__
        original_finalize = m.xyz_refinement_scorer.finalize
        original_select = m.xyz_refinement_scorer._select
        run_signature = inspect.signature(original_run)
        final_signature = inspect.signature(original_finalize)

        @wraps(original_run)
        def run(*args, **kwargs):
            if self.context is not None:
                raise ValueError('Nested native XYZ weight run')
            bound = run_signature.bind(*args, **kwargs)
            self.context = dict(cycle=bound.arguments['macro_cycle'], runner=args[0])
            try:
                return original_run(*args, **kwargs)
            finally:
                self.context = None

        @wraps(original_finalize)
        def finalize(scorer, *args, **kwargs):
            if scorer.finalized:
                return original_finalize(scorer, *args, **kwargs)
            if self.context is None or self.active is not None:
                raise ValueError('Native selector lacks an owned XYZ run')
            before = _rows(scorer)
            if (not before or len(self.decisions) >= MAX_DECISIONS or
                    sum(len(d['trials']) for d in self.decisions)+len(before) > MAX_TRIALS):
                raise ValueError('Native weight observation limit reached')
            bound = final_signature.bind(scorer, *args, **kwargs)
            runner = self.context['runner']
            d = dict(sequence=len(self.decisions)+1, cycle=self.context['cycle'],
                     r_free_only=scorer.r_free_only, eps=scorer.eps,
                     wx_scale=runner.wx_scale,
                     criteria={k: bound.arguments[k] for k in CRITERIA},
                     trials=before, steps=[], finalized=False, selected_index=None)
            self.decisions.append(d)
            self.active = (scorer, d, list(range(len(before))))
            try:
                value = original_finalize(scorer, *args, **kwargs)
                indices = self.active[2]
                if not scorer.finalized or _rows(scorer) != [before[i] for i in indices]:
                    raise ValueError('Native weight final state changed outside selection')
                d.update(finalized=True, selected_index=indices[0], remaining_indices=indices)
                return value
            finally:
                self.active = None

        @wraps(original_select)
        def select(scorer, sel):
            if self.active is None or self.active[0] is not scorer:
                raise ValueError('Native selector step outside owned finalization')
            _, d, indices = self.active
            mask = list(sel)
            if len(mask) != len(indices) or any(type(x) is not bool for x in mask):
                raise ValueError('Native weight selection mask changed')
            if len(d['steps']) >= 4:
                raise ValueError('Unsupported native weight selection stages')
            rows = [d['trials'][i] for i in indices]
            if _rows(scorer) != rows:
                raise ValueError('Native weight trials changed between stages')
            value = original_select(scorer, sel)
            fallback = not any(mask)
            effective = mask if not fallback else [abs(r['rf']-min(x['rf'] for x in rows)) < 1e-4 for r in rows]
            remaining = [i for i, keep in zip(indices, effective) if keep]
            if _rows(scorer) != [d['trials'][i] for i in remaining]:
                raise ValueError('Native weight selection differs from observed subset')
            d['steps'].append(dict(requested_mask=mask, fallback=fallback, remaining_indices=remaining))
            self.active = (scorer, d, remaining)
            return value

        m._nasolve_weight_observer = self
        self._install(m.run_all, '__init__', run)
        self._install(m.xyz_refinement_scorer, 'finalize', finalize)
        self._install(m.xyz_refinement_scorer, '_select', select)
        return self

    def __exit__(self, exc_type, exc, tb):
        owned = True
        for owner, name, original, wrapper in reversed(self.bindings):
            if getattr(owner, name) is wrapper:
                setattr(owner, name, original)
            else:
                owned = False
        if getattr(self.module, '_nasolve_weight_observer', None) is self:
            del self.module._nasolve_weight_observer
        self.restored = owned
        self.complete = exc_type is None and owned
        if not owned and exc_type is None:
            raise ValueError('Native weight observation lost ownership')
        return False

    def receipt(self):
        return dict(protocol=PROTOCOL,
                    implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    native_sources=dict(self.sources), entry_binding_authentication='NOT_ASSESSED',
                    capture_complete=self.complete, binding_restored=self.restored,
                    decisions=self.decisions)


def observe(*, _module=None, _source_hashes=None):
    if _module is None:
        import phenix.refinement.xyz_reciprocal_space as native
        _module = native
        _source_hashes = {'xyz_reciprocal_space': hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()}
    return _Observer(_module, _source_hashes)


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Nonfinite or invalid native weight metric')


def _index(value):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid native weight index')


def _fingerprint(value):
    if not isinstance(value, str) or re.fullmatch('[a-f0-9]{64}', value) is None:
        raise ValueError('Invalid native weight source or coordinate fingerprint')


def summarize(evidence):
    """Independently replay scalar masks and subsets; never run a native fit."""
    if (not isinstance(evidence, dict) or evidence.get('protocol') != PROTOCOL
            or evidence.get('capture_complete') is not True
            or evidence.get('binding_restored') is not True
            or evidence.get('entry_binding_authentication') != 'NOT_ASSESSED'):
        raise ValueError('Incomplete native weight observation')
    sources = evidence.get('native_sources')
    if not isinstance(sources, dict) or set(sources) != {'xyz_reciprocal_space'}:
        raise ValueError('Missing native weight source provenance')
    for value in [evidence.get('implementation_sha256'), *sources.values()]:
        _fingerprint(value)
    decisions = evidence.get('decisions')
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= MAX_DECISIONS:
        raise ValueError('Invalid native weight decision inventory')
    total = 0
    output = []
    for sequence, d in enumerate(decisions, 1):
        if not isinstance(d, dict):
            raise ValueError('Invalid native weight decision')
        for field in ('sequence', 'cycle', 'selected_index'):
            _index(d.get(field))
        if (d['sequence'] != sequence or d['cycle'] < 1 or d.get('finalized') is not True
                or type(d.get('r_free_only')) is not bool):
            raise ValueError('Invalid native weight sequence or completion')
        for field in ('eps', 'wx_scale'):
            _number(d.get(field))
        if d['eps'] != 1e-4 or d['wx_scale'] <= 0:
            raise ValueError('Unsupported native weight tolerance or scale')
        c = d.get('criteria')
        if not isinstance(c, dict) or set(c) != set(CRITERIA):
            raise ValueError('Invalid native weight criteria')
        for value in c.values():
            _number(value)
            if value < 0:
                raise ValueError('Negative native weight criterion')
        trials, steps = d.get('trials'), d.get('steps')
        if not isinstance(trials, list) or not trials or not isinstance(steps, list):
            raise ValueError('Invalid native weight trials or stages')
        total += len(trials)
        if total > MAX_TRIALS:
            raise ValueError('Native weight trial limit exceeded')
        for t in trials:
            if not isinstance(t, dict) or set(t) != set(FIELDS) | {'sites_frac_sha256'}:
                raise ValueError('Invalid native weight trial fields')
            for name in FIELDS:
                _number(t[name])
            _fingerprint(t['sites_frac_sha256'])
            if abs(t['rfrw']-(t['rf']-t['rw'])) > 1e-12:
                raise ValueError('Native R gap disagrees with trial metrics')
        expected_stages = 0 if len(trials) == 1 else 1 if d['r_free_only'] else 4
        if len(steps) != expected_stages:
            raise ValueError('Unexpected native weight stage count')
        indices = list(range(len(trials)))
        for stage, step in enumerate(steps):
            rows = [trials[i] for i in indices]
            if stage == 0:
                if d['r_free_only']:
                    mask = [t['b'] <= .029 and t['rf'] <= min(x['rf'] for x in rows)+1e-6 for t in rows]
                else:
                    mask = [t['b'] <= c['bond_rmsd'] and t['a'] <= c['angle_rmsd']
                            and t['rfrw'] <= c['r_free_r_work_gap']/100.
                            and t['rf'] <= min(x['rf'] for x in rows)+c['r_free_range_width']/100. for t in rows]
            elif stage == 1:
                omit_clash = all(t['clsc'] == 99999 for t in rows)
                scores = [round(t['rama']+t['rota']+t['cbet']+(0 if omit_clash else t['clsc']), 1) for t in rows]
                mask = [score <= min(scores) for score in scores]
            else:
                key = 'rf' if stage == 2 else 'rfrw'
                mask = [abs(t[key]-min(x[key] for x in rows)) <= d['eps'] for t in rows]
            if (not isinstance(step, dict) or set(step) != {'requested_mask','fallback','remaining_indices'}
                    or not isinstance(step['requested_mask'], list)
                    or any(type(x) is not bool for x in step['requested_mask'])
                    or step['requested_mask'] != mask or step['fallback'] is not (not any(mask))):
                raise ValueError('Native weight mask or fallback disagrees with replay')
            effective = mask if any(mask) else [abs(t['rf']-min(x['rf'] for x in rows)) < 1e-4 for t in rows]
            indices = [i for i, keep in zip(indices, effective) if keep]
            if step['remaining_indices'] != indices or any(type(i) is not int for i in step['remaining_indices']):
                raise ValueError('Native weight subset disagrees with replay')
        if (not indices or d.get('remaining_indices') != indices or d['selected_index'] != indices[0]
                or any(type(i) is not int for i in d['remaining_indices'])):
            raise ValueError('Native weight choice disagrees with replay')
        output.append(dict(sequence=sequence, cycle=d['cycle'], trial_count=len(trials),
            mode='SINGLE_TRIAL' if len(trials)==1 else 'RFREE_FALLBACK' if steps[0]['fallback'] else 'NATIVE_CRITERIA',
            criteria=dict(c), r_free_only=d['r_free_only'], wx_scale=d['wx_scale'],
            initial_eligible_count=None if not steps else sum(steps[0]['requested_mask']),
            selected_index=d['selected_index'], selected_trial=dict(trials[indices[0]])))
    return dict(protocol=PROTOCOL, decisions=output, trial_count=total,
                native_sources=dict(sources), implementation_sha256=evidence['implementation_sha256'],
                entry_binding_authentication='NOT_ASSESSED',
                source_scope='On-disk native file; not authentication of pre-existing runtime callables',
                metric_scope='Native scorer bond/angle summaries; no covalent-only interpretation',
                r_factor_scope='Trial XYZ summary; not final post-ADP/scale R factors',
                selected_endpoint_attribution='NOT_ASSESSED', scientific_acceptance='NOT_ASSESSED',
                automatic_checkpoint_selection=False)


def verify_file(evidence, directory):
    path = Path(directory) / 'weight-selection.json'
    if 'weight_selection' not in evidence:
        if path.exists() or path.is_symlink():
            raise ValueError('Unexpected weight selection sidecar')
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing weight selection sidecar')
    saved = json.loads(path.read_text())
    encode = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
    if encode(saved) != encode(evidence['weight_selection']):
        raise ValueError('Weight selection sidecar differs from native evidence')
