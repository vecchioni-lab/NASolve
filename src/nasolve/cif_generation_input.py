"""Reproducible native input projection; the original remains chemical authority.

This composes existing input adapters, with no SDK, source discovery, chemical
perception or execution. Temporary files are tool-owned and always removed.
"""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

POLICY_ID = 'cif-source-reader-preparation-v1'
ORDINARY_INPUT_POLICY = 'source-preserving-v1'


def ordinary_generation_options(policy):
    """Resolve the explicit caller recipe into existing frozen generation options.

    This mapping is versioned independently of future adapters. It grants no
    chemical authority or fallback: original-source and native checks still own
    qualification. Absence leaves old requests and defaults unchanged.
    """
    if policy is None:
        return {}
    if type(policy) is not str or policy != ORDINARY_INPUT_POLICY:
        raise ValueError('Unsupported dictionary_input_policy')
    return dict(source_input_policy='cif-source-reader-preparation-v1',
                bond_representation_policy='cif-source-declared-neutral-purine-aromatic-v1')


def validate_source_input_policy(policy):
    if policy is not None and policy != POLICY_ID:
        raise ValueError('Unsupported source input preparation policy')


def _digest(data):
    return dict(sha256=sha256(data).hexdigest(), size=len(data))


def source_input_files(original, code):
    """Derive exact graph/reader files from original bytes, without modifying them."""
    from .cif_numerical_recovery import prepare_graph_generation_source
    from .cif_elbow_input import prepare_elbow_source_dialect_input, prepare_elbow_phosphate_bond_order
    with TemporaryDirectory(prefix='cif-generation-input-') as temporary:
        root=Path(temporary).resolve(strict=True)
        source, graph, reader, consumer=[root/name for name in ('source.cif','graph.cif','reader.cif','consumer.cif')]
        source.write_bytes(original)
        graph_report=prepare_graph_generation_source(source,code,graph)
        reader_report=prepare_elbow_source_dialect_input(source,graph,code,reader)
        dialect=reader_report['consumer_reader_dialect']
        order_report=None
        if dialect=='MONOMER_LIBRARY_CIF':
            order_report=prepare_elbow_phosphate_bond_order(reader,code,consumer)
        else:
            consumer.write_bytes(reader.read_bytes())
        # Keep exact original/derived identities and the actual seed origin. Large
        # repeated assessment inventories are reproduced by the existing adapters.
        report=dict(schema_version=1,policy_id=POLICY_ID,component=code,
            source=_digest(original),graph_policy=graph_report['policy_id'],
            coordinate_origin=graph_report['coordinate_origin'],
            reader_policy=reader_report['policy_id'],reader_dialect=dialect,
            phosphate_order=order_report,chemical_declarations='PRESERVED',
            native_qualification='NOT_RUN',automatic_adoption=False)
        files={f'prepared/{p.name}':p.read_bytes() for p in (graph,reader,consumer)}
        report['files']={name:_digest(data) for name,data in files.items()}
        files['prepared/preparation.json']=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
        if source.read_bytes()!=original:
            raise ValueError('Generation input projection changed its original source')
    binding=dict(policy_id=POLICY_ID,consumer=_digest(files['prepared/consumer.cif']),
        reader_dialect=dialect,input_files={name:_digest(data) for name,data in files.items()})
    return binding,files


def generation_source(config):
    """Return the native input reference from an already validated request."""
    if config['recipe'].get('source_input_policy') is None:
        return 'source.cif',config['source'],config['recipe']['expected_dialect']
    prepared=config['source_preparation']
    return 'prepared/consumer.cif',prepared['consumer'],prepared['reader_dialect']
