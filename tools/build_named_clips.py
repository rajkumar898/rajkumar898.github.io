# -*- coding: utf-8 -*-
"""Web-size the clips a project shows under its own labels, into assets/video/.

tools/build_project_demos.py handles the one-clip-per-project case, where the
folder name is enough to pick the file. This one is for a project that shows
several clips side by side and needs each mapped to a specific published name.

    python tools/build_named_clips.py

720p H.264, CRF 28, AAC 96k, +faststart, plus a poster frame. These keep their
audio and narration, so they are never set to autoplay. Originals are never
touched.
"""
import io, os, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'projects')
OUT = os.path.join(ROOT, 'assets', 'video')

HEIGHT = 720
CRF = '28'
AUDIO_KBPS = '96k'

out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# (published basename, folder under projects/, a fragment of the source name,
#  and optionally a CRF for that clip — lower is better quality, bigger file)
CLIPS = [
    ('sas-explainer',
     'Scientific Animation Studio — Turning Research into Faithful Explainer Videos',
     'physics-informed-solar-forecasting-demo'),
    ('sas-story',
     'Scientific Animation Studio — Turning Research into Faithful Explainer Videos',
     'llm-augmented-solar-power-forecasting'),
    ('pi-solar-lab',
     'PI-Solar LAB — An Interactive Dashboard for Physics-Informed Probabilistic Solar Forecasting',
     'PI-Solar', '26'),
]


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    os.makedirs(OUT, exist_ok=True)
    exe = ffmpeg()
    missing = []

    for entry in CLIPS:
        name, folder, fragment = entry[:3]
        crf = entry[3] if len(entry) > 3 else CRF
        d = os.path.join(SRC, folder)
        if not os.path.isdir(d):
            missing.append('folder: ' + folder)
            continue
        hits = [f for f in sorted(os.listdir(d))
                if fragment.lower() in f.lower()
                and os.path.splitext(f)[1].lower() == '.mp4']
        if not hits:
            missing.append('no file matching %r in %s' % (fragment, folder))
            continue
        if len(hits) > 1:
            out.write('  %s: %d matches, using %s\n' % (name, len(hits), hits[0]))

        src = os.path.join(d, hits[0])
        mp4 = os.path.join(OUT, name + '.mp4')
        jpg = os.path.join(OUT, name + '.jpg')

        subprocess.run([exe, '-y', '-loglevel', 'error', '-i', src,
                        '-vf', 'scale=-2:%d' % HEIGHT,
                        '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p',
                        '-crf', crf, '-preset', 'slow',
                        '-movflags', '+faststart',
                        '-c:a', 'aac', '-b:a', AUDIO_KBPS, '-ac', '2',
                        mp4], check=True)
        # A frame a few seconds in, past any title card.
        subprocess.run([exe, '-y', '-loglevel', 'error', '-ss', '5', '-i', src,
                        '-vf', 'scale=-2:%d' % HEIGHT, '-frames:v', '1',
                        '-q:v', '4', jpg], check=True)

        with Image.open(jpg) as im:
            size = im.size
        out.write('%-16s %-44s CRF %-3s %6.1f MB -> %5.2f MB   poster %dx%d (%.0f KB)\n'
                  % (name, hits[0][:44], crf,
                     os.path.getsize(src) / 1048576.0,
                     os.path.getsize(mp4) / 1048576.0,
                     size[0], size[1], os.path.getsize(jpg) / 1024.0))

    if missing:
        out.write('\nMISSING\n')
        for m in missing:
            out.write('  %s\n' % m)
    out.flush()


main()
