"""Explicit crystal-link context before preparation, without ordinary admission.

Read the existing registered graph and local phosphate audit. Keep image bonds
separate from same-image links; old preparation consumers cannot accept this
record as their local-only context. No native terms, sources or coordinates are
created here. Construction lineage and chemical qualification belong downstream.
"""
from hashlib import sha256
from pathlib import Path
import re

from .cif_dictionary_sites import _need, _read
from .cif_model_context import _intent, _local_backbone
from .cif_phosphate_continuation import (
    RegisteredContinuation, _inherit_measured, inspect_registered_backbone,
)
from .cif_prepared_backbone import _registered_partners

POLICY_ID = 'registered-preparation-context-v1'


def derive_registered_preparation_context(model, report, components, *,
        registration_model, registration, discovery, continuations):
    """Describe every local/image partner through explicit registered sources.

    registration_model is the exact model bound by the graph. A later model uses
    the existing same-frame named-atom transfer, never a new nearest-partner
    search. That transfer proves endpoint identity/frame, not checkpoint ancestry.
    Callers must supply all input paths again to reconstruct this passive record;
    this function performs no basename discovery, persistence or publication.
    """
    _need(isinstance(components, (list, tuple)) and 1 <= len(components) <= 16
          and all(isinstance(c,str) and re.fullmatch(r'[A-Za-z0-9]{1,3}',c) for c in components)
          and len(set(components)) == len(components), 'Require unique explicit selected components')
    paths = dict(model=Path(model), registration_model=Path(registration_model),
                 registration=Path(registration), discovery=Path(discovery), continuations=Path(continuations))
    original = {key:_read(path) for key,path in paths.items()}
    hashes = {key:sha256(raw).hexdigest() for key,raw in original.items()}
    intent = _intent(report); codes = sorted(components)
    sites, local_links, audit, open_sites = _local_backbone(paths['model'], intent, codes, review_open=True)
    observations = inspect_registered_backbone(paths['registration_model'], paths['registration'],
                                               paths['discovery'], paths['continuations'])
    if original['registration_model'] != original['model']:
        observations = [_inherit_measured(paths['registration_model'], paths['model'],
            RegisteredContinuation(row['registered_continuation']['continuation_id'],
                paths['registration'], paths['discovery'], paths['continuations']), row)
            for row in observations]
    terminal = intent['post_mr_plan']['allow_op3_sites']
    registration_info, image_links = _registered_partners(observations, hashes['model'], sites,
                                                         local_links, open_sites, terminal)
    _need(audit['input_sha256'] == hashes['model'], 'Prepared model changed during context derivation')
    # Preserve both image directions. Source and target are coordinate identities;
    # logical identities and the graph binding stay in the image-link records.
    incoming = {b:dict(site=a,relation='local',operator_xyz='x,y,z') for a,b in local_links}
    outgoing = {a:dict(site=b,relation='local',operator_xyz='x,y,z') for a,b in local_links}
    for row, observation in zip(image_links, observations, strict=True):
        source, target = row['o3_site'], row['phosphate_site']
        _need(source not in outgoing and target not in incoming, 'Competing local/image phosphate partner')
        incoming[target] = dict(site=source,relation='registered_image',operator_xyz=row['o3_image'],
                                continuation_id=row['id'])
        outgoing[source] = dict(site=target,relation='registered_image',operator_xyz=row['target_operator_xyz'],
                                continuation_id=row['id'])
        edge = observation['registered_continuation']
        if 'frame_transfer' in edge:
            row['frame_transfer'] = edge['frame_transfer']
    contexts = {code:[dict(site=site,incoming=incoming.get(site),outgoing=outgoing.get(site),
        five_prime_state='linked' if site in incoming else 'phosphate' if 'P' in data['atoms'] else 'free_OH',
        three_prime_state='linked' if site in outgoing else 'free_OH')
        for site,data in sorted(sites.items()) if data['code']==code] for code in codes}
    _need(all(_read(paths[key]) == raw for key,raw in original.items()) and _intent(report) == intent,
          'Registered preparation input changed during derivation')
    return dict(schema_version=1, policy_id=POLICY_ID, status='REGISTERED_CONTEXT_FOR_REVIEW',
        model_sha256=hashes['model'], source_model_sha256=hashes['registration_model'],
        input_sha256=hashes, components=codes, intent=intent, site_contexts=contexts,
        local_links=local_links, image_links=image_links, registration=registration_info,
        protected_terminal_phosphates=sorted(terminal), phosphate_audit=audit,
        native_qualification='NOT_RUN', ordinary_admission=False,
        scientific_qualification='NOT_ASSESSED')
