# rajkumar898.github.io

Personal academic website for **Raj Kumar** — Research Scholar, Machine
Learning Lab, Jeju National University.

A single self-contained page. No build step, no framework, no npm. Open
`index.html` in a browser and it works; push it to GitHub and it is live.

```
D:\Personal WebPage
├── index.html              ← THE SITE. Markup, CSS, content and rendering, in one file.
├── README.md               ← you are here
│
├── assets/                 paper figures (pub-*.png), favicon, CV PDF
├── logos/                  institution logos used by Experience and Education
├── Photos/                 one folder per event, each with a caption.txt;
│                        Photos/web/ holds the generated web copies
├── Published Paper PDFs/   the PDFs linked from each publication
│
├── profile photo/          the original portrait; the tool resizes it
│
├── tools/
│   ├── build_media.py      builds Photos/web/ and assets/profile.jpg
│   ├── sync_gallery.py     pastes the generated gallery array into index.html
│   └── build_papers.py     builds assets/pub-*.png and assets/awards/
│
└── Updated_version/        a parked multi-page rebuild — see its own README
```

---

## How the content works

**All content lives in one JavaScript object called `SITE`**, near the bottom of
`index.html` inside the `<script>` block. The body is an empty shell; every
heading, card and link is rendered from `SITE` when the page loads.

- To change anything on the page, edit `SITE`. Never edit the HTML body.
- Sections with no data are **omitted entirely** — no empty headings, no
  "coming soon".
- Fields set to `"TODO"` render as muted placeholder text, and a URL set to
  `"TODO"` is not rendered at all, so the page never ships a dead link.

| Key | What it holds |
|---|---|
| `meta` | Page title, description, canonical URL, OG image |
| `profile` | Name, role, bio, portrait, location, name aliases, interest pills |
| `actions` | Hero buttons — first renders filled, the rest outlined |
| `news` | Dated one-line updates, newest first |
| `photos` | Fallback hero slideshow — empty; the hero shows `profile.photo` |
| `galleryPhotos` | The Photos carousel beside News — generated, see below |
| `threads` | Research themes; publications attach to them by `id` |
| `publications` | Published and accepted work only |
| `underReview` | Submitted work, rendered as a separate labelled block |
| `experience`, `education` | Roles and degrees, newest first |
| `contact` | Email, location, note, social channels |
| `nav` | Which sections appear and in what order |

The `<meta>` tags in `<head>` are duplicated as literal HTML on purpose: link
scrapers do not run JavaScript, so an OG tag generated from `SITE` would
produce a blank preview. The script overwrites them at runtime, but if you
change your **name, headline or site URL**, update both places.

---

## Adding a publication

One object in `SITE.publications`, newest first:

```js
{
  id: "j5",                          // stable slug -> #pub-j5 anchor
  type: "journal",                   // "journal" | "conference" | "dataset"
  thread: "multimodal",              // an id from SITE.threads, or ""
  title: "…",
  authors: ["Raj Kumar", "Yong-Woon Kim", "Yung-Cheol Byun"],  // published order
  venue: "IEEE Access",
  year: "2026",
  tldr: "One plain sentence on what the paper does.",
  abstract: "The published abstract, verbatim.",
  thumb: "assets/pub-j5.png",        // 800×800 square; "" for a placeholder
  thumbAlt: "What the figure shows",
  links: { doi: "https://doi.org/…", pdf: "Published Paper PDFs/….pdf" }
}
```

The filter chips recount themselves and the paper is listed under its thread
automatically.

**Three rules the template is built around:**

1. **Published or accepted only** in `publications`. Submitted work goes in
   `underReview`, and **do not name the target venue** there — a named venue on
   an unaccepted paper reads as a claim of acceptance. The renderer refuses to
   print one even if you set it.
2. **Author order exactly as published.** Never reorder to put yourself first,
   never truncate to "et al.". Your name is bolded automatically via
   `profile.nameAliases`.
3. **TL;DRs describe the paper, not you.** "Combines X and Y to do Z", never
   "I built".

### Adding a paper

Drop the PDF into `Published Paper PDFs/published journal papers/` or
`.../published conference papers/`, numbered like the others, and put a PNG of
its **methodology diagram** beside it under exactly the same name. If it won an
award, put the certificate in the conference folder as `<n>. Best Paper Award.pdf`
(or `.jpeg`). Then add the paper to the `PAPERS` list at the top of
`tools/build_papers.py`, giving it a SITE id, and run:

```bash
python tools/build_papers.py
```

It resizes each diagram into `assets/pub-<id>.png`, copies the certificates into
`assets/awards/`, prints the PDF paths to paste into `SITE.publications`, and
lists anything it could not find. Originals are never touched.

Then add the entry to `SITE.publications`. `links` takes `pdf`, `doi` and
`award`; the award renders as a badge rather than a file link. If the
certificate says something other than "Best Paper Award", put the exact wording
in `awardLabel` on the entry — the badge uses it verbatim.

`abstract` is optional; where it is set, the card grows a **Show Abstract**
toggle. The four journal abstracts on the page were extracted from the PDFs
themselves and are the authors' own text.

### Adding photos and videos

One folder per event under `Photos/`. Drop the originals in, add a
`caption.txt` beside them, then:

```bash
python tools/build_media.py    # writes Photos/web/ and tools/_gallery.txt
python tools/sync_gallery.py   # pastes that array into index.html
```

`caption.txt` looks like this:

```
caption: Presenting "…" — ICCC 2025, Taipei, December 2025
alt: Raj Kumar gesturing toward a slide showing the proposed architecture
```

`caption` is the line shown over the photo. `alt` is what is *in* the picture —
screen readers read it aloud, so describe the scene, not the occasion. Where one
folder needs more than one caption, address them by position:

```
For images 1 and 2:
caption: …
alt: …

For images 3-5:
caption: …
alt: …
```

Position means alphabetical order within the folder, which is the order the tool
prints when it runs.

The tool writes 1400px, quality-82 JPGs into `Photos/web/`, resizes
`profile photo/*.png` into `assets/profile.jpg`, and prints the finished
`galleryPhotos` array to `tools/_gallery.txt` — paste that into `index.html`.
Originals are never touched.

**Videos** are welcome. They are re-encoded to 1024px H.264 with `-an`, which
strips the audio track out of the file entirely, and play muted, looped and
inline on the page. A clip is held on screen for 9 seconds instead of the usual
4.5. **HEIC** is handled too (`pillow-heif`), so iPhone photos need no
conversion.

The tool needs `pillow`, `pillow-heif` and `imageio-ffmpeg`:

```bash
python -m pip install pillow pillow-heif imageio-ffmpeg
```

**Slide order** is set by two lists at the top of `tools/build_media.py`:

- `EVENT_ORDER` — which events open the carousel. One slide is taken from each,
  in that order, before anything repeats. Folders not listed follow behind.
- `LEAD` — which shot leads each event, named by the **original** file, so it
  survives adding or removing other photos in the folder.

After that first run through, the rest is interleaved — the event with the most
photos left goes next, never the one just used — so two shots of the same
occasion never sit next to each other and a big folder is spread out instead of
dumped at the end.

**A word of warning about `caption.txt` ranges.** "For images 3-5" counts
positions in alphabetical order within the folder. Add or delete one file and
every position after it shifts, so re-check the ranges whenever you change a
folder that uses more than one caption block. The tool prints
`entries missing caption or alt` — if that is not `0`, a range has fallen short.

---

## What still needs you

- **`assets/Raj-Kumar-CV.pdf`** does not exist — the Download CV button links to
  a file that is not there. Export `Raj Kumar Updated CV.docx` to PDF under
  that exact name. This is the only broken link on the page.
- **The patent entry is all `TODO`.** Title, year, application number, office
  and TL;DR are placeholders in `SITE.patents` — nothing about it was invented.
- **`assets/og-image.png`** does not exist, so a pasted link previews without a
  picture.
- Six of eight publications have `thread: ""`, so they collect under
  "Other Work" and two of the three research threads show no papers.
- Two lines are my wording, not yours, and are marked `NEW COPY` in the file:
  the quotes beside the Education and Awards headings.

---

## Deploying to GitHub Pages

This is a **user site**, served from the repository root at
`https://rajkumar898.github.io/`.

The repo must be named **`rajkumar898.github.io`** — your username, lowercase,
then `.github.io` — and must be **public** on a free account.

This folder is **not yet a git repository**:

```bash
git init
git branch -M main
git add .
git commit -m "Initial site"
git remote add origin https://github.com/rajkumar898/rajkumar898.github.io.git
git push -u origin main
```

Then repo → **Settings** → **Pages** → Source **Deploy from a branch**,
Branch **main**, folder **/ (root)** → Save. The first build takes 1–3 minutes.

Afterwards: `git add . && git commit -m "…" && git push`. There is no build
step, so what you commit is what goes live.

**Before the first push**, consider what you are committing.
`Published Paper PDFs/` is ~64 MB, of which `Merged_Publications.pdf` (23 MB)
and `Merged_Publications_compressed.pdf` are **not linked from the site**.
`Photos/` originals (~90 MB, including two phone videos) are unused once
`Photos/web/` exists — but they are also the only copies of the captions, so
keep the folder if you may re-run the tool. `.gitignore` already excludes
`.venv/`.

### Custom domain, later

Four `A` records for the apex domain → `185.199.108.153`, `185.199.109.153`,
`185.199.110.153`, `185.199.111.153`, plus a `CNAME` for `www` →
`rajkumar898.github.io`. Set it in Settings → Pages, wait for the DNS check,
tick **Enforce HTTPS**, then update `SITE.meta.url` and the `og:url` /
`canonical` tags in `<head>`.

---

## Working locally

Open `index.html` directly, or for something closer to production:

```bash
python -m http.server 8000
# http://localhost:8000
```

Before pushing: narrow the window to ~360px and check nothing scrolls
sideways; toggle light/dark and reload to confirm it persists; tab through with
the keyboard and check every control takes a visible focus ring; search
`index.html` for `TODO`.

---

## The parked multi-page version

`Updated_version/` holds a complete multi-page rebuild — separate pages for
Research, Publications, Projects, Experience, Education, Timeline, CV, Contact
and Blog, generated from content files by a Python script. It is **not** part
of the live site and nothing at the root depends on it.

See `Updated_version/README.md` for what it is and how to bring it back.
