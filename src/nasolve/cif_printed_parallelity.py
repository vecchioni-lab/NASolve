"""Read printed Phenix parallelity observations without rebuilding restraints.

Supported input is the pipe-header GEO layout with two fixed PDB-label columns
and residual/delta(deg)/sigma values. Printed values have limited precision; they
cannot establish exact weights, targets, derivatives or chemical acceptance.
"""
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re

POLICY_ID = 'cif-printed-parallelity-observation-v1'
_SECTION = re.compile(r'\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(restraints|interactions):\s*([0-9]+)\s*')
_TABLE = re.compile(r'\s*plane 1\s+plane 2\s+residual\s+delta\(deg\)\s+sigma\s*')
_LABEL = re.compile(r'pdb="[^"\r\n]+"')
_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')
_FIELDS = ('residual', 'delta_degrees', 'sigma')


def _need(condition, message):
    if not condition:
        raise ValueError('Printed parallelity: ' + message)


def _values(tokens):
    _need(len(tokens) == 3, 'require exactly residual, delta(deg) and sigma')
    _need(all(_NUMBER.fullmatch(t) for t in tokens), 'unsupported numerical spelling')
    values = [float(t) for t in tokens]
    _need(all(isfinite(v) for v in values), 'nonfinite printed value')
    return dict(zip(_FIELDS, tokens)), dict(zip(_FIELDS, values))


def parse_printed_parallelity(text):
    """Keep every declared group and original plane order; reject partial reads.

    Blank lines end individual groups, not their enclosing section. Label columns
    come from each group's first row, where both planes must have an atom. Later
    one-label rows stay in their original column, including a longer second plane.
    Missing sections mean NOT_RECORDED, not proof of zero native restraints.
    """
    _need(isinstance(text, str), 'require decoded GEO text')
    sections = []
    section = None
    block = None
    columns = None

    def finish_block():
        nonlocal block, columns
        if block is not None:
            for field in ('plane_1', 'plane_2'):
                labels = block[field]
                _need(len(labels) >= 3 and len(labels) == len(set(labels)),
                      'require at least three distinct labels in each plane')
            section['restraints'].append(block)
        block = None
        columns = None

    def finish_section():
        if section is not None:
            _need(len(section['restraints']) == section['declared_restraints'],
                  'parsed group count differs from the printed section count')

    for line_number, line in enumerate(text.splitlines(), 1):
        header = _SECTION.fullmatch(line)
        if header:
            finish_block()
            finish_section()
            kind, origin, count_kind, count = header.groups()
            section = None
            if kind == 'Parallelity':
                _need(count_kind == 'restraints', 'unsupported parallelity count heading')
                section = dict(origin=origin, header_line=line_number,
                               declared_restraints=int(count), restraints=[])
                sections.append(section)
            continue
        _need(not line.lstrip().startswith('Parallelity'), 'unsupported or malformed section header')
        if section is None:
            _need(_TABLE.fullmatch(line) is None, 'table has no enclosing section')
            continue
        if not line.strip():
            finish_block()
            continue
        if line.strip() == 'Sorted by residual:':
            _need(block is None and not section['restraints'], 'unexpected sorting header')
            continue
        if _TABLE.fullmatch(line):
            finish_block()
            block = dict(header_line=line_number, plane_1=[], plane_2=[])
            continue
        _need(block is not None, 'unexpected content outside a group')
        labels = list(_LABEL.finditer(line))
        _need(1 <= len(labels) <= 2, 'unsupported label row')
        spans = [(m.start(), m.end()) for m in labels]
        _need(not line[:spans[0][0]].strip()
              and all(not line[a[1]:b[0]].strip() for a, b in zip(spans, spans[1:])),
              'unsupported content between label columns')
        trailing = line[spans[-1][1]:].split()
        if columns is None:
            _need(len(labels) == 2, 'first row must identify both plane columns')
            columns = tuple(m.start() for m in labels)
            block['printed_values'], block['values'] = _values(trailing)
        else:
            _need(not trailing, 'unexpected numerical content after first row')
        for match in labels:
            _need(match.start() in columns, 'label changed its printed column')
            field = 'plane_1' if match.start() == columns[0] else 'plane_2'
            block[field].append(match.group())
    finish_block()
    finish_section()
    return dict(schema_version=1, policy_id=POLICY_ID,
                status='OBSERVED' if sections else 'NOT_RECORDED',
                source_sha256=sha256(text.encode('utf-8')).hexdigest(),
                sections=sections,
                observed_restraints=sum(len(s['restraints']) for s in sections) if sections else None,
                numerical_scope='PRINTED_PRECISION_ONLY; NO_WEIGHT_OR_TARGET_RECONSTRUCTION',
                scientific_approval='NOT_ASSESSED', automatic_adoption=False)


def read_printed_parallelity(path):
    """Read an explicit file without changing it; detect changes during parsing."""
    path = Path(path)
    before = path.read_bytes()
    result = parse_printed_parallelity(before.decode('utf-8'))
    _need(path.read_bytes() == before, 'source changed during observation')
    return result
