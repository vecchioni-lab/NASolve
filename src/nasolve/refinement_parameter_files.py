"""Rebind declared DataManager Miller-array filenames without changing science.

The existing input/checkpoint owner must authenticate each mapping from its
recorded command and checksummed input references. This function reads no files,
starts no process and supplies no ancestry or complete executable child policy.
Command arguments, other file fields and target/phase admission remain separately
owned. Qualified with Phenix 2.2.1-6174.
"""
from hashlib import sha256
import io
import json
import re

from .refinement_parameter_composition import _source_text, _definitions, _literal_signature

_FILE = 'data_manager.miller_array.file'
POLICY_ID = 'literal-datamanager-file-rebinding-v1'


def rebind_miller_files(policy, *, expected_policy_sha256, bindings):
    """Return PHIL bytes and a receipt for exact caller-authenticated mappings.

    Each binding names an exact historical filename, its resolved declared file
    and the source checksum plus its declared portable reference. The caller verifies that checksum through existing
    input owners; this transformer does not open the file. Every Miller selector
    must have a mapping, and every supplied mapping must be used. Labels, ordering
    and all other literal/effective definitions remain unchanged. The resolved filename records execution spelling; the source reference owns
    operational provenance. Paths are never guessed by basename. This is not a general PHIL or command path relocator.
    """
    text = _source_text(policy, expected_policy_sha256)
    if not isinstance(bindings,list) or not bindings:
        raise ValueError('Require explicit declared file bindings')
    mapping = {}
    resolved = set()
    for row in bindings:
        if (not isinstance(row,dict) or set(row) != {'historical_file','resolved_file','sha256','source_reference'}
                or not isinstance(row['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',row['sha256'])):
            raise ValueError('Malformed declared file binding')
        ref=row['source_reference']
        if (not isinstance(ref,dict) or ref.get('anchor') not in ('run','dataset','repository')
                or ref.get('sha256')!=row['sha256'] or not isinstance(ref.get('relative_path'),str)
                or not ref['relative_path'] or ref['relative_path'].startswith('/')
                or '..' in ref['relative_path'].split('/')):
            raise ValueError('Require a declared portable source reference with the same checksum')
        for key in ('historical_file','resolved_file'):
            value=row[key]
            if (not isinstance(value,str) or not value.strip()
                    or any(c in value for c in '\n\r\x00$') or not value.isascii()):
                raise ValueError('Require literal ASCII file paths')
        old,new=row['historical_file'],row['resolved_file']
        if old in mapping or new in resolved:
            raise ValueError('File bindings must have unique historical and resolved identities')
        mapping[old]=new;resolved.add(new)

    from iotbx import phil
    from iotbx.cli_parser import CCTBXParser
    from phenix.programs.phenix_refine import Program
    parser=CCTBXParser(program_class=Program,logger=io.StringIO())
    master=parser.master_phil;master.adopt_scope(parser.data_manager.master_phil)
    original=phil.parse(text,process_includes=False)
    list(_definitions(original))
    def fetch(tree):
        effective,unused=master.fetch(source=tree,track_unused_definitions=True)
        if unused:raise ValueError('Policy has unused native definitions')
        return effective
    before=fetch(original);used=[]
    def rewrite(node):
        children=[]
        for child in node.objects:
            if child.is_definition and child.full_path()==_FILE:
                if len(child.words)!=1 or child.words[0].value not in mapping:
                    raise ValueError('Miller selector has no exact declared historical binding')
                old=child.words[0].value;used.append(old)
                children.append(phil.parse('file = '+json.dumps(mapping[old]),process_includes=False).objects[0])
            elif child.is_definition:children.append(child)
            else:children.append(rewrite(child))
        return node.customized_copy(objects=children)
    changed=rewrite(original)
    if set(used)!=set(mapping):raise ValueError('Declared file binding is unused by the policy')
    result=changed.as_str().encode('ascii');reparsed=phil.parse(result.decode('ascii'),process_includes=False)
    after=fetch(reparsed);owned={_FILE}
    if (_literal_signature(original,owned)!=_literal_signature(reparsed,owned)
            or _literal_signature(before,owned)!=_literal_signature(after,owned)):
        raise ValueError('File rebinding changed non-file scientific literals or effective definitions')
    actual=[item.words[0].value for item in _definitions(reparsed) if item.full_path()==_FILE]
    if actual!=[mapping[old] for old in used]:raise ValueError('Rebound file identities or order changed')
    # Freeze mapping values into the receipt; no references to mutable caller data.
    bound=json.loads(json.dumps(bindings,sort_keys=True,allow_nan=False))
    return result,dict(schema_version=1,policy_id=POLICY_ID,
        source_policy_sha256=expected_policy_sha256,result_sha256=sha256(result).hexdigest(),
        bindings=bound,rebound_definitions=len(used),non_file_literals_unchanged=True,
        scope='DataManager Miller-array selectors only; no command or other file rebinding')
