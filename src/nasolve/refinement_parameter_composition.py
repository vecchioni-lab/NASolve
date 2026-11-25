"""Compose only scoped parameter fields using native PHIL literal nodes.

The caller owns the original science policy, its input anchors and execution.
This function starts no process, reads no crystallographic file and changes no
checkpoint. Native parsing is lazy; chemical/phase admission and continuous
parameter observation remain separate. Qualified with Phenix 2.2.1-6174.
"""
from hashlib import sha256
import io
import json
import re

from .refinement_parameter_text import selection_text

POLICY_ID = 'source-literal-parameter-composition-v1'


def _source_text(policy, expected):
    if type(policy) is not bytes:
        raise ValueError('Require exact original policy bytes')
    if (not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None
            or sha256(policy).hexdigest() != expected):
        raise ValueError('Original parameter-policy checksum mismatch')
    try:
        text = policy.decode('ascii')
    except UnicodeError as exc:
        raise ValueError('Require ASCII native parameter policy') from exc
    if '$' in text or re.search(r'(?:^|[;{}\n])\s*include\s', text):
        raise ValueError('Parameter composition requires self-contained literals, without includes or variables')
    if re.search(r'(?:^|[;{}\n])\s*\.[A-Za-z_]', text):
        raise ValueError('Parameter input must not redefine PHIL attributes')
    return text


def _definitions(node):
    for child in node.objects:
        if child.is_disabled:
            raise ValueError('Disabled parameter definitions need a separate policy')
        if child.is_definition:
            yield child
        else:
            yield from _definitions(child)


def _literal_signature(tree, owned):
    return [(item.full_path(), [word.value for word in item.words])
            for item in _definitions(tree) if item.full_path() not in owned]


def compose_parameters(policy, *, expected_policy_sha256, scope, source):
    """Return new PHIL bytes and a small literal-preservation receipt.

    Replace all occurrences of exactly eight XYZ/B/protection fields. Original
    target, phases, fixed scattering values, reflection choices, restraints and
    other settings stay with the supplied policy. Comments/whitespace may change;
    non-owned literal values and their effective native definitions must not.
    The supplied policy still requires independent scientific/input admission.
    Relative paths retain their original meaning only in its declared context.
    """
    text = _source_text(policy, expected_policy_sha256)
    selected = selection_text(scope, source)
    from iotbx import phil
    from iotbx.cli_parser import CCTBXParser
    from phenix.programs.phenix_refine import Program

    parser = CCTBXParser(program_class=Program, logger=io.StringIO())
    master = parser.master_phil
    master.adopt_scope(parser.data_manager.master_phil)
    original = phil.parse(text, process_includes=False)
    strategy = ['individual_sites']
    if selected.real_space:
        strategy.append('individual_sites_real_space')
    strategy.append('group_adp')
    fields = {
        'refinement.refine.strategy': strategy,
        'refinement.refine.sites.individual': [selected.xyz],
        'refinement.refine.adp.group': list(selected.groups),
        'refinement.refine.adp.group_adp_refinement_mode': 'group_selection',
        'refinement.main.apply_overall_isotropic_scale_to_adp': False,
        'refinement.main.find_and_add_hydrogens': False,
        'refinement.bulk_solvent_and_scale.apply_back_trace': False,
        'refinement.pdb_interpretation.sort_atoms': False,
    }
    owned = set(fields)
    # Validate original input before filtering, so unknown or disabled fields
    # cannot disappear merely because a similarly named replacement is valid.
    list(_definitions(original))

    def fetch(tree):
        effective, unused = master.fetch(source=tree, track_unused_definitions=True)
        if unused:
            raise ValueError('Original/composed policy has unused native definitions')
        return effective

    before = fetch(original)
    removed = []

    def retain(node):
        children = []
        for child in node.objects:
            if child.is_definition:
                if child.full_path() in owned:
                    removed.append(child.full_path())
                else:
                    children.append(child)
            else:
                children.append(retain(child))
        return node.customized_copy(objects=children)

    retained = retain(original)
    additions = []
    for path, value in fields.items():
        if path.endswith('.strategy'):
            additions.append(path + ' = ' + ' '.join('*' + name for name in value))
        elif isinstance(value, list):
            additions.extend(path + ' = ' + json.dumps(item) for item in value)
        else:
            additions.append(path + ' = ' + (str(value) if type(value) is bool else json.dumps(value)))
    updates = phil.parse('\n'.join(additions), process_includes=False)
    combined = retained.customized_copy(objects=retained.objects + updates.objects)
    # as_str on parsed literal nodes preserves float tokens. Never call
    # master.format(python_object=...) here: native floats use ten digits there.
    result = combined.as_str().encode('ascii')
    reparsed = phil.parse(result.decode('ascii'), process_includes=False)
    after = fetch(reparsed)
    literal_before = _literal_signature(original, owned)
    if (literal_before != _literal_signature(reparsed, owned)
            or _literal_signature(before, owned) != _literal_signature(after, owned)):
        raise ValueError('Composition changed non-owned scientific literals or effective definitions')
    actual = after.extract()
    for path, expected in fields.items():
        value = actual
        for part in path.split('.'):
            value = getattr(value, part)
        if value != expected:
            raise ValueError('Composed native field differs from declared parameter scope: ' + path)
    return result, dict(schema_version=1, policy_id=POLICY_ID,
        original_policy_sha256=expected_policy_sha256, source_model_sha256=selected.source_sha256,
        scope_sha256=selected.scope_sha256, result_sha256=sha256(result).hexdigest(),
        owned_fields=len(fields), removed_definitions=len(removed),
        non_owned_literals_unchanged=True,
        non_owned_literals_sha256=sha256(json.dumps(literal_before, separators=(',', ':')).encode()).hexdigest())
