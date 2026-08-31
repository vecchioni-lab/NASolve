from __future__ import print_function
import json
import sys
from iotbx import reflection_file_reader

# NASOLVE_FREE_R_AUDIT
filename, wanted_label, test_text = sys.argv[1:4]
test_value = int(test_text)
reflection_file = reflection_file_reader.any_reflection_file(filename)
try:
    arrays = reflection_file.as_miller_arrays(merge_equivalents=False)
except TypeError:
    arrays = reflection_file.as_miller_arrays()
selected = None
available = []
for array in arrays:
    info = array.info()
    labels = list(getattr(info, "labels", []) or [])
    label_string = info.label_string()
    available.append(label_string)
    if wanted_label in labels or label_string == wanted_label:
        selected = array
        break
if selected is None:
    raise RuntimeError("Free-R label not found; available: " + "; ".join(available))

unit_cell = selected.unit_cell()
indices = list(selected.indices())
data = list(selected.data())
groups = []
matching_method = "cctbx-match-bijvoet-mates"
try:
    matches = selected.match_bijvoet_mates()
    paired_positions = set()
    for first, second in matches.pairs():
        first, second = int(first), int(second)
        paired_positions.update([first, second])
        groups.append({
            "indices": [tuple(indices[first]), tuple(indices[second])],
            "values": set([int(data[first]), int(data[second])]),
            "d": float(unit_cell.d(indices[first])),
        })
    for position in range(len(indices)):
        if position in paired_positions:
            continue
        groups.append({
            "indices": [tuple(indices[position])],
            "values": set([int(data[position])]),
            "d": float(unit_cell.d(indices[position])),
        })
except Exception:
    matching_method = "exact-hkl-fallback"
    exact = {}
    for hkl, raw_value in zip(indices, data):
        index = tuple(int(value) for value in hkl)
        inverse = tuple(-value for value in index)
        key = min(index, inverse)
        item = exact.setdefault(key, {"indices": set(), "values": set(), "d": None})
        item["indices"].add(index)
        item["values"].add(int(raw_value))
        if item["d"] is None:
            item["d"] = float(unit_cell.d(index))
    groups = list(exact.values())

ordered = sorted(groups, key=lambda item: item["d"], reverse=True)
shells = [{"groups": 0, "free_groups": 0} for unused in range(10)]
free_groups = 0
inconsistent = 0
paired = 0
for number, item in enumerate(ordered):
    is_free = test_value in item["values"]
    if is_free:
        free_groups += 1
    if len(item["values"]) > 1:
        inconsistent += 1
    if len(item["indices"]) > 1:
        paired += 1
    shell = min(9, int(number * 10 / max(1, len(ordered))))
    shells[shell]["groups"] += 1
    shells[shell]["free_groups"] += int(is_free)

payload = {
    "array_labels": selected.info().label_string(),
    "array_anomalous": bool(selected.anomalous_flag()),
    "matching_method": matching_method,
    "stored_observations": len(selected.indices()),
    "independent_friedel_groups": len(ordered),
    "paired_friedel_groups": paired,
    "free_independent_groups": free_groups,
    "free_fraction": float(free_groups) / max(1, len(ordered)),
    "inconsistent_friedel_flag_groups": inconsistent,
    "test_flag_value": test_value,
    "resolution_shells": shells,
}
print("NASOLVE_FREE_R_AUDIT_JSON:" + json.dumps(payload, sort_keys=True))
