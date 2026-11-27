"""One source-order recovery under the same complete request and time allowance."""
from time import monotonic

from . import cif_acquisition_attempt as acquisition
from . import cif_acquisition_recovery as recovery
from .cif_dictionary_store import _bytes
from .cif_repair_attempt import _inventory, _need

POLICY_ID = "cif-complete-proven-source-order-recovery-v1"


def permission(enabled):
    _need(type(enabled) is bool, "Source-order recovery requires an explicit boolean")
    return {"connected_order_policy": POLICY_ID} if enabled else {}


def eligible(config, code):
    if config.get("connected_order_policy") != POLICY_ID:
        return False
    recipe = config["components"][code]["dictionary_request"]["recipe"]
    return (config["controls"]["sites"][code]["retained"] is None
            and recipe.get("source_input_policy") == recovery.SOURCE_INPUT_POLICY
            and bool(recipe.get("bond_representation_policy")) and not recipe.get("multiple_planes"))


def directory_name(code, number):
    return f"{code}-order-{number:04d}"


def acquire(source, code, store, primary, number, options):
    """Try the declared recipe. Only its own sealed, eligible failure may start a second job."""
    from .cif_acquisition_attempt import AcquisitionBudgetExceeded

    start = monotonic()
    outer = options["_remaining_seconds"]
    limit = options["total_timeout_seconds"]

    def remaining():
        seconds = min(outer(), limit - (monotonic() - start))
        if seconds <= 0:
            raise AcquisitionBudgetExceeded("No time remains in the original component allowance")
        return seconds

    options = dict(options, _remaining_seconds=remaining)
    try:
        result = acquisition.acquire_dictionary_attempt(source, code, store, primary, **options)
        return primary, result, None
    except ValueError:
        remaining()
        state = acquisition.inspect_acquisition_request(primary)
        if state["state"] != "RECORDED" or state["availability"] == "BLOCKED" or not state["attempts"]:
            raise
        last = state["attempts"][-1]
        if (last["state"] != "STOPPED" or last["finished"]["outcome"] != "RAISED"
                or last["intent"].get("parent_attempt") != options["_parent_attempt_identity"]):
            raise
        earlier = last["number"]
        if recovery.read_connected_order_failure(primary, earlier) is None:
            raise
    remaining()
    destination = primary.with_name(directory_name(code, number))
    _need(not destination.exists() and not destination.is_symlink(), "Source-order recovery requires a fresh request")
    options.update(max_attempts=1, connected_order_failure=(primary, earlier))
    result = acquisition.acquire_dictionary_attempt(source, code, store, destination, **options)
    return destination, result, {"original": earlier, "reordered": result["attempt_number"]}


def inspect(root, code, number, expected, original):
    """Rebind source, consumer, owned failure and limits of a separately reserved recovery."""
    directory = root / "acquisitions" / directory_name(code, number)
    if not directory.exists() and not directory.is_symlink():
        return None
    _need(original is not None and original["state"] == "STOPPED" and original["finished"]["outcome"] == "RAISED",
          "Source-order recovery has no sealed failed sibling")
    primary = root / "acquisitions" / code
    proof = recovery.read_connected_order_failure(primary, original["number"])
    _need(proof is not None, "Source-order recovery is unrelated to the original builder failure")
    state = acquisition.inspect_acquisition_request(directory)
    if state["state"] != "RECORDED":
        return None, {"state": "UNKNOWN", "activity": None}
    request = state["request"]
    ordinary = expected["dictionary_request"]
    recovered = dict(ordinary, recipe=dict(ordinary["recipe"], source_input_policy=recovery.CONNECTED_INPUT_POLICY))
    files = dict(expected["input_files"], **_inventory({recovery.EVIDENCE: _bytes(proof)}))
    wanted = dict(expected, dictionary_request=recovered, input_files=files, max_attempts=1)
    _need(_bytes(request["configuration"]) == _bytes(wanted) and len(state["attempts"]) <= 1,
          "Source-order recovery differs from the authorized source, child or allowance")
    if state["attempts"]:
        child = state["attempts"][0]
        if state["availability"] != "BLOCKED" or child["state"] not in {"STOPPED", "STOPPED_UNFINISHED"}:
            return request, child
    if state["availability"] == "BLOCKED":
        return request, {"state": "UNKNOWN", "activity": None}
    return request, {"state": "NOT_CREATED", "activity": False}


def selection(components, children, bindings):
    """Identify the exact successful acquisition that supplied each prepared component."""
    chosen = {}
    recoveries = {}
    for code in components:
        key = "order/" + code
        if key in children:
            _need(children[code]["state"] == "STOPPED" and children[code]["finished"]["outcome"] == "RAISED"
                  and children[key]["state"] == "STOPPED" and children[key]["finished"]["outcome"] == "RETURNED",
                  "Source-order recovery lacks its sealed failure and successful replacement")
            recoveries[code] = {"original": bindings[code]["number"], "reordered": bindings[key]["number"]}
            chosen[code] = bindings[key]
        else:
            chosen[code] = bindings[code]
    _need(all(child["state"] == "STOPPED" and child["finished"]["outcome"] == "RETURNED"
              for name, child in children.items() if name != "continuation" and name not in recoveries),
          "Complete request has an unsuccessful child")
    return chosen, recoveries
