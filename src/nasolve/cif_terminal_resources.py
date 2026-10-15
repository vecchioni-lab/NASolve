"""Read installed terminal modifications and a canonical in-memory control.

No model is supplied or edited. These are numerical-source records for later
review, not a terminal recipe, candidate adoption or geometry qualification.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from math import isfinite
import os
from pathlib import Path
import re
import subprocess
from tempfile import mkdtemp
import time
from typing import Mapping, Sequence

from .cif_native_validation import _artifact, _sha, _stop

TERMINAL_RESOURCE_POLICY = 'cif-installed-terminal-resources-v2'

_WORKER = r'''import hashlib,json,sys,traceback
from pathlib import Path

spec=json.loads(Path(sys.argv[1]).read_text())
report={"schema_version":1,"policy_id":spec["policy_id"],"status":"FAILED",
        "modifications":{},"canonical_control":{},"api_sources":[],"source_files":[],
        "model_editing":"NOT_RUN","optimization":"NOT_RUN","automatic_adoption":False,
        "scientific_approval":"NOT_RUN"}
sources={}
class UnsupportedNativeAPI(RuntimeError): pass
def sha(data):return hashlib.sha256(data).hexdigest()
def source_info(obj):
    info=getattr(obj,"source_info",None)
    if isinstance(info,str) and info.startswith("file: "):
        path=Path(info[6:])
        if path.is_file():sources.setdefault(str(path),path.read_bytes())
    return info
def row(obj):
    if not callable(getattr(obj,"cif_keywords",None)):
        raise UnsupportedNativeAPI("Native CIF row has no cif_keywords interface")
    return {key:getattr(obj,key) for key in obj.cif_keywords()}
categories={"atoms":"atom_list","bonds":"bond_list","angles":"angle_list",
            "torsions":"tor_list","chirality":"chir_list","plane_atoms":"plane_atom_list"}
def lists(obj):
    result={}
    for name,field in categories.items():
        if not hasattr(obj,field):raise UnsupportedNativeAPI("Missing native category: "+field)
        result[name]=[row(value) for value in getattr(obj,field)]
    return result
def component(obj):
    result={"metadata":row(obj.chem_comp),"source_provenance":source_info(obj),**lists(obj)}
    result["classification"] = obj.get_classification() if callable(getattr(obj,"get_classification",None)) else None
    result["formal_charge_readback"] = "RECORDED" if result["atoms"] and all(
        value.get("charge") not in (None,"",".","?") for value in result["atoms"]) else "UNSUPPORTED"
    return result
try:
    from mmtbx.monomer_library import server,cif_types
    import iotbx.pdb
    for module in [server,cif_types,iotbx.pdb]:
        path=Path(module.__file__)
        report["api_sources"].append({"module":module.__name__,"historical_path":str(path),"sha256":sha(path.read_bytes())})
    library=server.server()
    for identifier in spec["modification_ids"]:
        obj=library.mod_mod_id_dict.get(identifier)
        if obj is None:raise UnsupportedNativeAPI("Missing requested terminal modification: "+identifier)
        report["modifications"][identifier]={"metadata":row(obj.chem_mod),
            "source_provenance":source_info(obj),**lists(obj)}
    method="get_comp_comp_id_and_atom_name_interpretation"
    resolver=getattr(library,method,None)
    if not callable(resolver):raise UnsupportedNativeAPI("Native canonical residue-name resolution API is unavailable")
    base,interpretation=resolver(residue_name=spec["canonical_code"],atom_names=[])
    if base is None:raise UnsupportedNativeAPI("Missing canonical monomer after native residue-name resolution: "+spec["canonical_code"])
    before=component(base)
    resolution={"method":method,"input_atom_names":[],
        "interpreted_residue_name":getattr(interpretation,"residue_name",None),
        "resolved_component_id":before["metadata"].get("id")}
    effective,ids=library.get_comp_comp_id_mod(base,tuple(spec["modification_ids"]))
    after=component(effective)
    if component(base)!=before:raise RuntimeError("Native modification mutated the canonical base object")
    if list(ids)!=spec["modification_ids"]:raise RuntimeError("Native applied modification identifiers differ")
    report["canonical_control"]={"code":spec["canonical_code"],"resolution":resolution,"base":before,"effective":after,
        "applied_modification_ids":list(ids),"base_preserved":True,"scope":"in-memory library control; no coordinate model"}
    report["status"]="REVIEW"
except UnsupportedNativeAPI as exc:
    report.update(status="UNSUPPORTED",error=str(exc))
except Exception as exc:
    report.update(status="FAILED",error=type(exc).__name__+": "+str(exc),traceback=traceback.format_exc())
for name,data in sorted(sources.items()):
    path=Path(name);preserved=path.is_file() and path.read_bytes()==data
    report["source_files"].append({"historical_path":name,"sha256":sha(data),"size":len(data),"preserved_after_capture":preserved})
    if not preserved:report.update(status="FAILED",error="Installed source changed after capture")
Path("native_resources.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
sys.exit(0 if report["status"]=="REVIEW" else 2)
'''


def inspect_terminal_resources(output_parent: Path, executable: Path, *,
        environment: Mapping[str, str], phenix_version: str,
        modification_ids: Sequence[str] = ('5*END',), canonical_code: str = 'DG',
        timeout_seconds: float = 120) -> dict:
    """Capture exact native row fields, values and source hashes in a fresh directory."""
    if not isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise ValueError('Native resource timeout must be finite and positive')
    ids=list(modification_ids)
    if not ids or len(ids)!=len(set(ids)) or any(not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9*_-]{1,32}',value) for value in ids):
        raise ValueError('Require distinct explicit native modification identifiers')
    if not re.fullmatch(r'[A-Za-z0-9]{1,8}',canonical_code) or not phenix_version:
        raise ValueError('Require a canonical component code and explicit Phenix version')
    executable=Path(executable).resolve();payload=executable.read_bytes()
    parent=Path(output_parent).resolve();parent.mkdir(parents=True,exist_ok=True)
    work=Path(mkdtemp(prefix='cif-terminal-resources-',dir=parent))
    spec={'policy_id':TERMINAL_RESOURCE_POLICY,'modification_ids':ids,'canonical_code':canonical_code}
    (work/'resource_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (work/'resource_worker.py').write_text(_WORKER)
    command=[str(executable),'resource_worker.py','resource_spec.json']
    clock=time.monotonic()
    receipt={'schema_version':1,'audit_kind':'cif_native_terminal_resource_inventory',
        'policy_id':TERMINAL_RESOURCE_POLICY,'status':'FAILED','native_directory':str(work),
        'command':command,'phenix_version':str(phenix_version),'executable_sha256':_sha(payload),
        'executable_provenance':str(executable),'native_resources':None,'automatic_adoption':False,
        'model_editing':'NOT_RUN','optimization':'NOT_RUN','refinement':'NOT_RUN','readyset_retry':'NOT_RUN',
        'scientific_approval':'NOT_RUN','execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds,
            'started_at':datetime.now(timezone.utc).isoformat()}}
    try:
        with (work/'native.log').open('xb') as log:
            process=subprocess.Popen(command,cwd=work,env={**environment,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:code=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(process);receipt['execution'].update(status='TIMED_OUT',returncode=process.returncode)
                receipt['error']='Owned native resource process group exceeded the requested timeout'
            except BaseException:
                _stop(process);raise
            else:
                receipt['execution'].update(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
                path=work/'native_resources.json'
                if not path.is_file() or path.is_symlink():raise ValueError('Missing exact native resource report')
                report=json.loads(path.read_text())
                if report.get('schema_version')!=1 or report.get('policy_id')!=TERMINAL_RESOURCE_POLICY or report.get('status') not in {'REVIEW','UNSUPPORTED','FAILED'}:
                    raise ValueError('Unsupported native resource report')
                receipt['native_resources']=report
                if code==0 and report['status']=='REVIEW':
                    if set(report.get('modifications',{}))!=set(ids) or report.get('canonical_control',{}).get('base_preserved') is not True:
                        raise ValueError('Incomplete native resource/control evidence')
                    receipt['status']='REVIEW'
                elif report['status']=='UNSUPPORTED':receipt['status']='UNSUPPORTED'
                else:receipt['error']=report.get('error','Native resource worker failed')
    except (OSError,ValueError) as exc:
        receipt.update(error=type(exc).__name__+': '+str(exc))
    receipt['execution'].update(finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(time.monotonic()-clock,6))
    receipt['outputs']=[_artifact(path,work) for path in sorted(work.rglob('*')) if path.is_file() and not path.is_symlink()]
    with (work/'resources_receipt.json').open('x') as handle:
        json.dump(receipt,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')
    return receipt
