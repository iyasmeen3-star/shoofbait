"""Get a tour's 360° photos ready for phones on mobile data.

    python3 optimize-photos.py tours/<id>

For every photo in tours/<id>/tour.json:
  - the photo itself is saved at most 4096 px wide (2:1), JPEG quality 80, progressive.
    GoPro files (about 5.7K, 5-10 MB) come out around 1-2 MB; every phone can show 4096 px.
  - a small preview <name>-s.jpg (1024 x 512, about 40-80 KB) is made, and tour.json gets
    "preview" for that photo. The page shows the preview at once and swaps in the full photo
    when it has arrived.
Safe to run again: photos already small enough are left as they are (previews are remade).
Keep the camera originals somewhere else (Google Drive), not in the repo.
"""
import json, sys
from pathlib import Path
from PIL import Image

FULL_W, PREV_W = 4096, 1024


def main(folder):
    folder = Path(folder)
    tour_file = folder / 'tour.json'
    tour = json.loads(tour_file.read_text(encoding='utf-8'))
    for p in tour['panos']:
        src = folder / Path(p['image']).name
        im = Image.open(src)
        im = im.convert('RGB')
        w, h = im.size
        if abs(w / h - 2) > 0.05:
            print(f'warning: {src.name} is {w}x{h}, not 2:1. Is it a real 360° photo?')
        before = src.stat().st_size
        if w > FULL_W:
            im = im.resize((FULL_W, FULL_W // 2), Image.LANCZOS)
            im.save(src, 'JPEG', quality=80, optimize=True, progressive=True)
        prev = src.with_name(src.stem + '-s.jpg')
        im.resize((PREV_W, PREV_W // 2), Image.LANCZOS).save(prev, 'JPEG', quality=70, optimize=True, progressive=True)
        p['preview'] = str(Path(p['image']).with_name(prev.name))
        print(f'{src.name}: {before // 1024} KB -> {src.stat().st_size // 1024} KB, preview {prev.stat().st_size // 1024} KB')
    tour_file.write_text(json.dumps(tour, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
