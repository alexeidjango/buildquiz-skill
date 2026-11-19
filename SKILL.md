---
name: buildquiz
description: Build a phone practice quiz (kolokvijum, exam, or a school learning quiz) from a folder of course materials (slides, old answer keys, scanned or photographed pages, docx/pptx), covering everything or only chosen topics, then check it, verify every answer independently and publish it as a private artifact. Also rebuilds an existing quiz with the latest engine. Use for /buildquiz, or when the user asks for a "kviz", "quiz" or "kolokvijum" from sources.
---

# /buildquiz

Turns a folder of course materials into one verified, offline, single-file quiz that the user runs on an
iPhone as a private artifact. Every quiz uses the same engine in `engine/` (next to this file): template,
builder, checker, source reader, picture tool and render check. Only the sources and the scope change.

Examples:

    /buildquiz take sources from zastitamreza/K2 and build a quiz about everything
    /buildquiz sources in english/klk2, only topics "passive voice" and "reported speech"
    /buildquiz rebuild zastitamreza/kviz-k2

All commands below run from the project root (the folder that holds `.claude/`). `E` stands for `.claude/skills/buildquiz/engine`.
Nothing is installed and nothing goes to the network (see "Network"). Write quiz files (`kviz.toml`,
`termini.py`, `banka_*.py`) with the Write tool, never through shell heredocs: the shell eats the
backslashes in regexes. In `kviz.toml`, regexes go in single quotes (`izvor = 'стр\. \d+'`).

## Source rules (binding)

- **Slides** (lecture decks, photographed slides, handouts, the textbook for school quizzes) are the only
  source of truth. Every correct and every wrong option is justified from them, and every `why` cites the
  place: `P3, sl. 26` for slides, `стр. 51` / `str. 51` for book pages.
- **Keys** (old student question-and-answer lists) decide which questions get asked and how they are
  worded, never the answers. Where a key disagrees with the slides, the slide wins; the `note` may say the
  old key gives a different answer. Every in-scope key question enters the bank once (duplicates merged).
- **Key questions whose topic is not in the slides** enter the bank with `van=True` (shown as
  "van slajdova" / „ван ових страна“). Their answer comes from general knowledge, or from public sources
  only if the user allows a search in this conversation.
- **Reference material** (posters, notes, mock tests, book review questions) can supply questions and
  detail; the slides override it.
- **One quiz covers one exam.** Material for another kolokvijum stays out, even in the same folder.
- **Out of scope:** a question whose answer can only be confirmed by running code is not written; tell the
  user. Code quizzes (like Verovatnoća) are built by hand. Showing a snippet whose answer is stated on a
  slide is fine (the `code` field).

## Layout

    <subject>/<sources>/              what the user points at (e.g. zastitamreza/K2, biologija/biologija)
    <subject>/<sources>/_tekst/       extracted text, one .txt per source (+ _slike/ page images,
                                      PREGLED.md for photographed pages); shared by every quiz from them
    <subject>/kviz-<slug>/            one folder per quiz:
      kviz.toml                       settings (annotated example: reference/kviz.toml.primer)
      banka.py                        exactly: from banka_api import Banka; B = Banka(); Q = B.q; BANKA = B.pitanja
      banka_<area>.py                 one per area letter, lowercase (banka_k.py); starts `from banka import Q`
      termini.py                      coverage terms, grouped by area: TERMINI = {"K": {"name": r"regex"}, ...}
      kljuc.py                        optional: KLJUC = {"K12": "K", "O53-2": "J"}  (book/key item -> area)
      slike/<id>.jpg, slike_<A>.json  pictures and how each was made
      <izlaz>.html                    the built quiz (the file that is published)

A question: `Q("K", "text", [(correct, why), ...], [(wrong, why), ...], note=, kljuc=("K12",), van=, code=, img=)`.
Correct options first; more than one correct = multi-answer (scored all-or-nothing). Ids are assigned
per area in file order (K001, K002, ...).

## Pipeline

### 1. Parse the request
Source folder(s), scope (everything / topic list), and which exam if given. A missing or ambiguous source
folder is the only reason to stop and ask before reading. "rebuild <quiz folder>" goes to **Rebuild**.

### 2. Read the sources
Run `python E/citaj.py <sources>`. It writes `_tekst/<file name>.txt`, e.g. `_tekst/IMG_8149.JPG.txt`,
with subfolders mirrored (PDF per page `=== pN`, pptx per slide
`=== sN`, docx, txt/md) and skips files whose .txt is newer than the source, so transcriptions survive
reruns. It ignores folders starting with `.` or `_` and quiz folders. Every `ČITAJ <txt> <- <image>` line
is a page Claude must read; every `GREŠKA` line must be resolved or reported.

**Needs reading** (scans, photos, picture-only slides). For each `ČITAJ` line, replace the
`[ZA ČITANJE: ...]` placeholder in that .txt with a transcription in the format of `reference/prepis.md`
(page number, heading, main text with `**bold**`, side boxes and margin notes, handwriting `[РУКОМ: ...]` /
`[RUKOM: ...]`, figures and labels, questions, notes). Use the preview `<x>.jpg` for layout and the
full-resolution halves `<x>_a.jpg` / `<x>_b.jpg` for small text. Never guess: unreadable words become
`[nečitko]` / `[нечитко]`. More than about 5 pages: parallel subagents with 5 pages each, given the
`reference/prepis.md` prompt. No Anthropic API; reading happens in this session.

For photographed pages also write `_tekst/PREGLED.md`: a table of page number, photo, lesson; then
missing pages, duplicate shots and blurry photos replaced by better ones. A description of a diagram's
arrows or structure is checked against the full-resolution image before any question relies on it.

**HEIC:** if `citaj.py` reports `HEIC NIJE KONVERTOVAN`, tell the user. The fallback is `pillow-heif` from
PyPI, which needs the user's explicit permission first.

**Photographed books:** stop once here, before the checkpoint: list the topics found (lessons, page
ranges), gaps and practical tasks, and let the user choose the topics. Then continue with step 3.

### 3. Checkpoint with the user (one message, the only stop before the bank)
Show:
- a table of the sources and the role of each (slides / key / reference / not used, and why);
- `_tekst/PREGLED.md` for photographed pages: page order, gaps, duplicates; which gaps to skip;
- the scope mapped to concrete decks and slide ranges or book pages;
- who the quiz is for and their level (the user at university, or their child and the grade) — this sets
  the wording of questions and explanations;
- exam quiz or learning quiz. Exam: the format (number of questions, pass mark, time) taken from the
  slides with the slide cited, otherwise proposed with "please confirm". Learning: no pass mark; the third
  mode is „Провера знања“ / "Provera znanja" with a score and a message;
- script: Serbian Latin (`pismo = "lat"`, university courses so far) or Cyrillic (`"cyr"`, school);
- the areas (2 to 7, one uppercase ASCII letter each, with a label) and the simulation (N random
  questions, or a fixed mix per area); for an exam a cap on the bank size if wanted;
- the quiz folder (`<subject>/kviz-<slug>`) and title.

Once confirmed, write the short design note `plans/<subject>/YYYY-MM-DD-kviz-<slug>.md` from
`reference/dizajn-kviza.md`, create the quiz folder with `kviz.toml` and `banka.py`, and continue without
further stops.

### 4. Coverage terms and book items
- `termini.py`: every claim in the in-scope sources becomes a term with a regex that must match a question
  text or a correct option. When transcriptions mark bold words, start from
  `python E/citaj.py <sources> --termini` (stem regexes, so inflected forms match), group the terms by
  area and trim them by hand.
- `kljuc.py`: every question-like item in scope with its area: old key questions (`K12`), book review
  questions (`O53-2`), exercises, test tasks (`T73-6`). Each must be covered by a question's `kljuc=(...)`.

### 5. Write the bank
One writer subagent per area, in parallel, with the prompt in `reference/pisanje-oblasti.md` (filled in
for the area: letter, pages, files, book items, reader, target count). Each writes only its own
`banka_<area>.py`, makes its own pictures, and runs `python E/provera.py <quiz> --oblast <A>` until it
exits 0. `--oblast` imports only that area's file, so other writers' half-written files cannot break it.
For a small bank (under ~60 questions) write it yourself.

Rules for every question:
- one `why` per option, 1-2 sentences for the agreed reader, citing the source so it matches `izvor`;
- wrong options plausible and taken from neighbouring content; never "sve navedeno" / „све наведено“,
  "ništa od navedenog", double negatives, or wording that gives the answer away;
- exactly one defensible answer set; multi-answer only where natural (at most ~15 %);
- every fact once; counts may exceed the estimate (biologija: 279 vs ~185), fine for a learning quiz;
- a Cyrillic quiz has no Latin letters in visible text (allowed exceptions go in `latinica_dozvoljena`).

Pictures (`img`): `python E/slike.py <quiz> <A_id> <source-image> x0 y0 x1 y1 [--maska x0,y0,x1,y1,N]... [--broj x,y,N]...`
- coordinates are in the page preview from `_tekst/_slike/<page>.jpg`; the source image is the original
  photo (for a PDF page: `_slike/<page>_pN.png`; for HEIC: `_slike/<stem>_heic.jpg`);
- crop without the caption; cover every printed label that names an answer (`--maska`) and ask
  „Шта је означено бројем N?“ / "Šta je označeno brojem N?" or „Шта је приказано на слици?“;
- use the book's empty numbered circles (`--broj`) only where each arrow's target is unambiguous;
- open every output picture and check it; the call is recorded in `slike_<A>.json`.

### 6. Mechanical check
`python E/provera.py <quiz>` must exit 0: integrity (3-7 options, no duplicates, at least one right and one
wrong, no empty why, no repeated question+picture), citations, pictures present, script, every term
covered, every book/key item covered, simulation not larger than the bank.

### 7. Independent verification
One reviewer subagent per area (two small areas may share one) with `reference/provera-odgovora.md`.
Reviewers read only `_tekst/`, the pictures and the original page images, and edit nothing. Send each
finding list to that area's writer (SendMessage, so it keeps its context); it applies the fixes and
reruns `provera.py --oblast <A>`. Decide disputed findings yourself against the source. Then rerun the
full `provera.py`.

### 8. Build and render check
`python E/izgradi.py <quiz>` writes `<quiz>/<izlaz>`. Then `python E/pregled.py <quiz>/<izlaz>` must exit 0:
it plays every mode headless (with and without localStorage) and checks a picture renders.

### 9. Publish
New quiz: follow the Artifact tool's own instructions for a new page (its `quickstart` / design guidance),
then publish `<quiz>/<izlaz>` as a new private artifact with an `icon` (e.g. "quiz") and a one-line
`description`, and write the returned URL into `artifact` in `kviz.toml`.
Rebuild: first `read` the stored `artifact` URL with the Artifact tool (it refuses a publish to a URL this
conversation has not read), then publish `<quiz>/<izlaz>` with `url` set to it, so the iPhone link keeps
working. Never publish over another quiz's URL.

### 10. Report
Questions per area and in total, pictures, everything marked `van`, `[nečitko]` places, key/slide
disagreements, judgment calls the user may want to check, and the link.

## Rebuild

"/buildquiz rebuild <quiz folder>": skip steps 1-5; run `provera.py`, `izgradi.py`, `pregled.py`, then
publish to the URL in `kviz.toml` (step 9). This is how engine fixes reach a quiz. Pictures can be
regenerated with `python E/slike.py <quiz> --obnovi`.

Question ids are positions within an area (K001, K002, ...), and the phone keeps progress by id. If a
question was added, deleted or moved since the last publish, bump `kljuc_skladista` (e.g. `-v1` → `-v2`)
before building, so old progress is not attached to the wrong questions. Fixing a question's text in
place needs no bump.

## Network

Web searches (e.g. checking a `van` answer against public documentation) only with the user's explicit
permission in this conversation, and only the query leaves the machine. Publishing the artifact is the
normal end of the pipeline.
