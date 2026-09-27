# -*- coding: utf-8 -*-
"""Paste tools/_gallery.txt into SITE.galleryPhotos in index.html.

Run it straight after tools/build_media.py:

    python tools/build_media.py
    python tools/sync_gallery.py

It replaces everything between `galleryPhotos: [` and its closing `],` and
touches nothing else, so it is safe to run as often as you like. The comment
block above the array — which explains the fields — is left alone.
"""
import io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
ARRAY = os.path.join(ROOT, 'tools', '_gallery.txt')

out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

rows = io.open(ARRAY, encoding='utf-8').read().rstrip('\n')
s = io.open(PAGE, encoding='utf-8').read()

start = s.index('  galleryPhotos: [')
end = s.index('\n  ],\n', start) + len('\n  ],\n')
before = s[start:end].count('src: "')

s = s[:start] + '  galleryPhotos: [\n' + rows + '\n  ],\n' + s[end:]
io.open(PAGE, 'w', encoding='utf-8', newline='').write(s)

out.write('galleryPhotos: %d entries -> %d\n' % (before, rows.count('src: "')))
out.flush()
