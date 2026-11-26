"""Shared explicit source-array read from the qualified phased-refinement owner.

Extracted from NativePhasedGuard without broadening its observation policy.
Callers authenticate files, selectors and ordinary ancestry before this read.
This supplies no model, target, process, scale permission or acceptance decision.
Native imports are lazy; historical frozen workers remain unchanged.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SourceArrays:
    crystal: object
    observations: list
    hl: list
    flags: list


def indexed_values(indices, values, role):
    """Preserve the existing index join; never silently drop duplicate rows."""
    if len(indices) != len(values) or not indices:
        raise ValueError('Empty or mismatched ' + role)
    result = {}
    for h, value in zip(indices, values):
        if len(h) != 3 or any(type(v) is not int for v in h) or tuple(h) in result:
            raise ValueError('Duplicate or invalid indices in ' + role)
        result[tuple(h)] = value
    return result


def read_source_arrays(*, data_file, phase_file, data_labels, free_label,
                       phase_labels, test_flag_value):
    """Read exact named amplitude/Free-R/HL arrays and join them by Miller index.

    HL must cover exactly the merged observations. Original integer flags may
    include additional reflections but must cover every observation. Explicit
    Bijvoet averaging and ASU mapping retain the established source semantics;
    no intensity conversion, nonpositive-data filtering or phase substitution.
    Values are call-local captures; callers pin files and detach saved records.
    """
    from iotbx import reflection_file_reader

    def array(path, labels):
        matches = [a for a in reflection_file_reader.any_reflection_file(str(path)).as_miller_arrays()
                   if a.info().labels == labels]
        if len(matches) != 1:
            raise ValueError('Require exactly the requested native reflection labels')
        a = matches[0].map_to_asu()
        if not a.is_unique_set_under_symmetry():
            raise ValueError('Source reflections must be unique under symmetry')
        return a

    fo = array(data_file, data_labels)
    flags = array(data_file, [free_label])
    hl = array(phase_file, phase_labels)
    if not fo.is_xray_amplitude_array() or fo.sigmas() is None:
        raise ValueError('Phased local scope requires measured amplitudes with sigmas')
    if fo.anomalous_flag():
        fo = fo.average_bijvoet_mates().map_to_asu()
    if flags.anomalous_flag() or hl.anomalous_flag() or not hl.is_hendrickson_lattman_array():
        raise ValueError('Require non-anomalous source flags and HL quartet')
    for a in (flags, hl):
        if (a.space_group() != fo.space_group() or
                not a.unit_cell().is_similar_to(fo.unit_cell(),
                    relative_length_tolerance=1e-10, absolute_angle_tolerance=1e-10)):
            raise ValueError('Source diffraction arrays have different crystals')
    indices = list(map(list, fo.indices()))
    flag_lookup = indexed_values(list(map(list, flags.indices())), list(flags.data()), 'source flags')
    hl_lookup = indexed_values(list(map(list, hl.indices())), [list(v) for v in hl.data()], 'source HL')
    if set(map(tuple, indices)) != set(hl_lookup) or any(tuple(h) not in flag_lookup for h in indices):
        raise ValueError('Source phases/flags do not cover the complete observation set')
    if any(type(v) is not int for v in flag_lookup.values()):
        raise ValueError('Require integer source Free-R flags')
    flag_values = [flag_lookup[tuple(h)] == test_flag_value for h in indices]
    observations = [[h, float(f), float(s), b] for h,f,s,b in
                    zip(indices, fo.data(), fo.sigmas(), flag_values)]
    if any(not math.isfinite(v) or v <= 0 for r in observations for v in r[1:3]):
        raise ValueError('Source amplitudes/sigmas require explicit positive-data qualification')
    return SourceArrays(fo.crystal_symmetry(), observations,
                        [indices, [hl_lookup[tuple(h)] for h in indices]],
                        [indices, flag_values])
