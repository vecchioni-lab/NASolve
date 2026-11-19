"""Measured, read-only model/map projections over the existing view resolver.

A snapshot pins the files inspected now. It does not certify which model or
procedure generated the coefficients, prove coordinate-frame correspondence,
select a checkpoint, or authorize refinement. No native program is launched.
"""
from __future__ import annotations

from pathlib import Path

from .checkpoints import _file_reference
from .coot_view import resolve_view_profile
from .run_context import resolve_artifact_path


class InspectionError(ValueError):
    """The selected files could not form a consistent inspection snapshot."""


def inspect_model_map(run_directory: Path, **selection: object) -> dict[str, object]:
    """Return a JSON-ready snapshot without writing or changing the selected run.

    Selection keywords are forwarded unchanged to ``resolve_view_profile``;
    the installed owner defines available stage/checkpoint/preparation options.
    Artifact references and hashing reuse the checkpoint/run-context owners.
    Hashes are freshly measured, including for legacy inputs: they are not
    retroactive producer checksums. Explicit external files remain usable and
    are labelled rather than described as relocatable anchored artifacts.

    Recheck both the selected view and measured files before returning. A later
    consumer must revalidate references again at its own action boundary; this
    read is not a filesystem lock or a scientific approval record.
    """
    run = run_directory.expanduser().resolve()
    profile = resolve_view_profile(run, **selection)
    measured: dict[Path, dict[str, object]] = {}

    def reference(path: Path) -> dict[str, object]:
        resolved = path.resolve()
        if resolved not in measured:
            measured[resolved] = _file_reference(resolved, run)
        return dict(measured[resolved])

    artifacts = {
        'model': reference(profile.model_path),
        'map': reference(profile.map_path),
        'extra_models': [reference(path) for path in profile.extra_model_paths],
        'dictionaries': [reference(path) for path in profile.dictionary_paths],
        'anomalous_map_candidates': [reference(path) for path in profile.anomalous_map_paths],
    }
    if resolve_view_profile(run, **selection) != profile:
        raise InspectionError('View selection changed during inspection; resolve it again')
    for path, ref in measured.items():
        resolved = resolve_artifact_path(ref, run)
        if resolved != path or resolved.stat().st_size != ref['size']:
            raise InspectionError('Selected artifact changed during inspection; resolve it again')

    origin = profile.map_origin
    origin_record = None if origin is None else {
        'stage': origin.stage,
        'checkpoint_id': origin.checkpoint_id,
        'inherited_through': list(origin.inherited_through),
    }
    selected = {'stage': profile.stage, 'checkpoint_id': profile.checkpoint_id}
    attempt = getattr(profile, 'preparation_attempt', None)
    if attempt is not None:
        selected['preparation_attempt'] = attempt
    return {
        'kind': 'model-map-inspection',
        'schema_version': 1,
        'selection': selected,
        'source': profile.source,
        'map_source': profile.map_source,
        'map_origin': origin_record,
        'artifacts': artifacts,
        'artifact_hash_basis': 'measured_at_inspection',
        'reference_scope': (
            'contains_external_paths' if any(ref['anchor'] == 'absolute' for ref in measured.values())
            else 'anchored'
        ),
        'generation_evidence': 'not_assessed',
        'frame_evidence': 'not_assessed',
    }


__all__ = ['InspectionError', 'inspect_model_map']
