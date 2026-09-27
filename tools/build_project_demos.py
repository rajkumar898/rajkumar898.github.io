# -*- coding: utf-8 -*-
"""Web-size the project demo videos in projects/ into assets/demos/.

One folder per project under `projects/`, holding its screen recording. The
originals are 100–200 MB each, which no one on a phone is going to download, so
this writes a 1280px H.264 copy plus a poster frame.

Unlike the photo carousel clips, these KEEP THEIR AUDIO — a demo with narration
is worth hearing — so they are never set to autoplay. They sit behind a poster
with ordinary controls, and nothing plays until the visitor presses play.

    python tools/build_project_demos.py

Originals are never touched. Add a project by adding a line to DEMOS.
"""
import io, os, subprocess, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'projects')
OUT = os.path.join(ROOT, 'assets', 'demos')

WIDTH = 1280
CRF = '28'
AUDIO_KBPS = '96k'

out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# SITE.projects id -> the folder under projects/
DEMOS = [
    ('lora-agentic-ai-lab-member', 'Lora — An Agentic AI Member for the Research Lab'),
    ('ai-harness-discord', 'AI Harness — Supervised Multi-Agent Orchestration on Discord'),
    ('cited-research-assistant', 'Cited Research Assistant — A Hands-On AI System using Meta Muse Spark'),
    ('labreviewer', 'LabReviewer — An AI First Reviewer for Weekly Lab Meetings'),
    ('cross-model-review-team', 'Cross-Model Review Team — Claude Code and Codex as Teammates in Buzz'),
]

VID_EXT = {'.mp4', '.mov', '.m4v', '.webm'}


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    os.makedirs(OUT, exist_ok=True)
    exe = ffmpeg()
    missing = []

    for pid, folder in DEMOS:
        d = os.path.join(SRC, folder)
        if not os.path.isdir(d):
            missing.append('folder: ' + folder)
            continue
        vids = sorted(f for f in os.listdir(d)
                      if os.path.splitext(f)[1].lower() in VID_EXT)
        if not vids:
            missing.append('video in: ' + folder)
            continue
        if len(vids) > 1:
            out.write('  %s: %d videos, using %s\n' % (pid, len(vids), vids[0]))

        src = os.path.join(d, vids[0])
        mp4 = os.path.join(OUT, pid + '.mp4')
        jpg = os.path.join(OUT, pid + '.jpg')

        subprocess.run([exe, '-y', '-loglevel', 'error', '-i', src,
                        '-vf', 'scale=%d:-2' % WIDTH,
                        '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p',
                        '-crf', CRF, '-preset', 'slow',
                        '-movflags', '+faststart',
                        '-c:a', 'aac', '-b:a', AUDIO_KBPS, '-ac', '2',
                        mp4], check=True)
        # A frame a few seconds in, so the poster is not a title card or black.
        subprocess.run([exe, '-y', '-loglevel', 'error', '-ss', '3', '-i', src,
                        '-vf', 'scale=%d:-2' % WIDTH, '-frames:v', '1',
                        '-q:v', '4', jpg], check=True)

        with Image.open(jpg) as im:
            size = im.size
        out.write('%-32s %6.1f MB -> %5.1f MB  poster %dx%d\n'
                  % (pid, os.path.getsize(src) / 1048576.0,
                     os.path.getsize(mp4) / 1048576.0, size[0], size[1]))

    if missing:
        out.write('\nMISSING\n')
        for m in missing:
            out.write('  %s\n' % m)

    other = [f for f in sorted(os.listdir(SRC))
             if os.path.isdir(os.path.join(SRC, f))
             and f not in [d[1] for d in DEMOS]]
    if other:
        out.write('\nfolders in projects/ with no DEMOS entry yet:\n')
        for f in other:
            out.write('  %s\n' % f)
    out.flush()


main()
