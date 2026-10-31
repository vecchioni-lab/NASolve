"""Explicit graph-bound neutral furanose reaction controls for native inspection.

Source chemistry, complete candidate numerics and native reaction conventions are
separate authorities. This adapter emits diagnostic inputs, not a linked or
isolated native qualification and not an automatic ReadySet replacement.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
import tempfile

from .cif_attachment_profiles import inspect_attachment_profile
from .cif_attachment_sites import _model, _object, _projection_values, inspect_attachment_site
from .cif_candidate_usability import reassess_complete_candidate
from .cif_fana_component import _digest, _load, _save
from .cif_linked_preparation import _prune, _render, _selection, atom_rows
from .cif_preparation_qualification import project_source_configurations
from .cif_stereochemistry_audit import _graph
from .ligand_profiles import _emit

POLICY_ID = 'cif-graph-furanose-native-reaction-v1'
# OC2 follows the native NA-STAND outgoing oxygen convention, but only after
# the source graph proves a neutral C-O-H port and an explicit O-P substitution.
# Its other blanket phosphate deletions are deliberately not imported here.
ENERGY_POLICY = 'cif-neutral-furanose-outgoing-oxygen-oc2-v1'
_PROFILES = {'unbridged-furanose-phosphate-v1', 'two-o-four-c-methylene-furanose-phosphate-v1'}
_INPUTS = {'source.cif', 'numerical.cif', 'Ligands.xlsx', 'model.pdb', 'contexts.json', 'selection.json'}
_OUTPUTS = {'base_dictionary.cif', 'site_modifications.cif', 'site_modifications.phil', 'preparation.json'}


def _derive(root):
    selection = _load(root/'selection.json'); _object(selection, ('code',))
    code = selection['code']
    if not isinstance(code, str) or not re.fullmatch('[A-Z0-9]{1,3}', code):
        raise ValueError('Require explicit PDB-compatible component identity')
    values = _projection_values(root/'numerical.cif', code)
    source = _projection_values(root/'source.cif', code)
    # Numerical generation may choose a native group independently. It must not
    # change the source's declared polymer classification to gain link support.
    classification = lambda v: [' '.join(x.upper().split()) for x in v.get('_chem_comp.type', [])]
    if classification(values) and classification(source) != classification(values):
        raise ValueError('Candidate changes the source polymer classification')
    metadata_changes = []
    if not classification(values) and classification(source):
        metadata_changes.append({'field': '_chem_comp.type', 'before': None,
                                 'after': source['_chem_comp.type'], 'authority': 'SOURCE'})
        values['_chem_comp.type'] = list(source['_chem_comp.type'])
    assessment = reassess_complete_candidate(root/'source.cif', root/'numerical.cif', code)
    stereo = assessment['finished_stereo']
    if (assessment['candidate_status'] != 'CANDIDATE_REVIEW' or not stereo['terms']
            or any(t['handedness'] != 'PRESERVED' for t in stereo['terms'])):
        raise ValueError('Require complete source-preserving numerics and all source configurations')
    profile = inspect_attachment_profile(root/'source.cif', code, workbook=root/'Ligands.xlsx')
    if profile['topology_status'] != 'MATCH' or profile['matched_profile'] not in _PROFILES:
        raise ValueError('Require a uniquely supported furanose source graph')
    roles = profile['bindings']; charges = _graph(source)[2]
    contexts = _load(root/'contexts.json'); model = _model((root/'model.pdb').read_bytes())
    if not isinstance(contexts, list) or not contexts or len(contexts) > 256:
        raise ValueError('Require one to 256 explicit site contexts')
    for c in contexts:_object(c, ('schema_version', 'site', 'ports'))
    sites = [c['site'] for c in contexts]
    if (any(not isinstance(s, str) for s in sites) or len(set(sites)) != len(sites)
            or set(sites) != {s for s, row in model.items() if row['component'] == code}):
        raise ValueError('Contexts must cover every model site with this component exactly once')
    plans = []; blocks = []; phil = []
    with tempfile.TemporaryDirectory(prefix='nasolve-reaction-sites-') as temporary:
        context_file = Path(temporary)/'context.json'
        for context in sorted(contexts, key=lambda c: c['site']):
            # This existing source authority owns protonation, leaving groups,
            # model identity, partner elements and identity-symmetry restrictions.
            context_file.write_text(json.dumps(context))
            plan = inspect_attachment_site(root/'source.cif', code, workbook=root/'Ligands.xlsx',
                                           model=root/'model.pdb', context=context_file)
            if plan['plan_status'] != 'PROPOSED':
                raise ValueError('Source authority cannot qualify the declared neutral port operation')
            projection = plan['permitted_source_projection']; removed = set(projection['deleted_atoms'])
            outgoing = context['ports']['alcohol']['state'] == 'linked'
            incoming = context['ports']['phosphate']['state'] == 'linked'
            if incoming and charges[roles['phosphate']] != 0:
                raise ValueError('Charged phosphate centre needs separate native-state authority')
            derivative = _prune(values, removed, outgoing=False)
            changes = []; rows = []
            identifier = 'NSFR'+sha256(json.dumps({'code': code, 'context': context},sort_keys=True).encode()).hexdigest()[:12]
            for atom in sorted(removed):rows.append([identifier,'delete',atom,'.','.','.','.'])
            if outgoing:
                atom = roles['three_o']; index = derivative['_chem_comp_atom.atom_id'].index(atom)
                before = derivative['_chem_comp_atom.type_energy'][index]
                if before != 'OH1':
                    raise ValueError('Outgoing neutral alcohol requires explicit native OH1 typing')
                derivative['_chem_comp_atom.type_energy'][index] = 'OC2'
                changes.append({'atom_id': atom, 'before': before, 'after': 'OC2', 'policy_id': ENERGY_POLICY})
                rows.append([identifier,'change',atom,'.','.','OC2','.'])
            configuration = project_source_configurations({'source_configuration': stereo}, values, derivative)
            if any(c['status'] != 'RETAINED_SOURCE_NEIGHBORS' for c in configuration):
                raise ValueError('Reaction cannot remove a source-declared configuration')
            site = context['site']; selector = _selection(site, code)
            if rows:
                mod = {'data_':'mod_'+identifier}
                fields = ('mod_id','function','atom_id','new_atom_id','new_type_symbol','new_type_energy','new_partial_charge')
                for i, field in enumerate(fields):mod['_chem_mod_atom.'+field] = [r[i] for r in rows]
                blocks.append(_emit(mod))
                phil.append('refinement.pdb_interpretation.apply_cif_modification {\n'
                            f'  data_mod = {identifier}\n  residue_selection = {selector}\n}}\n')
            actual = atom_rows(derivative)
            plans.append({'site': site, 'context': context, 'selection': selector,
                          'modification_id': identifier if rows else None,
                          'source_projection': projection, 'deleted_atoms': sorted(removed),
                          'energy_type_changes': changes, 'expected_atoms': sorted(actual),
                          'source_configuration_projection': configuration,
                          'projected_definition': derivative})
    artifacts = {'base_dictionary.cif': _render(values, code),
                 'site_modifications.cif': '\n'.join(blocks) if blocks else 'data_mod_reaction_sites\n# No modifications.\n',
                 'site_modifications.phil': ''.join(phil)}
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'PREPARED_REVIEW',
              'component': code, 'source_profile': profile['matched_profile'], 'roles': roles,
              'source_configuration': stereo, 'sites': plans,
              'numerical_group_preserved': True, 'source_classification_preserved': True,
              'metadata_changes': metadata_changes, 'formal_charge_changes': [],
              'native_qualification': 'NOT_ASSESSED', 'isolated_native_qualification': 'NOT_ASSESSED',
              'partner_chemistry': 'NOT_ASSESSED', 'junction_geometry': 'NOT_ASSESSED',
              'experimental_protonation': 'UNASSESSED', 'automatic_adoption': False}
    return report, artifacts


def prepare_furanose_reaction_control(source, numerical, workbook, model, output, *, code, contexts):
    """Freeze a fresh diagnostic attempt and emit native per-site modifiers.

    All model sites sharing this component require explicit contexts. Candidate
    completeness and source stereochemistry are reassessed; a prior isolated pass
    is not treated as proof of the new linked state. No external tool is run.
    """
    paths = dict(zip(('source.cif','numerical.cif','Ligands.xlsx','model.pdb'),
                     [Path(p).expanduser().resolve(strict=True) for p in (source,numerical,workbook,model)]))
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or any(p.is_relative_to(out.resolve()) for p in paths.values()):
        raise ValueError('Output must be separate and cannot traverse symlinks')
    before = {n:p.read_bytes() for n,p in paths.items()}
    with tempfile.TemporaryDirectory(prefix='nasolve-reaction-preflight-') as temporary:
        stage = Path(temporary)
        for n,data in before.items():(stage/n).write_bytes(data)
        _save(stage/'contexts.json', contexts); _save(stage/'selection.json', {'code':code})
        expected, outputs = _derive(stage)
        out.mkdir(parents=True, exist_ok=False)
        for n in _INPUTS:
            with (out/n).open('xb') as stream:stream.write((stage/n).read_bytes())
    actual, frozen = _derive(out)
    if actual != expected or frozen != outputs or any(p.read_bytes() != before[n] for n,p in paths.items()):
        raise ValueError('Reaction inputs changed during freezing')
    for n,data in outputs.items():
        with (out/n).open('x') as stream:stream.write(data)
    _save(out/'preparation.json', actual)
    _save(out/'receipt.json', {'schema_version':1,'policy_id':POLICY_ID,
          'files':{n:_digest(out/n) for n in sorted(_INPUTS | _OUTPUTS)}})
    return read_furanose_reaction_control(out)


def read_furanose_reaction_control(control):
    """Recompute the frozen chemical operation and exact native inputs offline."""
    root = Path(control).expanduser().resolve(strict=True); paths = list(root.rglob('*'))
    if (any(p.is_symlink() or not p.is_file() for p in paths)
            or {p.name for p in paths} != _INPUTS | _OUTPUTS | {'receipt.json'}):
        raise ValueError('Require an exact nonsymlinked reaction capsule')
    before = {p:p.read_bytes() for p in paths}; receipt = _load(root/'receipt.json')
    if (set(receipt) != {'schema_version','policy_id','files'} or type(receipt['schema_version']) is not int
            or receipt['schema_version'] != 1 or receipt['policy_id'] != POLICY_ID
            or receipt['files'] != {n:_digest(root/n) for n in sorted(_INPUTS | _OUTPUTS)}):
        raise ValueError('Invalid completion receipt or checksums')
    report, outputs = _derive(root)
    if (report != _load(root/'preparation.json') or any((root/n).read_bytes() != data.encode() for n,data in outputs.items())
            or any(p.read_bytes() != data for p,data in before.items())):
        raise ValueError('Saved reaction differs from fresh source derivation')
    return report
