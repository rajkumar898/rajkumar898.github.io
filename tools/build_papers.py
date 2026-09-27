# -*- coding: utf-8 -*-
"""Build the publication figures and award certificates from Published Paper PDFs/.

Every paper in `Published Paper PDFs/` ships a `.png` of its methodology
diagram next to the PDF. This resizes those into `assets/` under the names
SITE.publications already uses, and copies the award certificates into
`assets/awards/`.

    python tools/build_papers.py

Originals are never touched. The mapping below is the only thing to edit when
a paper is added: give it a SITE id and name its files.
"""
import io, os, shutil, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Published Paper PDFs')
JOURNALS = os.path.join(SRC, 'published journal papers')
CONFS = os.path.join(SRC, 'published conference papers')
ASSETS = os.path.join(ROOT, 'assets')
AWARDS = os.path.join(ASSETS, 'awards')

FIG_EDGE = 1600      # opened full-size in the lightbox; 1600 is plenty
CERT_EDGE = 1600

out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# SITE id -> (folder, stem shared by the .pdf and the .png)
PAPERS = [
    ('j1', JOURNALS, '1. Hybrid_Framework_Combining_Diffusion-Based_Image_Augmentation_and_Feature_Level_SMOTE_for_Addressing_Extreme_Class_Imbalance_IEEEAccess'),
    ('j2', JOURNALS, '2. Mitigating dataset imbalance using image-based diffusion and feature-level SMOTE for solar panel classification with CNNs_EnergyReports'),
    ('j3', JOURNALS, '3. Multi-tier data augmentation and balancing framework integrating diffusion tomeklink and SMOTE DiToS for robust image-based fault detection in solar panels_SETA'),
    ('j4', JOURNALS, '4. Fungal Blast Disease Detection in Rice Seed Using Machine Learning'),
    ('c1', CONFS, '1. Hybrid Approach to Mitigate Extreme Class Imbalance using Stable Diffusion and SMOTE'),
    ('c2', CONFS, '2. Image-Level Generative Oversampling and Boundary-Based Cleaning for Solar Panel Fault Detection'),
    ('c3', CONFS, '3. LLM-Augmented Multimodal Approach to Reliable Solar Energy Forecasting'),
    ('c4', CONFS, '4. Multimodal Cross-Site Solar Energy Forecasting Using Large Language Model'),
    ('c5', CONFS, '5. Robust Cross-Site Solar Power Forecasting via Semantic Operational Feature Integration Under LOSO'),
]

# SITE id -> (certificate file in the conference folder, published name)
CERTIFICATES = [
    ('c2', CONFS, '2. Best Paper Award.pdf', 'adintech-2025-best-paper.pdf'),
    ('c3', CONFS, '3. Best Paper Presentation Award.jpeg', 'iccc-2025-best-presentation.jpg'),
    ('c4', CONFS, '4. Best Paper Award.pdf', 'icobar-smart-2026-best-paper.pdf'),
]


def shrink(src, dest, edge, quality=None):
    im = Image.open(src)
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA')
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')
    w, h = im.size
    if max(w, h) > edge:
        f = edge / float(max(w, h))
        im = im.resize((max(1, int(w * f)), max(1, int(h * f))), Image.LANCZOS)
    if dest.lower().endswith('.png'):
        # Diagrams are flat-coloured line art with text; a 256-colour palette
        # keeps the lettering crisp at a fraction of the size a JPEG would
        # need to avoid ringing around the strokes.
        im.quantize(colors=256, method=Image.MEDIANCUT).save(dest, 'PNG', optimize=True)
    else:
        im.save(dest, 'JPEG', quality=quality or 85, optimize=True, progressive=True)
    return im.size


def main():
    os.makedirs(AWARDS, exist_ok=True)
    missing = []

    out.write('figures\n')
    for pid, folder, stem in PAPERS:
        png = os.path.join(folder, stem + '.png')
        pdf = os.path.join(folder, stem + '.pdf')
        if not os.path.isfile(pdf):
            missing.append('PDF  ' + stem)
        if not os.path.isfile(png):
            missing.append('FIG  ' + stem)
            continue
        dest = os.path.join(ASSETS, 'pub-%s.png' % pid)
        before = os.path.getsize(png) / 1024.0
        w, h = shrink(png, dest, FIG_EDGE)
        out.write('  %-4s %4dx%-4d %7.0f KB -> %6.0f KB\n'
                  % (pid, w, h, before, os.path.getsize(dest) / 1024.0))

    out.write('\ncertificates\n')
    for pid, folder, name, published in CERTIFICATES:
        src = os.path.join(folder, name)
        dest = os.path.join(AWARDS, published)
        if not os.path.isfile(src):
            missing.append('CERT ' + name)
            continue
        if published.lower().endswith('.pdf'):
            shutil.copyfile(src, dest)
            out.write('  %-4s %-40s %6.0f KB (copied)\n'
                      % (pid, published, os.path.getsize(dest) / 1024.0))
        else:
            w, h = shrink(src, dest, CERT_EDGE, quality=82)
            out.write('  %-4s %-40s %6.0f KB (%dx%d)\n'
                      % (pid, published, os.path.getsize(dest) / 1024.0, w, h))

    out.write('\nPDF paths for SITE.publications[].links.pdf\n')
    for pid, folder, stem in PAPERS:
        rel = os.path.relpath(os.path.join(folder, stem + '.pdf'), ROOT).replace('\\', '/')
        out.write('  %-4s %s\n' % (pid, rel))

    if missing:
        out.write('\nMISSING\n')
        for m in missing:
            out.write('  %s\n' % m)
    else:
        out.write('\nnothing missing\n')
    out.flush()


main()
