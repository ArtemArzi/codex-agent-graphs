"""Render declared observations conservatively; this helper does not collect evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

STATUSES = {'confirmed', 'partial', 'open', 'falsified'}


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get('hypothesis'), str) or not payload['hypothesis'].strip():
        raise ValueError('hypothesis must be a nonempty string')
    rows = payload.get('expectations')
    if not isinstance(rows, list) or not rows:
        raise ValueError('expectations must contain at least one observable expectation')
    checked, ids = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('each expectation must be an object')
        item = dict(row)
        ident = item.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            raise ValueError('expectation IDs must be nonempty unique strings')
        ids.add(ident)
        if not isinstance(item.get('expected'), str) or not item['expected'].strip():
            raise ValueError(f'{ident}: expected must describe an observable criterion')
        status = item.get('status', 'open')
        if status not in STATUSES:
            raise ValueError(f'{ident}: unsupported status {status!r}')
        required = item.get('required', True)
        if not isinstance(required, bool):
            raise ValueError(f'{ident}: required must be boolean')
        item['required'] = required
        item['declared_status'] = status
        evidence = item.get('evidence') or {}
        if not isinstance(evidence, dict):
            raise ValueError(f'{ident}: evidence must be an object')
        has_evidence = all(isinstance(evidence.get(k), str) and evidence[k].strip()
                           for k in ('source', 'observed_at', 'scope', 'observation'))
        # A label, screenshot filename or asserted PASS alone is not an observation.
        if status != 'open' and not has_evidence:
            item['status'] = 'open'
            item['warning'] = 'Declared result lacks source, observation time, scope or observation.'
        else:
            item['status'] = status
        checked.append(item)
    required = [r for r in checked if r['required']]
    if not required:
        raise ValueError('at least one expectation must be required')
    if any(r['status'] == 'falsified' for r in required):
        overall = 'falsified'
    elif all(r['status'] == 'open' for r in checked):
        overall = 'open'
    elif all(r['status'] == 'confirmed' for r in checked):
        overall = 'confirmed'
    else:
        overall = 'partial'
    return {'hypothesis': payload['hypothesis'], 'overall': overall,
            'expectations': checked,
            'boundary': 'Summarizes declared observations in their stated scope; does not verify sources or establish financial truth.'}


def cell(value) -> str:
    return str(value if value is not None else '').replace('|', '\\|').replace('\n', '<br>')


def render(result: dict) -> str:
    lines = [f"Гипотеза: {result['hypothesis']}", f"Итог: **{result['overall']}**", '',
             result['boundary'], '',
             '| ID | Ожидание | Обязательное | Наблюдение и источник | Статус |',
             '| --- | --- | --- | --- | --- |']
    for r in result['expectations']:
        e = r.get('evidence') or {}
        evidence = ' · '.join(str(e.get(k, '')) for k in ('observation', 'source', 'observed_at', 'scope'))
        lines.append('| ' + ' | '.join(map(cell, [r['id'], r['expected'], r['required'], evidence, r['status']])) + ' |')
    lines += ['', '| ID | Разрыв или недостающий факт |', '| --- | --- |']
    for r in result['expectations']:
        if r['status'] != 'confirmed':
            lines.append(f"| {cell(r['id'])} | {cell(r.get('warning') or r.get('gap') or 'Нужно уточнить или проверить ожидание')} |")
    lines += ['', '| ID | Следующее действие | Ответственный | Срок |', '| --- | --- | --- | --- |']
    for r in result['expectations']:
        if r['status'] != 'confirmed':
            lines.append('| ' + ' | '.join(map(cell, [r['id'], r.get('next_action', 'Не определено'),
                                                     r.get('owner', 'Не определён'), r.get('due', 'Не определён')])) + ' |')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.input.read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError) as exc:
        print(f'Invalid evidence input: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else render(result), end='\n' if args.json else '')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
