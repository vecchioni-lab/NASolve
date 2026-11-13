#!/usr/bin/env python3
"""Check the development roadmap and render its human view; never grant approval."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'docs/topostitch-roadmap.json'
HUMAN = ROOT/'docs/topostitch-roadmap.md'
CLOSED = {'COMPLETE','SCOPED_COMPLETE'}
STATUSES = CLOSED | {'PARTIAL','OPEN','DEFERRED'}


def unique_object(pairs):
    value = {}
    for key,item in pairs:
        if key in value:
            raise ValueError(f'Duplicate roadmap key: {key}')
        value[key] = item
    return value


def validate(value):
    if type(value.get('schema_version')) is not int or value['schema_version'] != 1 or value.get('kind') != 'topostitch-development-roadmap':
        raise ValueError('Unsupported roadmap schema/kind')
    if value.get('runtime_authority') is not False:
        raise ValueError('A development roadmap cannot grant runtime authority')
    date.fromisoformat(value['updated'])
    updates = value['human_updates']; entries = updates['entries']
    if updates['prefix'] != 'W' or not entries or not updates['rule']:
        raise ValueError('Missing human update numbering contract')
    numbers = [entry['number'] for entry in entries]
    if (type(updates['starts_at']) is not int or updates['starts_at'] < 1
            or any(type(n) is not int for n in numbers)
            or numbers != list(range(updates['starts_at'],updates['starts_at']+len(entries)))
            or type(updates['current']) is not int or updates['current'] != numbers[-1]
            or type(updates['next']) is not int or updates['next'] != numbers[-1]+1):
        raise ValueError('Human update numbers must be contiguous, unique and advance by one')
    for entry in entries:
        if not entry['title'] or entry['state'] not in {'RECORDED','IN_PROGRESS'}:
            raise ValueError('Incomplete human update')
        if entry['state'] == 'IN_PROGRESS':
            if entry is not entries[-1] or entry['code_commit'] is not None:
                raise ValueError('Only the latest human update may be in progress')
        elif not isinstance(entry['code_commit'],str) or not re.fullmatch(r'[0-9a-f]{40}',entry['code_commit']):
            raise ValueError('Recorded human updates require exact code provenance')
    for item in [r['last_audit'] for r in value['milestones']] + list(value['evidence'].values()):
        if 'human_update' in item and (type(item['human_update']) is not int or item['human_update'] not in numbers):
            raise ValueError('Unknown human update reference')
    rows = value['milestones']; by_id = {r['id']:r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('Duplicate milestone ID')
    evidence = value['evidence']
    for row in rows:
        identifier = row['id']
        if re.fullmatch(r'[FSP][0-9]{2}',identifier) is None or row['status'] not in STATUSES:
            raise ValueError(f'Invalid milestone ID/status: {identifier}')
        if row['track'] not in {'shared','stitch','pine'} or not row['acceptance'] or not row['next_action']:
            raise ValueError(f'Missing milestone track, acceptance or next action: {identifier}')
        if len(set(row['depends_on'])) != len(row['depends_on']) or not set(row['depends_on']) <= set(by_id):
            raise ValueError(f'Unknown/duplicate milestone dependency: {identifier}')
        if not set(row['evidence']) <= set(evidence):
            raise ValueError(f'Unknown evidence: {identifier}')
        audit = row['last_audit']; date.fromisoformat(audit['date'])
        if not re.fullmatch(r'[0-9a-f]{40}',audit['code_commit']) or not audit['reviewer'] or not audit['scope']:
            raise ValueError(f'Incomplete milestone audit: {identifier}')
        if row['status'] in CLOSED:
            if not row['delivered'] or not row['evidence'] or any(by_id[d]['status'] not in CLOSED for d in row['depends_on']):
                raise ValueError(f'Closed milestone lacks delivered evidence or closed dependencies: {identifier}')
    visited, visiting = set(),set()
    def visit(identifier):
        if identifier in visiting:
            raise ValueError(f'Dependency cycle at {identifier}')
        if identifier in visited: return
        visiting.add(identifier)
        for dep in by_id[identifier]['depends_on']: visit(dep)
        visiting.remove(identifier); visited.add(identifier)
    for identifier in by_id: visit(identifier)
    for order in [value['current_priority'],*value['work_order'].values()]:
        if len(set(order)) != len(order) or not set(order) <= set(by_id):
            raise ValueError('Unknown or duplicated work-order entry')
    for item in value['benchmarks']:
        if not set(item['jobs']) <= set(by_id): raise ValueError('Benchmark refers to an unknown job')
    for identifier,item in evidence.items():
        reference = item['reference'].split('#')[0]
        path = (ROOT/reference).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f'Missing/outside-repository evidence reference: {identifier}')
        if not item['result'] or not item['limitation']:
            raise ValueError(f'Evidence must retain result and limitation: {identifier}')


def human_audit(item):
    label = f"W{item['human_update']}" if 'human_update' in item else 'earlier work'
    return f"[{label}](https://github.com/vecchioni-lab/NASolve/commit/{item['code_commit']})"


def render(value):
    lines = ['# TopoStitch and Pine completion roadmap','',
        f"**Current audited work queue: {value['updated']}.** Generated from",
        '[the machine-readable ledger](topostitch-roadmap.json); edit that ledger and run',
        '`python scripts/audit_topostitch_roadmap.py --write`, then `--check`.',
        'This is one queue with two linked tracks, not two competing implementations.',
        'The [design](topostitch.md) owns semantics, the [handoff](development-handoff.md)',
        'owns the current code/validation edge, and cited evidence owns scientific claims.',
        'A recut changes representation; a bend changes the physical structure. Neither',
        'operation authorizes a chemical nick or chemistry change.','',
        '## Finish lines','']
    updates=value['human_updates']; current=updates['entries'][-1]
    at=lines.index('## Finish lines')
    lines[at:at]=[f"**Current update: W{updates['current']} — {current['title']}.** "
        +f"Next: W{updates['next']}.", '',
        'Use these numbers in human updates. Exact commits remain in the machine ledger;',
        'earlier history is not renumbered. An update number does not close a scientific gate.', '',
        '## Recent Willow updates', '', '| Update | Work | Record |', '| --- | --- | --- |'] + [
        f"| W{e['number']} | {e['title']} | {e['state']} |" for e in updates['entries'][-10:]] + ['']
    for label,key in [('First explicit stitch','explicit_stitch'),('Campaign stitching','campaign_stitch'),('Pine ASU slicing','pine_slicing')]:
        lines += [f"- **{label}:** {value['finish_lines'][key]}"]
    lines += ['', '## Current order and audit discipline','',
        '**Immediate focus:** '+', '.join(value['current_priority'])+'.',
        'The two tracks share F01/F02. Intact-duplex repair does not require finishing',
        'the whole ASU editor; ASU slicing cannot be used to disguise a physical gap.',
        'Prototype work may precede a dependency, but scientific closure cannot.','']
    for name,order in value['work_order'].items():
        lines += [f"- **{name.title()}:** "+' → '.join(order)+'.']
    lines += ['', 'Audit at every substantial checkpoint, not only at the end of a session:','']
    lines += [f'{i}. {rule}' for i,rule in enumerate(value['audit_rules'],1)]
    lines += ['', '**Status meanings:** SCOPED_COMPLETE closes only its stated supported scope;',
        'PARTIAL records delivered work with open acceptance; OPEN has not met its gate;',
        'DEFERRED is outside the current finish line. COMPLETE requires the full declared',
        'gate. The audit script checks consistency and references, not scientific truth.','']
    for track,title in [('shared','Shared foundations'),('stitch','Roadmap A — working sticky-end repair'),('pine','Roadmap B — Pine ASU slicing and required GUI')]:
        selected = [r for r in value['milestones'] if r['track']==track]
        lines += [f'## {title}','','| Job | Laboratory outcome | Status | Depends on |','| --- | --- | --- | --- |']
        for row in selected:
            lines += [f"| [{row['id']}](#{row['id'].lower()}) | {row['title']} | {row['status']} | {', '.join(row['depends_on']) or '—'} |"]
        for row in selected:
            lines += ['',f'<a id="{row["id"].lower()}"></a>',f"### {row['id']} — {row['title']}",'',row['goal'],'',
                '**Delivered:** '+(' '.join(row['delivered']) if row['delivered'] else 'No implemented capability is claimed.'),'',
                '**Closure audit:**','']
            lines += [f'- {criterion}' for criterion in row['acceptance']]
            lines += ['', '**Next action:** '+row['next_action'],
                '**Evidence:** '+(', '.join(f'[{e}](#{e.lower()})' for e in row['evidence']) or 'None yet')+'.',
                f"**Last audit:** {row['last_audit']['date']}, {row['last_audit']['reviewer']}, {human_audit(row['last_audit'])}; {row['last_audit']['scope']}."]
        lines += ['']
    lines += ['## Benchmark register','','Private input/result bindings stay in local frozen receipts; these labels are not',
        'operational paths or proof that an arbitrary model/dataset combination is solvable.','',
        '| Case | State | Jobs | Remaining evidence |','| --- | --- | --- | --- |']
    for item in value['benchmarks']:
        lines += [f"| {item['id']} — {item['case']} | {item['state']} | {', '.join(item['jobs'])} | {item['remaining']} |"]
    lines += ['', '## Evidence and limits','']
    for identifier,item in value['evidence'].items():
        ref=item['reference'].removeprefix('docs/')
        lines += [f'<a id="{identifier.lower()}"></a>',f'### {identifier} — {item["kind"]}','',
            f"[Evidence contract]({ref}) at {human_audit(item)}.",item['result'],
            '**Limit:** '+item['limitation'],'']
    lines += ['## Deferred extensions, not hidden blockers','']
    for item in value['deferred']: lines += [f"- **{item['scope']}:** {item['trigger']}"]
    lines += ['', '## Reconciliation: reuse what is already delivered','']
    lines += ['<details><summary>Earlier implementation references</summary>', '']
    lines += ['- '+line for line in value['history_reconciliation']]
    lines += ['', '</details>']
    lines += ['', 'Modeled on Cedar’s separation of completion queue, capability contract and',
        'evidence ledger. No queue edit grants runtime authority, scientific approval',
        'or permission to merge branches.','']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--write',action='store_true',help='Regenerate the human view after validating the ledger')
    mode.add_argument('--check',action='store_true',help='Check the ledger and human view without writing (default)')
    args = parser.parse_args()
    try:
        value=json.loads(SOURCE.read_text(),object_pairs_hook=unique_object)
        validate(value); expected=render(value)
        if args.write: HUMAN.write_text(expected)
        elif not HUMAN.is_file() or HUMAN.read_text()!=expected:
            raise ValueError('Human roadmap is stale; audit the ledger and run --write')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'{parser.prog}: {exc}\n')
    print(f"Roadmap structure, references and synchronization passed: {len(value['milestones'])} jobs; scientific closure still requires the recorded acceptance audit.")


if __name__=='__main__':
    main()
