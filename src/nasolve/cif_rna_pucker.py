"""Explain an observed Phenix RNA pucker adjustment without changing its qualification."""
from copy import deepcopy
from pathlib import Path

from .campaign_records import path_in
from .cif_candidate_qualification import inspect_candidate_qualification_processes
from .cif_candidate_qualification_execution import _inputs, _inventory, _owned_native_capture, _ref
from .cif_candidate_usability import _check_native_targets, covalent_proxy_signature, qualify_candidate_native
from .cif_dictionary_sites import _need
from .cif_doctor import _duplicate_tags, _number
from .cif_phenix_configuration import _library, _pin
from .cif_postmr_cache import verify_current_consumer
from .cif_stereochemistry_audit import _values
from .cif_terminal_qualification import _rows
from .ligand_profiles import _blocks

POLICY_ID = "observed-phenix-rna2p-targets-v1"
_RESOURCE = "chem_data/geostd/rna_dna/mod_rna2p.cif"
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


def project_pucker_targets(values, table):
    """Apply only the selected literal change rules in memory, preserving source rows."""
    _need(table.get("data_")=="mod_rna2p", "Unsupported pucker modification block")
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
            _need(set(row)==columns and row["mod_id"]=="rna2p" and row["function"]=="change",
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


def review_pucker_adjustment(directory, installation):
    """Re-evaluate two stopped coordinate seeds against the currently selected native table."""
    root=Path(directory).expanduser().resolve(strict=True)
    protocol,paths,models,phil=_inputs(root)
    _need("literal_rna" not in protocol,"Require the original default native qualification")
    state=inspect_candidate_qualification_processes(root)
    _need(state["state"]=="STOPPED" and set(state["phases"])=={"native-000","native-001"},
          "Require a stopped, complete pair of original native jobs")
    original_inventory=_inventory(root)
    consumer=protocol["consumer"]
    verify_current_consumer(installation,installation.executables["phenix.ready_set"],consumer)
    library_root=Path(installation.root).resolve(strict=True)
    template=_library(library_root)/_RESOURCE
    pin=_pin(template,library_root,source=True)
    _need(not _duplicate_tags(template.read_text()),"Duplicate pucker template tags")
    blocks=_blocks(template)
    _need(len(blocks)==1,"Ambiguous pucker template")
    code=protocol["component"]
    projected,counts=project_pucker_targets(_values(paths[1],code),blocks[0].values)
    options={"bond_representation_policy":protocol["bond_representation_policy"]}
    seeds=[]
    signatures=[]
    for index,model in enumerate(models):
        job=state["phases"][f"native-{index:03d}"]["job"]
        receipt=path_in(root,job["cwd"]["path"]+"/native_receipt.json")
        ref=_ref(receipt,root)
        native=_owned_native_capture(root,ref,index,protocol,model,paths[1],phil,state)
        mappings=native.get("monomer_mappings",{}).get("rows",[])
        mods=mappings[0].get("chem_mod_ids") if len(mappings)==1 else None
        _need(mods=={"ids":["rna2p"],"status":"RECORDED"}, "Require exactly one recorded native rna2p adjustment")
        raw=qualify_candidate_native(*paths,model,code,native,**options)
        explained=_check_native_targets(*paths,model,code,native,projected=projected,**options)
        signatures.append(covalent_proxy_signature(native))
        seeds.append({"seed":model.stem,"native_receipt":ref,"literal_checks_failed":
                      [k for k,v in raw["checks"].items() if not v],
                      "adjusted_checks_failed":[k for k,v in explained["checks"].items() if not v]})
    same=signatures[0]==signatures[1]
    accounted=(all(counts.values()) and same and
               all(s["literal_checks_failed"] and not s["adjusted_checks_failed"] for s in seeds))
    _need(_inventory(root)==original_inventory and pin==_pin(template,library_root,source=True),
          "Qualification inputs or selected Phenix pucker table changed during review")
    verify_current_consumer(installation,installation.executables["phenix.ready_set"],consumer)
    return {"policy_id":POLICY_ID,"component":code,"phenix_version":consumer["version"],"modifier":"rna2p",
            "table":pin,"source":_ref(paths[0],root),"candidate":_ref(paths[1],root),
            "matched_rows":counts,"seeds":seeds,"same_covalent_proxies":same,
            "status":"ADJUSTED_TARGETS_EXPLAINED" if accounted else "REVIEW",
            "scope":"ISOLATED_COMPONENT_ONLY","qualification_unchanged":True,"automatic_adoption":False}


def _default_basis(directory, installation):
    from .cif_dictionary_store import _digest
    review=review_pucker_adjustment(directory,installation)
    _need(review["status"]=="ADJUSTED_TARGETS_EXPLAINED","Original Phenix pucker change is unexplained")
    return review,_digest(review)


def _separate_roots(default_job, literal_job):
    root=Path(default_job).expanduser().resolve(strict=True)
    literal=Path(literal_job).expanduser().absolute()
    _need(not literal.is_symlink() and not literal.resolve().is_relative_to(root)
          and not root.is_relative_to(literal.resolve()),"Require separate original and literal qualification roots")
    return root,literal


def verify_literal_pucker(default_job, literal_job, installation):
    """Check the same isolated component with only the native pucker adjustment disabled."""
    from .cif_candidate_qualification_execution import execute_candidate_qualification
    root,literal=_separate_roots(default_job,literal_job)
    _need(not literal.exists(),"Require a fresh literal qualification directory")
    _,basis=_default_basis(root,installation)
    p,paths,_,_=_inputs(root)
    execute_candidate_qualification(*paths,p["component"],p["consumer"],installation,literal,
        native_timeout_seconds=p["native_timeout_seconds"],total_timeout_seconds=p["total_timeout_seconds"],
        bond_representation_policy=p["bond_representation_policy"],_literal_rna_basis=basis)
    return read_literal_pucker(root,literal,installation)


def read_literal_pucker(default_job, literal_job, installation):
    """Recheck both independent directories and the selected native numerical table."""
    from .cif_candidate_qualification_execution import LITERAL_USABILITY, REPORT, read_candidate_qualification
    root,literal=_separate_roots(default_job,literal_job)
    review,basis=_default_basis(root,installation)
    p,paths,_,_=_inputs(root)
    lp,lpaths,lmodels,_=_inputs(literal)
    strict=read_candidate_qualification(literal)
    _need(lp.get("literal_rna")=={"default_review_sha256":basis}
          and all(lp[k]==p[k] for k in ("component","consumer","bond_representation_policy","seeds",
                                       "native_timeout_seconds","total_timeout_seconds"))
          and all(a.read_bytes()==b.read_bytes() for a,b in zip(paths,lpaths)),
          "Literal read belongs to another source, candidate, consumer or original pucker review")
    _need(strict["same_covalent_proxies"] and len(strict["seed_qualifications"])==2 and
          all(q["policy_id"]==LITERAL_USABILITY and q["native_usable"] and
              q["checks"]["no_native_pucker_overlay"] for q in strict["seed_qualifications"]),
          "Both literal coordinate seeds must independently satisfy the original chemistry")
    return {"schema_version":1,"policy_id":"paired-isolated-rna-pucker-v1",
            "status":"LITERAL_AND_NATIVE_TARGETS_VERIFIED","component":p["component"],
            "default_review":review,"default_review_sha256":basis,"literal_report":_ref(literal/REPORT,literal),
            "literal_seeds":[s.stem for s in lmodels],"source_and_candidate_identical_across_jobs":True,
            "scope":"ISOLATED_COMPONENT_ONLY","linked_context":"NOT_RUN","automatic_adoption":False}
