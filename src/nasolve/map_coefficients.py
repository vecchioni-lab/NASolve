"""Read-only selection and description of native complex coefficient arrays.

The caller owns file resolution, checksum verification and the existing iotbx
reader. These helpers neither read files nor calculate maps, fit a model or infer
a coefficient-generation policy. They also support a direct native-Python import
without importing the NASolve package or requiring its application dependencies.
"""


def select_complex_array(arrays, labels):
    """Reuse the preview reader's exact, ordered label match and refusal.

    ``labels`` is the explicit list supplied by the caller. The original array
    object is returned unchanged. No first-match fallback, label inference or
    amplitude-only match is permitted; duplicate complex matches are ambiguous.
    """
    matches = [array for array in arrays
               if array.is_complex_array() and array.info().labels == labels]
    if len(matches) != 1:
        raise ValueError('Exact complex map labels not found')
    return matches[0]


def describe_complex_array(array):
    """Describe the selected native array's headers, without examining its data.

    These are reader observations, not proof of producer XYZ/ADPs, absolute origin,
    model/map correspondence, work/free eligibility or independent validation.
    The caller must bind this description to verified bytes and reader version.
    """
    if not array.is_complex_array():
        raise ValueError('Map coefficient description requires a complex array')
    group = array.space_group()
    return {
        'kind': 'map-coefficient-header',
        'schema_version': 1,
        'labels': list(array.info().labels),
        'cell_parameters': list(array.unit_cell().parameters()),
        'space_group': {
            'symbol': str(array.space_group_info()),
            'number': group.type().number(),
            'hall_symbol': group.type().hall_symbol(),
            'operators_xyz': [op.as_xyz() for op in group.all_ops()],
        },
        'reflection_count': array.size(),
        'anomalous': array.anomalous_flag(),
        'generation_evidence': 'not_assessed',
        'model_frame_correspondence': 'not_assessed',
    }


__all__ = ['select_complex_array', 'describe_complex_array']
