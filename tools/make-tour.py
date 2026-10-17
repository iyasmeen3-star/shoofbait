"""Turn a marketer's submission into a ready tour.

    python3 make-tour.py <incoming folder> <tours folder>

<incoming folder> holds listing.json (see api/listing.schema.json) and the 360° photos (.jpg/.jpeg),
in shooting order by file name (1.jpg, 2.jpg … or the camera's own numbering), and optionally one
360° arrival video (.mp4, street → door → first room; listing.json "arrivalEndsAt" = the photo number
it ends in, default 1).
Creates <tours folder>/<id>/ with the photos as 1.jpg, 2.jpg …, tour.json, small previews
(optimize-photos.py), and adds or updates the listing card in <tours folder>/index.json.

Arrows between rooms are not added here: the AI linking step (ai-link, coming) does that. Until then
buyers move with the room list at the bottom of the page.
"""
import importlib.util, json, re, secrets, shutil, subprocess, sys, time
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('optimize_photos', HERE / 'optimize-photos.py')
optimize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optimize)


def shrink_video(src, dst):
    """360° video for phones: 2880×1440 (2:1), H.264, 30 fps, no sound, starts playing before it has fully
    downloaded. A 1-minute camera export (300–500 MB) comes out around 20–40 MB."""
    if not shutil.which('ffmpeg'):
        shutil.copy(src, dst)
        print('warning: ffmpeg not found, video copied as is (GitHub refuses files over 100 MB)')
        return
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-an', '-vf', 'scale=2880:1440,fps=30',
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '26', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', str(dst)], check=True)
    print(f'video: {src.stat().st_size // 2**20} MB -> {dst.stat().st_size // 2**20} MB')


def natural(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', p.name)]


def fail(msg):
    sys.exit('make-tour: ' + msg)


def main(incoming, tours):
    incoming, tours = Path(incoming), Path(tours)
    try:
        L = json.loads((incoming / 'listing.json').read_text(encoding='utf-8'))
    except Exception as e:
        fail(f'listing.json missing or not valid JSON ({e})')
    for k in ('name', 'city', 'agent'):
        if not L.get(k):
            fail(f'listing.json needs "{k}"')
    photos = sorted([p for p in incoming.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg')], key=natural)
    if not photos:
        fail('no .jpg photos found')
    for p in photos:
        w, h = Image.open(p).size
        if abs(w / h - 2) > 0.05:
            fail(f'{p.name} is {w}x{h}: not a 360° photo (should be twice as wide as tall)')

    tid = L.get('id') or f"l{time.strftime('%y%m%d')}-{secrets.token_hex(2)}"
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,63}', tid):
        fail(f'bad id "{tid}"')
    out = tours / tid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    names = L.get('rooms') or []
    panos = []
    for i, p in enumerate(photos, 1):
        shutil.copy(p, out / f'{i}.jpg')
        panos.append({'id': str(i), 'name': names[i - 1] if i <= len(names) and names[i - 1] else f'مكان {i}',
                      'image': f'tours/{tid}/{i}.jpg', 'yaw': 0, 'links': []})
    videos = sorted(p for p in incoming.iterdir() if p.suffix.lower() in ('.mp4', '.mov'))
    arrival = None
    if videos:
        shrink_video(videos[0], out / 'arrival.mp4')
        end = int(L.get('arrivalEndsAt', 1))
        arrival = {'video': f'tours/{tid}/arrival.mp4', 'to': str(min(max(end, 1), len(photos))),
                   'label': 'الطريق إلى البيت'}
    loc = '، '.join(x for x in (L.get('district') and 'حي ' + L['district'], L.get('area'), L.get('city')) if x)
    tour = {'name': L['name'], 'location': loc, 'price': L.get('price', 0), 'area': L.get('size'),
            'agent': L['agent'], 'marketers': L.get('marketers', []), 'license': L.get('license', {}),
            'details': {**L.get('details', {}), **({'type': L['type']} if L.get('type') else {})},
            'pin': L.get('pin'), 'arrival': arrival, 'start': '1', 'linked': False, 'panos': panos}
    tour = {k: v for k, v in tour.items() if v not in (None, {}, [])} | {'panos': panos}
    (out / 'tour.json').write_text(json.dumps(tour, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    optimize.main(out)

    card = {'id': tid, 'name': L['name'], 'type': L.get('type'), 'city': L['city'], 'area': L.get('area'),
            'district': L.get('district'), 'price': L.get('price'), 'bedrooms': L.get('bedrooms'),
            'bathrooms': L.get('bathrooms'), 'size': L.get('size'), 'spots': len(photos),
            'cover': f'tours/{tid}/{"2" if len(photos) > 1 else "1"}.jpg', 'coverX': 50, 'pin': L.get('pin')}
    card = {k: v for k, v in card.items() if v not in (None, '')}
    idx_file = tours / 'index.json'
    idx = json.loads(idx_file.read_text(encoding='utf-8')) if idx_file.exists() else []
    idx = [card] + [o for o in idx if o.get('id') != tid]
    idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'tour ready: {tid} ({len(photos)} photos) -> #{tid}')
    return tid


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
