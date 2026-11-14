"""Opt-in full-model pairing and stacking through the existing NAR compiler.

Coordinate guessing selects relationships, never chemical identity. The initial
scope requires an unambiguous, single-model nucleotide PDB and at least one
detected pair. Unpaired sites and absent symmetry search remain explicit.
"""
from hashlib import sha256
import json
from pathlib import Path


def prepare_full_model_restraints(model, output, *, data_root=None,
                                  ready_set_executable=None):
    from restraints import guesser
    from restraints.residue_library import load_residue_records
    from .cif_explicit_na_policy import _model, compile_explicit_na_policy
    from .component_records import resolve_component_record
    from .curated_ligands import ligand_source
    from .postmr import _patch_narestraints_records

    model, output = Path(model).absolute(), Path(output).absolute()
    if output.exists() or any(p.is_symlink() for p in [output, *output.parents]):
        raise FileExistsError('Full-model restraints require a fresh regular output directory')
    before, _, residues, codes, _, _ = _model(model)
    records, corrections = _patch_narestraints_records(load_residue_records(), set(codes.values()))
    for code in sorted(set(codes.values())):
        try:
            resolve_component_record(records, code)
        except ValueError as exc:
            raise ValueError(f'Full-model NARestraints cannot map component {code}: {exc}') from exc
    original = guesser.load_residue_records
    guesser.load_residue_records = lambda: records
    try:
        candidates, warnings = guesser.guess_pairs(model, allow_noncanonical=True)
    finally:
        guesser.load_residue_records = original
    if not candidates:
        raise ValueError('No base pairs detected for the full-model recipe; no complete pairing policy can be claimed')
    pairs = []
    for candidate in candidates:
        sites = [p.chain + ':' + str(p.resid) for p in [candidate.first, candidate.second]]
        pairs.append({'sites': sites, 'components': [codes[s] for s in sites], 'scope': 'requested'})
    # Match NAR's declared consecutive-chain policy without bridging TER records.
    order = []; segments = {}; segment = 0
    for line in before.decode('ascii').splitlines():
        if line[:6].strip() == 'TER':
            segment += 1
        elif line[:6] in {'ATOM  ', 'HETATM'}:
            site = line[21] + ':' + line[22:26].strip()
            if site not in segments:
                segments[site] = segment; order.append(site)
    stacks = [(a, b) for a, b in zip(order, order[1:])
              if a.split(':')[0] == b.split(':')[0] and segments[a] == segments[b]]
    sources = {code: ligand_source(code, data_root, ready_set_executable=ready_set_executable)
               for code in sorted(set(codes.values()))}
    if model.read_bytes() != before:
        raise ValueError('Model changed during full-model relationship selection')
    # The compiler binds every selector to the actual PDB and source graph,
    # rejects duplicate/multiply paired sites, and disables competing native SS.
    used = {s for row in pairs for s in row['sites']} | {s for edge in stacks for s in edge}
    used_codes = {codes[s] for s in used}
    compiled = compile_explicit_na_policy(model, pairs, stacks,
        {c: sources[c].path.resolve() for c in used_codes}, output / 'compiled')
    if model.read_bytes() != before:
        raise ValueError('Model changed during full-model restraint compilation')
    paired = {s for row in pairs for s in row['sites']}
    result = {
        'schema_version': 1, 'mode': 'full-model', 'scope': 'all',
        'policy_authority': 'NARestraints', 'automatic_adoption': False,
        'model_sha256': sha256(before).hexdigest(),
        'mapped_site_count': len(residues), 'retained_pair_count': len(pairs),
        'stack_count': len(stacks), 'include_stacking': True,
        'retained_pairs': pairs, 'unpaired_sites': [s for s in order if s not in paired],
        'unrestrained_relationship_sites': [s for s in order if s not in used],
        'symmetry_pairs': 'NOT_SEARCHED', 'guesser_warnings': list(warnings),
        'selection': 'NAR_COORDINATE_GUESS_WITH_NONCANONICAL_RECIPES',
        'stack_policy': 'NAR_CHAIN_ORDER_WITH_TER_BOUNDARIES; NOT_COVALENT_LINK_PROOF',
        'source_authority': {c: {'kind': sources[c].kind, 'authority': sources[c].authority}
                             for c in used_codes},
        'compatibility_corrections': corrections,
        'request_counts': compiled['request_counts'],
        'restraint_file': 'compiled/explicit_na_policy.phil',
        'compiler_receipt': 'compiled/explicit_na_policy.json',
        'native_membership': 'NOT_ASSESSED', 'scientific_qualification': 'NOT_ASSESSED',
    }
    (output / 'full_model_restraints.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    return result
