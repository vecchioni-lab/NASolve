"""Explicit source representation in native generation and read-only replay.

The host derives permission from the maintained chemical classifier. The worker
checks exact inventories against that contract; it never edits native bond orders.
Historical generation workers and mixed-recovery receipts remain unchanged.
"""
from copy import deepcopy
from hashlib import sha256
from inspect import getsource
import json
from pathlib import Path

from .cif_purine_representation import POLICY_ID as REPRESENTATION_POLICY, validate_policy

POLICY_ID = "cif-source-native-complete-candidate-v2"
CONTRACT_POLICY = "cif-source-native-representation-contract-v1"


def generation_representation_contract(source, code, policy):
    from .cif_doctor import assess_dictionaries
    from .cif_generation import _bond_representation
    from .cif_purine_representation import purine_bond_representation, _charges
    validate_policy(policy)
    if policy is None:
        raise ValueError("An explicit representation policy is required")
    source = Path(source)
    assessment = assess_dictionaries([source], stage="source")
    components = assessment["components"]
    if (len(components) != 1 or components[0]["component_id"] != code
            or components[0]["verdicts"]["graph"] != "PASS"
            or assessment["input_integrity"] != "UNCHANGED"
            or _charges(components[0]["inventory"]["atoms"]) is None):
        raise ValueError("Require one valid source graph and complete unambiguous formal charges")
    source_component = components[0]
    projected = deepcopy(source_component)
    for row in projected["inventory"]["bond_orders"]:
        if set(row["aromatic_declarations"].values()) == {"Y"}:
            row["declarations"] = {"type": "AROMATIC"}
    representation = purine_bond_representation(source_component, projected,
        _bond_representation(source_component, projected))
    if representation["status"] not in {"EXACT", "SOURCE_DECLARED_EQUIVALENT"}:
        raise ValueError("Source aromatic conversion is outside the explicit representation policy")
    systems = representation["equivalent_rings"] + representation["equivalent_fused_systems"]
    return {"schema_version": 1, "policy_id": CONTRACT_POLICY, "representation_policy": policy,
            "component": code, "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "representation": representation,
            "allowed_systems": [[b["atoms"] for b in row["bonds"]] for row in systems]}


def native_representation_check(snapshot, expected, contract, *, coordinates=False, charges=False):
    """Pure worker-safe check; only a complete authorized ring may become 1.5."""
    import math
    checks = {}
    converted = []
    try:
        rows = snapshot["atoms"]
        atoms = {r["atom"]: r for r in rows}
        elements = expected["elements"]
        checks["atom_identities"] = len(atoms) == len(rows) == len(elements) and set(atoms) == set(elements)
        checks["atom_elements"] = checks["atom_identities"] and all(atoms[n]["element"].upper() == e for n, e in elements.items())
        bonds = snapshot["bonds"]
        actual = {tuple(sorted(r["atoms"])): r["native_order"] for r in bonds}
        wanted = {tuple(r["atoms"]): r["order"] for r in expected["bonds"]}
        checks["exact_connectivity"] = (len(actual) == len(bonds) == len(wanted) == len(expected["bonds"])
            and actual.keys() == wanted.keys()
            and all(len(r["atoms"]) == 2 and r["atoms"][0] != r["atoms"][1] for r in bonds))
        checks["finite_native_orders"] = all(type(v) in (int, float) and math.isfinite(v) for v in actual.values())
        changed = {edge for edge in wanted if actual.get(edge) != wanted[edge]}
        covered = set()
        for system in contract["allowed_systems"]:
            edges = {tuple(edge) for edge in system}
            if edges & changed and edges <= wanted.keys() and all(actual.get(edge) == 1.5 for edge in edges):
                covered.update(edges)
                converted.append(system)
        checks["authorized_complete_representation"] = checks["exact_connectivity"] and checks["finite_native_orders"] and changed <= covered
        checks["finite_coordinates"] = all(len(r["xyz"]) == 3 and all(type(x) in (int, float) and math.isfinite(x) for x in r["xyz"]) for r in rows)
        if coordinates:
            checks["source_coordinates"] = checks["atom_identities"] and checks["finite_coordinates"] and all(
                all(math.isclose(x, y, abs_tol=1e-9, rel_tol=0) for x, y in zip(atoms[n]["xyz"], expected["coordinates"][n])) for n in elements)
        if charges:
            checks["source_formal_charges"] = checks["atom_identities"] and all(type(atoms[n]["native_atom_charge"]) is int
                and atoms[n]["native_atom_charge"] == expected["charges"][n] for n in elements)
            checks["source_total_charge"] = type(snapshot["molecule_charge"]) is int and snapshot["molecule_charge"] == sum(expected["charges"].values())
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        checks["complete_native_inventory"] = False
    return {"policy_id": "cif-source-native-representation-contract-v1",
            "status": "SOURCE_REPRESENTATION_PASS" if checks and all(checks.values()) else "BLOCKED",
            "checks": checks, "converted_systems": converted, "native_bond_order_editing": "NOT_RUN"}


def source_representation_worker(base):
    """Create the opt-in worker, preserving the historical worker byte-for-byte."""
    old = " result['charge_control']=control_declared_charges(molecule,spec['declared_charge_control'])"
    new = r''' result["representation_handoff"]=native_representation_check(result["reader"],spec["declared_charge_control"],spec["source_representation_contract"],coordinates=True)
 if result["representation_handoff"]["status"]!="SOURCE_REPRESENTATION_PASS":raise ValueError("Native reader representation is not source-authorized")
 handoff_expected=dict(spec["declared_charge_control"])
 handoff_expected["bonds"]=[{"atoms":b["atoms"],"order":b["native_order"]} for b in result["reader"]["bonds"]]
 result["charge_control"]=control_declared_charges(molecule,handoff_expected)'''
    conversion = ' molecule=api.return_molecule_class(molecule,simple=False)'
    converted = conversion + r'''
 result["representation_conversion_inventory"]=native_inventory(molecule)
 result["representation_conversion"]=native_representation_check(result["representation_conversion_inventory"],spec["declared_charge_control"],spec["source_representation_contract"],coordinates=True,charges=True)
 result["representation_conversion"]["checks"]["exact_native_conversion"]=result["representation_conversion_inventory"]==result["charge_control"]["after"]
 if not all(result["representation_conversion"]["checks"].values()):result["representation_conversion"]["status"]="BLOCKED"
 if result["representation_conversion"]["status"]!="SOURCE_REPRESENTATION_PASS":raise ValueError("Native class conversion changed the qualified source state")'''
    finish = " result['builder'].update(status='COMPLETED',after=native_inventory(output),after_format=output.GetOriginalFormat())"
    finished = r''' result["representation_finished_inventory"]=native_inventory(output)
 result["representation_finished"]=native_representation_check(result["representation_finished_inventory"],spec["declared_charge_control"],spec["source_representation_contract"],charges=True)
 if result["representation_finished"]["status"]!="SOURCE_REPRESENTATION_PASS":raise ValueError("Finished native inventory changed source chemistry")
''' + finish
    for before, after in [(old,new),(conversion,converted),(finish,finished)]:
        if base.count(before)!=1:raise ValueError("Native generation worker insertion differs")
        base=base.replace(before,after)
    return getsource(native_representation_check)+"\n"+base


def _replay_charge_control(reader, expected):
    """Run the maintained pure charge rule on recorded scalar data, without SDK."""
    from types import SimpleNamespace
    from .cif_declared_charge_control import control_declared_charges
    class Molecule(list):
        def GetOriginalFormat(self):
            return reader["format"]
    class Bond(list):
        pass
    molecule=Molecule(SimpleNamespace(name=r["atom"],symbol=r["element"],charge=r["native_atom_charge"],
        chiral=r["native_chiral_marker"],volume_sign=r["native_volume_sign"],
        xyz=SimpleNamespace(**dict(zip("xyz",r["xyz"])))) for r in reader["atoms"])
    index={a.name:a for a in molecule};molecule.charge=reader["molecule_charge"];molecule.bonds=[]
    for row in reader["bonds"]:
        bond=Bond(index[n] for n in row["atoms"]);bond.order=row["native_order"];molecule.bonds.append(bond)
    adjusted={**expected,"bonds":[{"atoms":r["atoms"],"order":r["native_order"]} for r in reader["bonds"]]}
    return control_declared_charges(molecule,adjusted)


def generation_representation_validation(result, expected, contract):
    """Recompute stage checks, including failed conversion and absent final output."""
    checks = {}
    reader = native_representation_check(result.get("reader",{}),expected,contract,coordinates=True)
    checks["reader_evidence"] = reader == result.get("representation_handoff")
    checks["reader_authorized"] = reader["status"] == "SOURCE_REPRESENTATION_PASS"
    charge = result.get("charge_control",{})
    checks["charge_handoff"] = charge.get("status") == "DECLARED_CHARGE_CONTROL_PASS"
    if reader["status"] == "SOURCE_REPRESENTATION_PASS":
        try:
            checks["charge_evidence"] = charge == _replay_charge_control(result["reader"],expected)
        except (KeyError,TypeError,ValueError,AttributeError,IndexError):
            checks["charge_evidence"] = False
    if "representation_conversion_inventory" in result:
        conversion = native_representation_check(result["representation_conversion_inventory"],expected,contract,coordinates=True,charges=True)
        conversion["checks"]["exact_native_conversion"] = result["representation_conversion_inventory"] == charge.get("after")
        if not all(conversion["checks"].values()):conversion["status"]="BLOCKED"
        builder=result.get("builder",{})
        checks["conversion_evidence"] = (conversion == result.get("representation_conversion")
            and ("before" not in builder or (builder["before"] == result["representation_conversion_inventory"]
                 and builder.get("before_format") == result.get("reader",{}).get("format"))))
        checks["conversion_authorized"] = conversion["status"] == "SOURCE_REPRESENTATION_PASS"
    else:
        checks["conversion_authorized"] = False
    if "representation_finished_inventory" in result:
        finished = native_representation_check(result["representation_finished_inventory"],expected,contract,charges=True)
        builder=result.get("builder",{})
        checks["finished_evidence"] = (finished == result.get("representation_finished")
            and (builder.get("status") != "COMPLETED" or (builder.get("after") == result["representation_finished_inventory"]
                 and builder.get("after_format") == result.get("reader",{}).get("format"))))
        checks["finished_authorized"] = finished["status"] == "SOURCE_REPRESENTATION_PASS"
    else:
        checks["finished_inventory_not_claimed"] = "representation_finished" not in result and result.get("builder",{}).get("status") != "COMPLETED"
    return {"policy_id":CONTRACT_POLICY,"status":"SOURCE_REPRESENTATION_PASS" if all(checks.values()) else "BLOCKED",
            "checks":checks,"finished_inventory":"RECORDED" if "representation_finished_inventory" in result else "UNAVAILABLE",
            "candidate_qualification":"INDEPENDENT_REQUIRED","automatic_adoption":False}


def _expected(source,code,dialect):
    from .cif_stereochemistry_audit import _values,_graph,_coordinates
    values=_values(source,code);elements,bonds,charges,_=_graph(values);_,xyz=_coordinates(values,source=True)
    order={"SINGLE":1,"DOUBLE":2,"TRIPLE":3,"AROMATIC":1.5,"DELOCALIZED":1.5}
    return {"component":code,"dialect":dialect,"elements":elements,"coordinates":xyz,
            "charges":{n:int(q) for n,q in charges.items()},"bonds":[{"atoms":list(p),"order":order[o]} for p,o in bonds.items()]}


def read_representation_candidate(directory):
    """Replay a versioned standalone generation receipt; never load native code."""
    try:
        return _read_representation_candidate(Path(directory))
    except (OSError,KeyError,TypeError,AttributeError,IndexError,OverflowError) as exc:
        raise ValueError("Incomplete source representation evidence: "+str(exc)) from exc


def _read_representation_candidate(root):
    from .cif_source_candidate import WORKER,SOURCE_PATHS,native_object_reference,complete_candidate_stereo,candidate_generation_diagnostic
    from .cif_constructor_setup import native_setup_reference
    from .cif_generation import _ideal_seed,inspect_component_generation,_explicit_formal_charges,_help_option_definitions,_OPTION_ALIASES
    from .cif_stereochemistry_audit import audit_optimizer_log
    from .cif_postmr_cached_model import cached_preparation_replays
    from .cif_mixed_recovery import _safe
    if any(p.is_symlink() for p in [root,*root.parents,*root.rglob("*")]):raise ValueError("Unsafe candidate directory")
    load=lambda p:json.loads(p.read_text())
    report=load(root/"source_candidate_receipt.json")
    if (type(report.get("schema_version")) is not int or report["schema_version"]!=1
            or report.get("policy_id")!=POLICY_ID or report.get("bond_representation_policy")!=REPRESENTATION_POLICY
            or report.get("automatic_adoption") is not False or report.get("requires_cif_review") is not False
            or report.get("native_backend")!="EXPLICIT_NATIVE_CCTBX_PREPARATION; INSTALLED_OPT_DEFAULTS"
            or report.get("selection")!="PENDING_NATIVE_USABILITY; OUTPUTS_PRESERVED_FOR_AUTOMATIC_FALLBACK"
            or report.get("native_proxy_validation")!="NOT_RUN" or report.get("source_preserved") is not True
            or any(report.get(k)!="NOT_RUN" for k in ["absolute_cip_assignment","installed_phenix_edits","model_editing"])):
        raise ValueError("Unsupported source generation scope")
    def verify(ref):
        if ref.get("anchor")!="candidate_directory" or not _safe(ref.get("path")):raise ValueError("Unsafe candidate reference")
        p=root/ref["path"];data=p.read_bytes()
        if sha256(data).hexdigest()!=ref.get("sha256") or len(data)!=ref.get("size"):raise ValueError("Candidate artifact changed")
        return p
    refs=report["outputs"];names=[r["path"] for r in refs]
    if len(names)!=len(set(names)) or "source_candidate_receipt.json" in names:raise ValueError("Ambiguous output inventory")
    for ref in refs:verify(ref)
    omitted=report.get("excluded_serialized_outputs",[])
    for ref in omitted:
        if not _safe(ref.get("path")) or Path(ref["path"]).suffix not in {".pkl",".pickle"}:raise ValueError("Invalid serialized exclusion")
        if (root/ref["path"]).exists():verify(ref)
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p!=root/"source_candidate_receipt.json"}
    if actual-set(r["path"] for r in omitted)!=set(names):raise ValueError("Candidate file inventory differs")
    source=root/"source.cif";code=report["component"]
    contract=generation_representation_contract(source,code,REPRESENTATION_POLICY)
    if contract!=report["source_representation_contract"] or contract["source_sha256"]!=report["source_sha256"]:raise ValueError("Source representation contract differs")
    if (root/"candidate_worker.py").read_text()!=source_representation_worker(WORKER):raise ValueError("Candidate worker differs")
    if (root/"source_ideal.pdb").read_text()!=_ideal_seed(source,code)[0]:raise ValueError("Candidate source seed differs")
    rows=report["sources"]
    if len(rows)!=len(SOURCE_PATHS):raise ValueError("Incomplete native source pins")
    prefix=rows[0]["path"][:-len(SOURCE_PATHS[0])].rstrip("/")
    for name,row in zip(SOURCE_PATHS,rows):
        if row.get("anchor")!="phenix_installation" or not _safe(row.get("path")) or row["path"]!=prefix+"/"+name:raise ValueError("Native source anchor differs")
        snap={**row["snapshot"],"path":"api_sources/"+name+".txt","sha256":row["sha256"],"size":row["size"]}
        if row["snapshot"].get("path")!=snap["path"] or not row["path"].endswith("/"+name):raise ValueError("Source snapshot identity differs")
        verify(snap)
    builder=(root/"api_sources/elbow/command_line/builder.py.txt").read_bytes()
    if report["native_object_reference"]!=native_object_reference(builder) or report["native_setup_reference"]!=native_setup_reference(builder):raise ValueError("Native API reference differs")
    spec_path=root/"candidate_spec.json"
    if not spec_path.exists():
        if report["execution"]["status"]!="NOT_RUN" or report["candidate"] is not None or report["status"]!="FAILED" or not report.get("error"):raise ValueError("Unexplained missing native specification")
        if report["diagnostic"]!=candidate_generation_diagnostic(report):raise ValueError("Candidate diagnostic differs")
        return report
    spec=load(spec_path);expected=_expected(source,code,spec["declared_charge_control"]["dialect"])
    if expected["dialect"] not in {"CHEMICAL_COMPONENTS_CIF","MONOMER_LIBRARY_CIF"}:raise ValueError("Unknown source reader dialect")
    if spec["declared_charge_control"]!=json.loads(json.dumps(expected)) or spec["source_representation_contract"]!=contract:raise ValueError("Native handoff specification differs")
    definitions=_help_option_definitions((root/"elbow_help.log").read_text(errors="replace"));caps=report["generator_capabilities"]
    flags={k:next((v for v in aliases if definitions.get(v) is (k!="opt")),None) for k,aliases in _OPTION_ALIASES.items()}
    if None in flags.values() or caps["selected_aliases"]!=flags or caps["supported_option_definitions"]!=definitions or caps["status"]!="SUPPORTED":raise ValueError("Generator capability evidence differs")
    if (caps.get("returncode")!=0 or caps.get("phenix_version")!=report.get("phenix_version")
            or caps.get("definition_parser")!="exact-installed-help-option-definitions-v1"
            or verify(caps["help_output"])!=root/"elbow_help.log"):raise ValueError("Generator help binding differs")
    step=next((v for v in ["--opt_steps","--opt-steps"] if definitions.get(v) is True),None)
    count=report["single_block_steps"];timeout=report["execution"]["timeout_seconds"]
    if type(count) is not int or not 1<=count<=600 or type(timeout) not in (int,float) or not 0<timeout<=600 or step is None:raise ValueError("Invalid generation bounds")
    args=[f"{flags['id']}={code}",f"{flags['output']}=candidate",f"{flags['template']}=source_ideal.pdb",f"{flags['initial_geometry']}=source_ideal.pdb",
          f"{flags['add_hydrogens']}=False",f"{flags['source_state_preservation']}=low",f"{flags['chiral']}=retain",flags['opt'],f"{step}={count}"]
    prefix=rows[0]["path"][:-len(SOURCE_PATHS[0])].rstrip("/")
    # Absolute strings here are compared as historical provenance only.
    historical=Path(spec["installation_root"])
    wanted={"component":code,"library":str(historical/prefix),"installation_root":str(historical),"arguments":args,
            "sources":[{"installed":str(historical/r["path"]),"sha256":r["sha256"],"module":name[:-3].replace("/",".")} for name,r in zip(SOURCE_PATHS,rows)],
            "declared_charge_control":json.loads(json.dumps(expected)),"source_representation_contract":contract}
    if len(caps.get("command",[]))!=2 or caps["command"][1]!="--help" or not Path(caps["command"][0]).is_relative_to(historical):raise ValueError("Unselected historical help dispatcher")
    if spec!=wanted or report["arguments"]!=args:raise ValueError("Complete native specification differs")
    result=load(root/"candidate_result.json") if (root/"candidate_result.json").exists() else {}
    if result!=report.get("result",{}):raise ValueError("Native result differs")
    for name,snapshot,options in [("representation_handoff",result.get("reader"),{"coordinates":True}),
            ("representation_conversion",result.get("representation_conversion_inventory"),{"coordinates":True,"charges":True}),
            ("representation_finished",result.get("representation_finished_inventory"),{"charges":True})]:
        if name in result:
            actual=native_representation_check(snapshot,expected,contract,**options)
            if name=="representation_conversion":
                actual["checks"]["exact_native_conversion"]=snapshot==result.get("charge_control",{}).get("after")
                if not all(actual["checks"].values()):actual["status"]="BLOCKED"
            if actual!=result[name]:raise ValueError("Recorded representation stage differs")
    validation=generation_representation_validation(result,expected,contract)
    if validation!=report["representation_validation"]:raise ValueError("Generation representation validation differs")
    status="FAILED"
    if report["candidate"] is not None:
        candidate=verify(report["candidate"])
        if candidate!=root/"candidate.cif" or report["candidate_retained"] is not True:raise ValueError("Unexpected retained candidate")
        inspection=inspect_component_generation(source,candidate,code,bond_representation_policy=REPRESENTATION_POLICY)
        stereo=complete_candidate_stereo(source,candidate,code)
        a,b=inspection["source_assessment"]["components"],inspection["generated_assessment"]["components"]
        charge_ok=len(a)==len(b)==1 and bool(_explicit_formal_charges(a[0])) and _explicit_formal_charges(a[0])==_explicit_formal_charges(b[0])
        if not cached_preparation_replays(report["inspection"],inspection) or not cached_preparation_replays(report["finished_stereo"],stereo) or report["formal_charges_preserved"]!=charge_ok:raise ValueError("Candidate assessment differs")
        status="REJECTED" if inspection["status"]=="REJECTED" or not charge_ok or stereo["stereochemistry"]=="INVERTED" or validation["status"]!="SOURCE_REPRESENTATION_PASS" else "CANDIDATE_REVIEW"
    elif report["candidate_retained"] is not False or (root/"candidate.cif").exists():raise ValueError("Unexplained candidate output")
    trajectory=audit_optimizer_log((root/"candidate_worker.log").read_text(errors="replace"))
    stopping={"status":trajectory["stopping"],"convergence_claimed":False,"trajectory":trajectory}
    if report.get("error") or report["status"]!=status or report["stopping"]!=stopping or report["diagnostic"]!=candidate_generation_diagnostic(report):raise ValueError("Generation outcome differs")
    return report
