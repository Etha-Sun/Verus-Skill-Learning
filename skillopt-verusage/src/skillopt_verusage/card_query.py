"""Optional paginated full-text card lookup; results are matches, not advice."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


STOP = {'a', 'an', 'and', 'the', 'is', 'of', 'to', 'in', 'for', 'with', 'or'}


def terms(text):
    return set(re.findall(r'[a-z][a-z0-9_]*', text.lower())) - STOP


def search(cards, query, *, limit=5, offset=0):
    if not query.strip() or not terms(query):
        raise ValueError('Supply at least one searchable keyword')
    if limit < 1 or offset < 0:
        raise ValueError('limit must be positive and offset nonnegative')
    wanted = terms(query)
    rows = []
    for card in cards:
        content = card['content']
        matched = sorted(wanted & terms(content))
        if not matched:
            continue
        trigger = content.split('**Action:**', 1)[0]
        score = len(matched) + 2 * len(wanted & terms(trigger))
        sections = re.split(r'(?=\*\*[A-Za-z][A-Za-z ]*:\*\*)', content)
        excerpts = [s.strip() for s in sections if wanted & terms(s)]
        rows.append({'id': card['id'], 'score': score, 'matched_terms': matched,
                     'excerpt': '\n'.join(excerpts)[:800]})
    rows.sort(key=lambda row: (-row['score'], row['id']))
    end = offset + limit
    return {'card_retrieval': 1, 'operation': 'search', 'query': query,
            'total_matches': len(rows), 'offset': offset, 'limit': limit,
            'next_offset': end if end < len(rows) else None,
            'results': rows[offset:end],
            'caveat': 'Lexical matches only. Check full Trigger and Avoid when; '
                      'refine keywords or page freely. No recommendation or required read count.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    cards = json.loads(Path(__file__).with_name('cards.json').read_text())['cards']
    try:
        result = search(cards, args.query, limit=args.limit, offset=args.offset)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
