"""Approve a draft tour: removes the "draft" mark and puts it on the listings page.

    python3 approve-tour.py <tours folder> <id>

Claude runs this when the team says the tour is approved.
"""
import json, sys
from pathlib import Path


def main(tours, tid):
    tours = Path(tours)
    tf = tours / tid / 'tour.json'
    tour = json.loads(tf.read_text(encoding='utf-8'))
    tour.pop('draft', None)
    tf.write_text(json.dumps(tour, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    idx_file = tours / 'index.json'
    idx = json.loads(idx_file.read_text(encoding='utf-8'))
    for o in idx:
        if o.get('id') == tid:
            o.pop('hidden', None)
    idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'approved: {tid}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
