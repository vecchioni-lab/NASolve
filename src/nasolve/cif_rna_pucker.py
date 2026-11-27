"""Explain an observed Phenix RNA pucker adjustment without changing its qualification."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .campaign_records import path_in
from .cif_candidate_qualification import inspect_candidate_qualification_processes
from .cif_candidate_qualification_execution import _inputs, _inventory, _owned_native_capture, _ref
from .cif_candidate_usability import _check_native_targets, covalent_proxy_signature, qualify_candidate_native
from .cif_dictionary_sites import _need, _read, _safe
from .cif_dictionary_store import _digest, _hash
from .cif_elbow_contract import MAX_SOURCE_BYTES
from .cif_doctor import _duplicate_tags, _number
from .cif_phenix_configuration import _library, _pin
from .cif_postmr_cache import verify_current_consumer
from .cif_stereochemistry_audit import _graph, _values
from .cif_terminal_qualification import _rows
from .ligand_profiles import _blocks

POLICY_ID = "observed-phenix-rna2p-targets-v1"
OBSERVED_POLICY_ID = "observed-phenix-rna-pucker-by-seed-v1"
PAIRED_USABILITY = "cif-isolated-native-and-literal-rna-usability-v1"
ETHER_PUCKER_PERMISSION = "source-ribose-methyl-ether-observed-puckers-v1"
ETHER_PAIRED_USABILITY = "cif-isolated-methyl-ether-native-and-literal-puckers-v1"
_TERMS = (
    ("bonds", "bond", 2, ("type", "value_dist", "value_dist_esd")),
    ("angles", "angle", 3, ("value_angle", "value_angle_esd")),
    ("torsions", "tor", 4, ("value_angle", "value_angle_esd", "period")),
)


def _term_key(row, names, category):
    end = tuple(row[n] for n in names)
    _need(all(v not in {"", ".", "?"} for v in end) and len(set(end))==len(end),
          "Ambiguous pucker target endpoints")
    return end if category=="tor" else min(end, end[::-1])


def _valid_target(field, raw, category):
    if field=="type":
        return raw=="coval"
    v=_number(raw)
    if v is None:
        return False
    if field=="period":
        return v.is_integer() and v>0
    if field=="value_angle":
        return category=="tor" or 0<v<180
    return v>0


def project_pucker_targets(values, table, *, modifier="rna2p"):
    """Apply only the selected literal change rules in memory, preserving source rows."""
    _need(modifier in ("rna2p", "rna3p") and table.get("data_") == "mod_" + modifier,
          "Unsupported pucker modification block")
    result=deepcopy(values)
    counts={}
    allowed={"data_"}
    for display, category, size, fields in _TERMS:
        section="_chem_mod_"+category
        comp="_chem_comp_"+category
        names=tuple("atom_id_"+str(i) for i in range(1,size+1))
        columns={"function","mod_id",*names,*("new_"+f for f in fields)}
        if category=="tor":
            columns.add("id")
        allowed.update(section+"."+f for f in columns)
        rules={}
        for row in _rows(table,section):
            _need(set(row)==columns and row["mod_id"]==modifier and row["function"]=="change",
                  "Unsupported pucker modification fields or operation")
            key=_term_key(row,names,category)
            _need(key not in rules,"Duplicate pucker modification endpoints")
            _need(all(_valid_target(f,row["new_"+f],category) for f in fields),"Invalid pucker target")
            rules[key]=row
        _need(bool(rules),"Missing pucker modification category")
        counts[display]=0
        for index, original in enumerate(_rows(values,comp)):
            rule=rules.get(_term_key(original,names,category))
            if rule is None:
                continue
            if category=="bond":
                orders={original[k].upper() for k in ("type","value_order") if k in original}
                _need(orders and orders<={"SING","SINGLE"},"Pucker change requires a source single bond")
                if "value_order" in original:
                    result[comp+".value_order"][index]="coval"
            for field in fields:
                _need(comp+"."+field in result, "Pucker change has no corresponding numerical field")
                result[comp+"."+field][index]=rule["new_"+field]
            counts[display]+=1
    _need(set(table)==allowed, "Unsupported pucker modification category or field")
    return result,counts


class ArchivedPuckerTableUnavailable(ValueError):
    """The older two-directory comparison needs its original numerical table."""


def _table_resource(modifier):
    _need(modifier in ("rna2p", "rna3p"), "Unsupported Phenix sugar pucker")
    return f"chem_data/geostd/rna_dna/mod_{modifier}.cif"


def installed_pucker_table(installation_root, *, modifier="rna2p"):
    """Identify the table within the same Phenix installation selected for refinement."""
    root=Path(installation_root).resolve(strict=True)
    table=_library(root)/_table_resource(modifier)
    return table, _pin(table,root,source=True)


def available_pucker_pin(installation_root):
    root=Path(installation_root).resolve(strict=True)
    path=_library(root)/_table_resource("rna2p")
    return _pin(path,root,source=True) if path.is_file() else None


def validate_table_pin(pin, *, modifier="rna2p"):
    _need(isinstance(pin,dict) and set(pin)=={"anchor","path","size","sha256"}
          and pin["anchor"]=="phenix_installation" and _safe(pin["path"])
          and pin["path"].endswith("/site-packages/"+_table_resource(modifier))
          and type(pin["size"]) is int and 0<pin["size"]<=MAX_SOURCE_BYTES and _hash(pin["sha256"]),
          "Require a pinned Phenix RNA pucker table")


def observed_ether_permission(permission):
    return isinstance(permission, dict) and permission.get("policy_id") == ETHER_PUCKER_PERMISSION


def permitted_pucker_tables(permission):
    """Validate the original single table or the explicit two-table methyl-ether recipe."""
    if not observed_ether_permission(permission):
        validate_table_pin(permission)
        return {"rna2p": permission}
    pins = permission.get("tables")
    _need(set(permission) == {"policy_id", "tables"} and isinstance(pins, dict)
          and set(pins) == {"rna2p", "rna3p"}, "Require both identified Phenix pucker tables")
    for modifier, pin in pins.items():
        validate_table_pin(pin, modifier=modifier)
    return pins


def verify_installed_pucker_permission(root, permission):
    for modifier, pin in permitted_pucker_tables(permission).items():
        selected = installed_pucker_table(root) if modifier == "rna2p" else installed_pucker_table(root, modifier=modifier)
        _need(selected[1] == pin, "Selected Phenix pucker table differs from the frozen request")


def literal_tables_match(mode, permission):
    """A control may freeze only tables actually observed and allowed by this request."""
    if not isinstance(mode, dict):
        return False
    allowed = permitted_pucker_tables(permission)
    if set(mode) == {"default_review_sha256", "table"}:
        return mode["table"] == allowed["rna2p"]
    observed = mode.get("tables")
    return (observed_ether_permission(permission) and set(mode) == {"default_review_sha256", "tables"}
            and isinstance(observed, dict) and bool(observed) and observed.keys() <= allowed.keys()
            and all(pin == allowed[m] for m, pin in observed.items()))


def table_bytes(path,pin, *, modifier="rna2p"):
    validate_table_pin(pin, modifier=modifier)
    _need(Path(path).stat().st_size==pin["size"],"RNA pucker table size differs")
    data=_read(path)
    _need(len(data)==pin["size"] and sha256(data).hexdigest()==pin["sha256"],"RNA pucker table checksum differs")
    return data


def bound_pucker_file(reference, root=None, *, site_copy=False):
    """Open one declared table, enforcing its relative layout for frozen inputs."""
    _need(isinstance(reference,dict) and set(reference)=={"path","pin"}, "Invalid RNA pucker reference")
    pin=reference["pin"]
    validate_table_pin(pin)
    if root is None:
        _need(isinstance(reference["path"],(str,Path)), "Invalid selected RNA table path")
        path=Path(reference["path"])
    else:
        name="inputs/furanose/rna2p.cif" if site_copy else "furanose/"+pin["sha256"]+".cif"
        _need(reference["path"]==name, "Invalid frozen RNA table reference")
        path=Path(root)/name
    return path,table_bytes(path,pin),pin


def _pucker_block(path,pin, *, modifier="rna2p"):
    data=table_bytes(path,pin,modifier=modifier)
    _need(not _duplicate_tags(data.decode("utf-8")),"Duplicate pucker template tags")
    blocks=_blocks(path)
    _need(len(blocks)==1 and table_bytes(path,pin,modifier=modifier)==data,"Ambiguous or changed pucker template")
    return blocks[0].values


def linked_pucker_expectations(prepared,native):
    """Use the paired table only at a linked site that actually received both modifiers."""
    from .cif_linked_preparation import component_values
    tables=prepared.get("rna_pucker_tables",{})
    if not tables:
        return {}
    plans={p["site"]:p for p in prepared["preparation"]["sites"]}
    observed={r["site"]:r.get("chem_mod_ids") for r in native["monomer_mappings"]["rows"]}
    output={}
    for site,(path,pin) in tables.items():
        modifier=plans[site].get("modification_id")
        if not modifier or observed.get(site)!={"status":"RECORDED","ids":[modifier,"rna2p"]}:
            continue
        projection,code=prepared["projections"][site]
        values,counts=project_pucker_targets(component_values(projection,code),_pucker_block(path,pin))
        _need(all(counts.values()),"Linked RNA table has no corresponding targets in a required category")
        output[site]={"values":values,"matched_rows":counts,"table_sha256":pin["sha256"]}
    return output


def _review_observed(root, table_for):
    """Compare each stopped native job with the numerical table that job actually selected."""
    root = Path(root).expanduser().resolve(strict=True)
    protocol, paths, models, phil = _inputs(root)
    _need("literal_rna" not in protocol, "Require the original default native qualification")
    state = inspect_candidate_qualification_processes(root)
    _need(state["state"] == "STOPPED" and set(state["phases"]) == {"native-000", "native-001"},
          "Require a stopped, complete pair of original native jobs")
    original_inventory = _inventory(root)
    code = protocol["component"]
    values = _values(paths[1], code)
    options = {"bond_representation_policy": protocol["bond_representation_policy"]}
    tables, targets, counts = {}, {}, {}
    seeds, modifiers, signatures = [], [], []
    for index, model in enumerate(models):
        job = state["phases"][f"native-{index:03d}"]["job"]
        receipt = path_in(root, job["cwd"]["path"] + "/native_receipt.json")
        ref = _ref(receipt, root)
        native = _owned_native_capture(root, ref, index, protocol, model, paths[1], phil, state)
        mappings = native.get("monomer_mappings", {}).get("rows", [])
        observed = mappings[0].get("chem_mod_ids") if len(mappings) == 1 else None
        modifier = next((m for m in ("rna2p", "rna3p")
                         if observed == {"ids": [m], "status": "RECORDED"}), None)
        _need(modifier is not None, "Require one recorded native rna2p or rna3p adjustment per seed")
        if modifier not in tables:
            path, pin = tables[modifier] = table_for(modifier)
            block = _pucker_block(path, pin, modifier=modifier)
            targets[modifier], counts[modifier] = project_pucker_targets(values, block, modifier=modifier)
        raw = qualify_candidate_native(*paths, model, code, native, **options)
        explained = _check_native_targets(*paths, model, code, native, projected=targets[modifier], **options)
        signatures.append(covalent_proxy_signature(native))
        modifiers.append(modifier)
        seeds.append({"seed": model.stem, "native_receipt": ref,
                      "literal_checks_failed": [k for k, v in raw["checks"].items() if not v],
                      "adjusted_checks_failed": [k for k, v in explained["checks"].items() if not v]})
    for modifier, (path, pin) in tables.items():
        table_bytes(path, pin, modifier=modifier)
    _need(_inventory(root) == original_inventory, "Qualification inputs changed during pucker review")
    same = signatures[0] == signatures[1]
    explained = (all(all(c.values()) for c in counts.values())
                 and all(s["literal_checks_failed"] and not s["adjusted_checks_failed"] for s in seeds))
    summary = dict(component=code, phenix_version=protocol["consumer"]["version"], source=_ref(paths[0], root),
                   candidate=_ref(paths[1], root), seeds=seeds, same_covalent_proxies=same,
                   scope="ISOLATED_COMPONENT_ONLY", qualification_unchanged=True, automatic_adoption=False)
    if set(tables) == {"rna2p"}:
        # This exact result is part of older stored qualification fingerprints.
        return dict(summary, policy_id=POLICY_ID, modifier="rna2p", table=tables["rna2p"][1],
                    matched_rows=counts["rna2p"], status="ADJUSTED_TARGETS_EXPLAINED" if same and explained else "REVIEW")
    for seed, modifier in zip(seeds, modifiers):
        seed.update(modifier=modifier, matched_rows=counts[modifier])
    explained = explained and (len(tables) > 1 or same)
    return dict(summary, policy_id=OBSERVED_POLICY_ID,
                tables={m: p for m, (_, p) in tables.items()}, status="SEED_TARGETS_EXPLAINED" if explained else "REVIEW")


def _review_default(root, template, pin):
    """Reproduce the original two-seed rna2p qualification from its one frozen table."""
    def frozen(modifier):
        _need(modifier == "rna2p", "Frozen RNA qualification requires exactly rna2p in both seeds")
        return template, pin
    return _review_observed(root, frozen)


def review_pucker_adjustment(directory, installation, *, exact_rna2p=False):
    """Read the observed sugar state in each seed against the identified Phenix installation."""
    root = Path(directory).expanduser().resolve(strict=True)
    protocol, _, _, _ = _inputs(root)
    ready = installation.executables["phenix.ready_set"]
    verify_current_consumer(installation, ready, protocol["consumer"])
    def installed(modifier):
        if modifier == "rna2p":
            return installed_pucker_table(installation.root)
        return installed_pucker_table(installation.root, modifier=modifier)
    result = _review_default(root, *installed("rna2p")) if exact_rna2p else _review_observed(root, installed)
    pins = result["tables"] if "tables" in result else {"rna2p": result["table"]}
    _need(all(installed(m)[1] == pin for m, pin in pins.items()), "Installed pucker table changed")
    verify_current_consumer(installation, ready, protocol["consumer"])
    return result


def _default_basis(directory, installation):
    review = review_pucker_adjustment(directory, installation, exact_rna2p=True)
    _need(review["status"] == "ADJUSTED_TARGETS_EXPLAINED", "Original Phenix pucker change is unexplained")
    return review, _digest(review)


def _separate_roots(default_job, literal_job):
    root=Path(default_job).expanduser().resolve(strict=True)
    literal=Path(literal_job).expanduser().absolute()
    _need(not literal.is_symlink() and not literal.resolve().is_relative_to(root)
          and not root.is_relative_to(literal.resolve()),"Require separate original and literal qualification roots")
    return root,literal


def verify_literal_pucker(default_job, literal_job, installation, *, include_observed_states=False, _attempt_identity=None, _remaining_seconds=None):
    """Check the same isolated component with only the native pucker adjustment disabled."""
    from .cif_candidate_qualification_execution import execute_candidate_qualification
    root,literal=_separate_roots(default_job,literal_job)
    _need(not literal.exists(),"Require a fresh literal qualification directory")
    if include_observed_states:
        review = review_pucker_adjustment(root, installation)
        _need(review["status"] in {"ADJUSTED_TARGETS_EXPLAINED","SEED_TARGETS_EXPLAINED"},
              "Original Phenix pucker change is unexplained")
        basis = _digest(review)
    else:
        review, basis = _default_basis(root, installation)
    if "tables" in review:
        tables = {m:installed_pucker_table(installation.root, modifier=m) for m in review["tables"]}
        _need({m:pin for m, (_,pin) in tables.items()} == review["tables"],
              "Selected Phenix tables differ from the observed sugar states")
        options = {"_literal_rna_tables":tables}
    else:
        table, pin = installed_pucker_table(installation.root)
        _need(pin == review["table"], "Selected RNA table differs from the original pucker review")
        options = {"_literal_rna_table":(table,pin)}
    p,paths,_,_=_inputs(root)
    execute_candidate_qualification(*paths,p["component"],p["consumer"],installation,literal,
        native_timeout_seconds=p["native_timeout_seconds"],total_timeout_seconds=p["total_timeout_seconds"],
        bond_representation_policy=p["bond_representation_policy"],_literal_rna_basis=basis,
        _attempt_identity=_attempt_identity,_remaining_seconds=_remaining_seconds,**options)
    return read_literal_pucker(root,literal,installation)


def read_literal_pucker(default_job, literal_job, installation=None):
    """Reopen the four native reads. Older pairs require their selected Phenix installation."""
    return _read_pair(default_job,literal_job,installation)[0]


def _read_pair(default_job,literal_job,installation=None):
    root,literal=_separate_roots(default_job,literal_job)
    lp,_,_,_=_inputs(literal)
    basis = lp.get("literal_rna", {})
    pin = basis.get("table")
    if "tables" in basis:
        pins = basis["tables"]
        if installation is not None:
            verify_current_consumer(installation,installation.executables["phenix.ready_set"],lp["consumer"])
            _need(all(installed_pucker_table(installation.root,modifier=m)[1] == v for m,v in pins.items()),
                  "Current Phenix sugar tables differ from the recorded ones")
        def selected(modifier):
            _need(modifier in pins, "Observed sugar state has no frozen table")
            return literal/"inputs"/(modifier+".cif"), pins[modifier]
        review = _review_observed(root, selected)
        _need(review.get("tables") == pins, "Frozen tables differ from the states recorded in the two native jobs")
    elif pin is None:
        if installation is None:
            raise ArchivedPuckerTableUnavailable("This earlier qualification requires the recorded Phenix installation")
        review,_=_default_basis(root,installation)
    else:
        if installation is not None:
            verify_current_consumer(installation,installation.executables["phenix.ready_set"],lp["consumer"])
            _need(installed_pucker_table(installation.root)[1]==pin,"Current native pucker table differs")
        review=_review_default(root,literal/"inputs/rna2p.cif",pin)
    return _paired_reads(root,literal,review)


def _paired_reads(root,literal,review):
    from .cif_candidate_qualification_execution import LITERAL_USABILITY, REPORT, read_candidate_qualification
    by_seed = review.get("policy_id") == OBSERVED_POLICY_ID
    required = "SEED_TARGETS_EXPLAINED" if by_seed else "ADJUSTED_TARGETS_EXPLAINED"
    _need(review["status"] == required, "Original Phenix pucker change is unexplained")
    basis=_digest(review)
    p,paths,_,_=_inputs(root)
    lp,lpaths,lmodels,_=_inputs(literal)
    strict=read_candidate_qualification(literal)
    _need(lp.get("literal_rna",{}).get("default_review_sha256")==basis
          and all(lp[k]==p[k] for k in ("component","consumer","bond_representation_policy","seeds",
                                       "native_timeout_seconds","total_timeout_seconds"))
          and all(a.read_bytes()==b.read_bytes() for a,b in zip(paths,lpaths)),
          "Literal read belongs to another source, candidate, consumer or original pucker review")
    _need(strict["same_covalent_proxies"] and len(strict["seed_qualifications"])==2 and
          all(q["policy_id"]==LITERAL_USABILITY and q["native_usable"] and
              q["checks"]["no_native_pucker_overlay"] for q in strict["seed_qualifications"]),
          "Both literal coordinate seeds must independently satisfy the original chemistry")
    summary={"schema_version":1,
            "policy_id":"paired-isolated-rna-pucker-by-seed-v1" if by_seed else "paired-isolated-rna-pucker-v1",
            "status":"LITERAL_AND_SEED_TARGETS_VERIFIED" if by_seed else "LITERAL_AND_NATIVE_TARGETS_VERIFIED","component":p["component"],
            "default_review":review,"default_review_sha256":basis,"literal_report":_ref(literal/REPORT,literal),
            "literal_seeds":[s.stem for s in lmodels],"source_and_candidate_identical_across_jobs":True,
            "scope":"ISOLATED_COMPONENT_ONLY","linked_context":"NOT_RUN","automatic_adoption":False}
    return summary,strict


def require_pucker_source(values, permission):
    """Require the declared RNA and sugar chemistry authorized by this recipe."""
    from .postmr_restoration import ribose_hydroxyl, ribose_methyl_ether
    _need([" ".join(t.upper().split()) for t in values.get("_chem_comp.type", ())] == ["RNA LINKING"],
          "Paired RNA qualification requires source-declared linking RNA")
    graph = _graph(values)
    if observed_ether_permission(permission):
        return ribose_methyl_ether(graph)
    ribose_hydroxyl(graph)
    return None


def paired_acquisition_qualification(default,literal,pin):
    """Build the isolated component result from all four underlying native jobs."""
    review,strict=_read_pair(default,literal)
    p,paths,_,_=_inputs(Path(literal))
    require_pucker_source(_values(paths[0],p["component"]), pin)
    if observed_ether_permission(pin):
        policy = ETHER_PAIRED_USABILITY
    else:
        _need(review["policy_id"] == "paired-isolated-rna-pucker-v1",
              "This acquisition requires the same authorized rna2p table in both coordinate seeds")
        policy = PAIRED_USABILITY
    _need(literal_tables_match(p.get("literal_rna"), pin), "Paired native readings used another RNA table")
    q=dict(strict["qualification"],policy_id=policy,paired_rna={
        "default":review["default_review"],"literal_report":review["literal_report"],
        "literal_seeds":[{"seed":s,"native_receipt":r} for s,r in zip(review["literal_seeds"],strict["native_receipts"])],
        "consumer_sha256":_digest(p["consumer"])})
    if policy == ETHER_PAIRED_USABILITY:
        q["paired_rna"]["pucker_permission"] = deepcopy(pin)
    return q


def validate_paired_qualification(q,*,source_sha256,candidate_sha256,code,consumer=None,table=None):
    """Bind the compact snapshot to both seeds, both conditions and the numerical table."""
    pair=q.get("paired_rna")
    required = {"default", "literal_report", "literal_seeds", "consumer_sha256"}
    ether = q.get("policy_id") == ETHER_PAIRED_USABILITY
    _need(isinstance(pair, dict) and set(pair) == (required | {"pucker_permission"} if ether else required),
          "Require both independent RNA readouts")
    if ether:
        recorded_permission = pair["pucker_permission"]
        _need(observed_ether_permission(recorded_permission) and (table is None or table == recorded_permission),
              "Methyl-ether readout differs from the requested pucker permission")
        table = recorded_permission
    review=pair["default"]
    _need(isinstance(review,dict) and review.get("component")==code and review.get("scope")=="ISOLATED_COMPONENT_ONLY"
          and review.get("automatic_adoption") is False and _hash(pair["consumer_sha256"]),
          "Incomplete native RNA evidence or original basis")
    by_seed = review.get("policy_id") == OBSERVED_POLICY_ID
    if by_seed:
        recorded = review.get("tables")
        _need(ether
              and review.get("status") == "SEED_TARGETS_EXPLAINED" and isinstance(recorded, dict)
              and isinstance(review.get("seeds"), list) and all(isinstance(s, dict) for s in review["seeds"]),
              "Stored per-seed sugar result requires explicit methyl-ether permission")
        modifiers = [s.get("modifier") for s in review["seeds"]]
        _need(all(m in ("rna2p", "rna3p") for m in modifiers) and set(modifiers) == set(recorded)
              and type(review.get("same_covalent_proxies")) is bool
              and (len(recorded) == 2 or review["same_covalent_proxies"]),
              "Observed sugar states disagree with the recorded seeds or native terms")
        mode = {"default_review_sha256": _digest(review), "tables": recorded}
        counts = [s.get("matched_rows") for s in review["seeds"]]
    else:
        _need(review.get("policy_id")==POLICY_ID and review.get("status")=="ADJUSTED_TARGETS_EXPLAINED"
              and review.get("modifier")=="rna2p" and review.get("same_covalent_proxies") is True,
              "Incomplete single-table native RNA evidence")
        mode = {"default_review_sha256": _digest(review), "table": review.get("table")}
        counts = [review.get("matched_rows")]
    permission = review.get("table") if table is None else table
    _need(q.get("literal_rna") == mode and literal_tables_match(mode, permission),
          "Stored native RNA tables differ from the original readings or requested permission")
    _need(consumer is None or (_digest(consumer)==pair["consumer_sha256"] and consumer["version"]==review.get("phenix_version")),
          "Stored RNA evidence belongs to another native consumer")
    def reference(ref,path):
        return (isinstance(ref,dict) and set(ref)=={"anchor","path","sha256","size"} and
                ref["anchor"]=="qualification_directory" and ref["path"]==path and _hash(ref["sha256"])
                and type(ref["size"]) is int and ref["size"]>0)
    for label,digest in (("source",source_sha256),("candidate",candidate_sha256)):
        ref=review.get(label)
        _need(reference(ref,"inputs/"+label+"/"+label+".cif") and ref["sha256"]==digest,
              "Native RNA review used another component dictionary")
    _need(all(isinstance(c,dict) and set(c)=={"bonds","angles","torsions"}
              and all(type(n) is int and n>0 for n in c.values()) for c in counts),
          "Missing native RNA numerical changes")
    default,literal=review.get("seeds"),pair["literal_seeds"]
    _need(reference(pair["literal_report"],"qualification_execution.json"),"Require the sealed literal RNA readout")
    hashes=[]
    for records in (default,literal):
        _need(isinstance(records,list) and len(records)==2 and all(isinstance(r,dict) for r in records)
              and [r.get("seed") for r in records]==["source","candidate"],"Require both RNA coordinate seeds")
        for i,row in enumerate(records):
            ref=row.get("native_receipt")
            name=ref.get("path") if isinstance(ref,dict) else None
            _need(_safe(name) and len(name.split("/"))==4 and name.startswith(f"native/{i:03d}/")
                  and name.endswith("/native_receipt.json") and reference(ref,name),
                  "Incomplete native RNA coordinate-seed receipt")
            hashes.append(ref["sha256"])
    _need(len(set(hashes))==4 and all(isinstance(r.get("literal_checks_failed"),list) and r["literal_checks_failed"]
          and set(r["literal_checks_failed"])<={"exact_effective_definitions","effective_declared_bond_orders",
              "exact_active_bonds","exact_active_angles","exact_active_torsions"}
          and r.get("adjusted_checks_failed")==[] for r in default),
          "Unexplained native RNA difference or duplicate seed evidence")
