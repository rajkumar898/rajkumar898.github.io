# -*- coding: utf-8 -*-
"""Build Photos/web/ from the event folders in Photos/, and print SITE.galleryPhotos.

Each folder under Photos/ is one event. Its caption.txt supplies the caption and
the alt text; a folder may carry more than one caption block, addressed to
specific images by position ("For images 3-5:").

Originals are never touched. Phone photos carry EXIF orientation, so each image
is transposed before resizing or half of them come out sideways. Videos are
re-encoded to H.264 with the audio track DROPPED — they autoplay muted on the
page, and a file with no audio stream cannot surprise anyone.

    python tools/build_media.py
"""
import io, os, re, subprocess, sys
from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

try:
    import cv2
except ImportError:
    cv2 = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Photos')
OUT = os.path.join(SRC, 'web')
PROFILE_DIR = os.path.join(ROOT, 'profile photo')
PROFILE_OUT = os.path.join(ROOT, 'assets', 'profile.jpg')

# The original portrait, full width, trimmed at the bottom — head down to just
# below the pockets, which comes out square. Fractions of the original
# (left, top, right, bottom). Adjust these four numbers and re-run if you
# replace the original; the tool prints the resulting size and aspect ratio.
PROFILE_CROP = (0.0, 0.0, 1.0, 0.80)

MAX_EDGE = 1400          # displayed ~450px wide; 1400 covers 2x retina
QUALITY = 82
VIDEO_W = 854            # the carousel frame is ~520px, so this is still 1.6x
VIDEO_CRF = '32'

IMG_EXT = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp'}
VID_EXT = {'.mp4', '.mov', '.m4v', '.webm'}

# The order the events open the carousel in. One slide is taken from each, in
# this order, before anything repeats; folders not listed here follow, and the
# rest of the run is interleaved so no two neighbouring slides share an event.
EVENT_ORDER = [
    'Green Hydrogen RLRC Forum',
    'Global Hyperscale AI Camp',
    'BK-21 Colloquium 2025',
    'ICCC 2025 Conference Taiwan',
    'KIIT Conference 2026',
    'RD and Innovation Symposium',
]

# Which shot leads each event — named by the ORIGINAL file, so it survives
# adding or removing other photos in the folder. Anything unlisted just leads
# with whatever sorts first.
LEAD = {
    'Green Hydrogen RLRC Forum':    '22.png',
    'Global Hyperscale AI Camp':    'IMG_5818.JPG.jpeg',
    'BK-21 Colloquium 2025':        'IMG_6516.JPG.jpeg',
    'ICCC 2025 Conference Taiwan':  'WhatsApp Image 2025-12-22 at 11.44.22 PM.jpeg',
    'KIIT Conference 2026':         '1.jpg',
    'RD and Innovation Symposium':  'IMG_8002.mp4',
}

out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def slug(s, n=46):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:n].strip('-')


# ---------------------------------------------------------------- captions ---
RANGE = re.compile(r'^for\s+images?\s+([\d\s,and&-]+):?\s*$', re.I)


def parse_captions(path, count):
    """-> list of (caption, alt), one per image index, from a caption.txt."""
    if not os.path.isfile(path):
        return [('', '')] * count
    lines = [l.strip() for l in io.open(path, encoding='utf-8').read().splitlines()]

    blocks, cur = [], {'idx': None, 'caption': '', 'alt': ''}
    for l in lines:
        if not l:
            continue
        m = RANGE.match(l)
        if m:
            if cur['caption'] or cur['alt']:
                blocks.append(cur)
            nums = []
            for part in re.split(r'[,&]|\band\b', m.group(1)):
                part = part.strip()
                if not part:
                    continue
                if '-' in part:
                    a, b = part.split('-', 1)
                    nums += list(range(int(a), int(b) + 1))
                else:
                    nums.append(int(part))
            cur = {'idx': nums, 'caption': '', 'alt': ''}
        elif l.lower().startswith('caption:'):
            cur['caption'] = l.split(':', 1)[1].strip()
        elif l.lower().startswith('alt:'):
            cur['alt'] = l.split(':', 1)[1].strip()
    if cur['caption'] or cur['alt']:
        blocks.append(cur)

    res = [('', '')] * count
    generic = [b for b in blocks if b['idx'] is None]
    if generic:
        res = [(generic[0]['caption'], generic[0]['alt'])] * count
    for b in blocks:
        if not b['idx']:
            continue
        for i in b['idx']:
            if 1 <= i <= count:
                res[i - 1] = (b['caption'], b['alt'])
    return res


# -------------------------------------------------------------- focal point ---
# The carousel frame is 16:10 and fills with `object-fit: cover`, so an image
# taller than that is trimmed top and bottom. Centred, that cuts the head off a
# portrait shot. These find the face and emit the `object-position` that keeps
# it in frame.
FRAME = 16.0 / 10.0

_CASCADES = None


def cascades():
    global _CASCADES
    if _CASCADES is None:
        d = cv2.data.haarcascades
        _CASCADES = [cv2.CascadeClassifier(os.path.join(d, n)) for n in
                     ('haarcascade_frontalface_default.xml',
                      'haarcascade_frontalface_alt2.xml',
                      'haarcascade_profileface.xml')]
    return _CASCADES


def face_y(path):
    """Vertical centre of the most confidently detected face, 0..1, or None.

    Three cascades vote. Overlapping detections are merged into one cluster and
    the cluster with the most votes wins, which throws out most of the single-
    cascade false positives Haar is prone to on busy conference backgrounds.
    """
    if cv2 is None:
        return None, 0
    img = cv2.imread(path)
    if img is None:
        return None, 0
    h, w = img.shape[:2]
    small = cv2.resize(img, (900, int(h * 900.0 / w))) if w > 900 else img
    sh, sw = small.shape[:2]
    g = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))

    clusters = []
    for cls in cascades():
        for (bx, by, bw, bh) in cls.detectMultiScale(
                g, 1.07, 9, minSize=(int(sw * .04), int(sw * .04))):
            cx, cy = bx + bw / 2.0, by + bh / 2.0
            for c in clusters:
                if abs(c['cx'] - cx) < bw * .6 and abs(c['cy'] - cy) < bh * .6:
                    c['n'] += 1
                    c['cx'] = (c['cx'] * (c['n'] - 1) + cx) / c['n']
                    c['cy'] = (c['cy'] * (c['n'] - 1) + cy) / c['n']
                    c['w'] = max(c['w'], bw)
                    break
            else:
                clusters.append({'cx': cx, 'cy': cy, 'w': bw, 'n': 1})

    if not clusters:
        return None, 0
    best = max(clusters, key=lambda c: (c['n'], c['w']))
    return best['cy'] / float(sh), best['n']


def focus_for(path, size):
    """-> a CSS object-position string, or '' when plain centring is right."""
    w, h = size
    if w / float(h) >= FRAME:
        return ''                      # wider than the frame: nothing is lost
    cy, votes = face_y(path)
    if cy is None:
        return ''
    # A lone cascade firing below the midline is nearly always a false positive
    # — furniture, a logo, a patch of slide. Faces sit high; trust that.
    if votes < 2 and cy > 0.60:
        return ''
    cy = max(0.05, min(0.85, cy))
    if abs(cy - 0.5) < 0.04:
        return ''
    return '50%% %d%%' % round(cy * 100)


# ------------------------------------------------------------------ images ---
def write_image(src, dest):
    im = Image.open(src)
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA')
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')
    w, h = im.size
    if max(w, h) > MAX_EDGE:
        f = MAX_EDGE / float(max(w, h))
        im = im.resize((max(1, int(w * f)), max(1, int(h * f))), Image.LANCZOS)
    im.save(dest, 'JPEG', quality=QUALITY, optimize=True, progressive=True)
    return im.size


def write_video(src, dest, poster):
    exe = ffmpeg()
    subprocess.run([exe, '-y', '-loglevel', 'error', '-i', src,
                    '-vf', 'scale=%d:-2' % VIDEO_W,
                    '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p',
                    '-crf', VIDEO_CRF, '-preset', 'slow',
                    '-movflags', '+faststart',
                    '-an',                       # no audio track at all
                    dest], check=True)
    subprocess.run([exe, '-y', '-loglevel', 'error', '-i', src,
                    '-vf', 'scale=%d:-2' % VIDEO_W, '-frames:v', '1',
                    '-q:v', '4', poster], check=True)


# -------------------------------------------------------------------- main ---
def main():
    # Rebuilt from scratch every run. Without this, deleting an original leaves
    # its web copy behind and the numbering of everything after it shifts onto
    # stale files.
    if os.path.isdir(OUT):
        for f in os.listdir(OUT):
            p = os.path.join(OUT, f)
            if os.path.isfile(p):
                os.remove(p)
    os.makedirs(OUT, exist_ok=True)

    # Whatever single image sits in `profile photo/` is the portrait — the file
    # name is not fixed, so renaming or replacing it needs no code change.
    pics = sorted(f for f in os.listdir(PROFILE_DIR)
                  if os.path.splitext(f)[1].lower() in IMG_EXT) \
        if os.path.isdir(PROFILE_DIR) else []
    if len(pics) > 1:
        out.write('profile: %d images in "profile photo/", using %s\n'
                  % (len(pics), pics[0]))
    if pics:
        src = os.path.join(PROFILE_DIR, pics[0])
        im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        l, t, r, b = PROFILE_CROP
        im = im.crop((int(im.width * l), int(im.height * t),
                      int(im.width * r), int(im.height * b)))
        if im.width > 1000:
            im = im.resize((1000, int(im.height * 1000.0 / im.width)), Image.LANCZOS)
        im.save(PROFILE_OUT, 'JPEG', quality=86, optimize=True, progressive=True)
        out.write('profile: %s  %dx%d  aspect %.2f  %.0f KB\n'
                  % (os.path.relpath(PROFILE_OUT, ROOT), im.width, im.height,
                     im.width / float(im.height),
                     os.path.getsize(PROFILE_OUT) / 1024.0))

    events, skipped = [], []
    for folder in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, folder)
        if not os.path.isdir(d) or folder == 'web':
            continue
        names = sorted(n for n in os.listdir(d)
                       if os.path.splitext(n)[1].lower() in IMG_EXT | VID_EXT)
        caps = parse_captions(os.path.join(d, 'caption.txt'), len(names))
        pre = slug(folder, 28)
        items = []
        for i, name in enumerate(names):
            ext = os.path.splitext(name)[1].lower()
            base = '%s-%d' % (pre, i + 1)
            src = os.path.join(d, name)
            caption, alt = caps[i]
            try:
                if ext in VID_EXT:
                    dest = os.path.join(OUT, base + '.mp4')
                    poster = os.path.join(OUT, base + '.jpg')
                    write_video(src, dest, poster)
                    with Image.open(poster) as pim:
                        psize = pim.size
                    items.append({'src': 'Photos/web/' + base + '.mp4',
                                  'poster': 'Photos/web/' + base + '.jpg',
                                  'video': True, 'caption': caption, 'alt': alt,
                                  'focus': focus_for(poster, psize), 'event': folder,
                                  'orig': name})
                else:
                    dest = os.path.join(OUT, base + '.jpg')
                    size = write_image(src, dest)
                    items.append({'src': 'Photos/web/' + base + '.jpg',
                                  'video': False, 'caption': caption, 'alt': alt,
                                  'focus': focus_for(dest, size), 'event': folder,
                                  'orig': name})
            except Exception as e:
                skipped.append('%s/%s  (%s)' % (folder, name, e))
        if items:
            events.append((folder, items))

    # Events sorted by EVENT_ORDER; anything unlisted keeps alphabetical order
    # behind the listed ones.
    def rank(folder):
        return EVENT_ORDER.index(folder) if folder in EVENT_ORDER else len(EVENT_ORDER)

    events.sort(key=lambda e: (rank(e[0]), e[0]))

    # Each event's chosen lead shot moves to the front of its pool.
    pools = []
    for folder, items in events:
        pool = list(items)
        want = LEAD.get(folder)
        if want:
            for k, m in enumerate(pool):
                if m['orig'] == want:
                    pool.insert(0, pool.pop(k))
                    break
            else:
                out.write('  LEAD not found: %s / %s\n' % (folder, want))
        pools.append(pool)

    # First pass: the opening run of the carousel is one slide from each event,
    # in EVENT_ORDER — its best shot first.
    order, last = [], -1
    for i, pool in enumerate(pools):
        if pool:
            order.append(pool.pop(0))
            last = i

    # Then keep interleaving: take from whichever event has the most left,
    # never the one just used, so no two neighbouring slides share an occasion
    # and a large folder is spread out rather than dumped at the end.
    while any(pools):
        cand = [i for i, p in enumerate(pools) if p and i != last]
        if not cand:
            cand = [i for i, p in enumerate(pools) if p]
        pick = max(cand, key=lambda i: len(pools[i]))
        order.append(pools[pick].pop(0))
        last = pick

    out.write('\nevents: %d | media: %d | skipped: %d\n'
              % (len(events), len(order), len(skipped)))
    for folder, items in events:
        out.write('  %-34s %d\n' % (folder[:34], len(items)))
    for s in skipped:
        out.write('  SKIPPED %s\n' % s)

    missing = [m['src'] for m in order if not m['caption'] or not m['alt']]
    out.write('entries missing caption or alt: %d\n' % len(missing))

    def js(v):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'

    focused = [m for m in order if m['focus']]
    out.write('entries given a focal point: %d of %d\n' % (len(focused), len(order)))
    for m in focused:
        out.write('  %-42s %s\n' % (m['src'].replace('Photos/web/', ''), m['focus']))

    rows = []
    for m in order:
        row = '    { src: %s,' % js(m['src'])
        if m['video']:
            row += ' video: true, poster: %s,' % js(m['poster'])
        if m['focus']:
            row += '\n      focus: %s,' % js(m['focus'])
        row += '\n      alt: %s,' % js(m['alt'])
        row += '\n      caption: %s }' % js(m['caption'])
        rows.append(row)
    io.open(os.path.join(ROOT, 'tools', '_gallery.txt'), 'w',
            encoding='utf-8', newline='\n').write(',\n'.join(rows))
    out.write('wrote tools/_gallery.txt\n')

    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    out.write('Photos/web total: %.1f MB\n' % (total / 1048576.0))
    out.flush()


main()
