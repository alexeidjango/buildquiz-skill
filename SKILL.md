---
name: buildquiz
description: Build a phone practice quiz (exam, test, school learning quiz; "kviz", "kolokvijum") from a folder of course materials (slides, old answer keys, scanned or photographed pages, docx/pptx), covering everything or only chosen topics, then check it, verify every answer independently and publish it as a private artifact. Screens in English, Serbian (Latin or Cyrillic) or Russian, switchable on the page. Also rebuilds an existing quiz with the latest engine. Use for /buildquiz, or when the user asks for a quiz, test, "kviz" or "kolokvijum" from sources.
---

# /buildquiz

Turns a folder of course materials into one verified, offline, single-file quiz that the user runs on a
phone as a private artifact. Every quiz uses the same engine in `engine/` (next to this file): template,
builder, checker, source reader, picture tool, render check and screen language files. Only the sources
and the scope change.

Examples:

    /buildquiz take sources from networks/K2 and build a quiz about everything
    /buildquiz sources in english/test2, only topics "passive voice" and "reported speech"
    /buildquiz rebuild networks/quiz-k2

All commands below run from the project root (the folder that holds `.claude/`). `E` stands for
`.claude/skills/buildquiz/engine`. Nothing is installed and nothing goes to the network (see "Network").
Write quiz files (`quiz.toml`, `terms.py`, `bank_*.py`) with the Write tool, never through shell heredocs:
the shell eats the backslashes in regexes. In `quiz.toml`, regexes go in single quotes
(`citation = 'стр\. \d+'`).

## Source rules (binding)

- **Slides** (lecture decks, photographed slides, handouts, the textbook for school quizzes) are the only
  source of truth. Every correct and every wrong option is justified from them, and every `why` cites the
  place, e.g. `P3, sl. 26` for slides, `стр. 51` / `p. 51` for book pages.
- **Keys** (old student question-and-answer lists) decide which questions get asked and how they are
  worded, never the answers. Where a key disagrees with the slides, the slide wins; the `note` may say the
  old key gives a different answer. Every in-scope key question enters the bank once (duplicates merged).
- **Key questions whose topic is not in the slides** enter the bank with `off_source=True` (tagged "not on
  the slides" in the screen language, or the quiz's `off_source_label`). Their answer comes from general
  knowledge, or from public sources only if the user allows a search in this conversation.
- **Reference material** (posters, notes, mock tests, book review questions) can supply questions and
  detail; the slides override it.
- **One quiz covers one exam.** Material for another exam stays out, even in the same folder.
- **Out of scope:** a question whose answer can only be confirmed by running code is not written; tell the
  user. Showing a snippet whose answer is stated on a slide is fine (the `code` field).

## Layout

    <subject>/<sources>/              what the user points at (e.g. networks/K2, biology/book)
    <subject>/<sources>/_text/        extracted text, one .txt per source (+ _pages/ page images,
                                      OVERVIEW.md for photographed pages); shared by every quiz from them
    <subject>/quiz-<slug>/            one folder per quiz:
      quiz.toml                       settings (annotated example: reference/quiz.toml.example)
      bank.py                         exactly: from bank_api import Bank; B = Bank(); Q = B.q; BANK = B.questions
      bank_<area>.py                  one per area letter, lowercase (bank_k.py); starts `from bank import Q`
      terms.py                        coverage terms, grouped by area: TERMS = {"K": {"name": r"regex"}, ...}
      items.py                        optional: ITEMS = {"K12": "K", "O53-2": "J"}  (book/key item -> area)
      images/<id>.jpg, images_<A>.json  pictures and how each was made
      <output>.html                   the built quiz (the file that is published)

A question: `Q("K", "text", [(correct, why), ...], [(wrong, why), ...], note=, items=("K12",), off_source=, code=, img=)`.
Correct options first; more than one correct = multi-answer (scored all-or-nothing). Ids are assigned
per area in file order (K001, K002, ...).

## Pipeline

### 1. Parse the request
Source folder(s), scope (everything / topic list), and which exam if given. A missing or ambiguous source
folder is the only reason to stop and ask before reading. "rebuild <quiz folder>" goes to **Rebuild**.

### 2. Read the sources
Run `python E/read_sources.py <sources>`. It writes `_text/<file name>.txt`, e.g. `_text/IMG_8149.JPG.txt`,
with subfolders mirrored (PDF per page `=== pN`, pptx per slide `=== sN`, docx, txt/md) and skips files
whose .txt is newer than the source, so transcriptions survive reruns. It ignores folders starting with
`.` or `_` and quiz folders. Every `READ <txt> <- <image>` line is a page Claude must read; every `ERROR`
line must be resolved or reported.

**Needs reading** (scans, photos, picture-only slides). For each `READ` line, replace the
`[TO READ: ...]` placeholder in that .txt with a transcription in the format of `reference/transcription.md`
(page number, heading, main text with `**bold**`, side boxes and margin notes, handwriting
`[HANDWRITTEN: ...]`, figures and labels, questions, notes). Use the preview `<x>.jpg` for layout and the
full-resolution halves `<x>_a.jpg` / `<x>_b.jpg` for small text. Never guess: unreadable words become
`[illegible]`. More than about 5 pages: parallel subagents with 5 pages each, given the
`reference/transcription.md` prompt. No Anthropic API; reading happens in this session.

For photographed pages also write `_text/OVERVIEW.md`: a table of page number, photo, lesson; then
missing pages, duplicate shots and blurry photos replaced by better ones. A description of a diagram's
arrows or structure is checked against the full-resolution image before any question relies on it.

**HEIC:** if `read_sources.py` reports `HEIC NOT CONVERTED`, tell the user. The fallback is `pillow-heif`
from PyPI, which needs the user's explicit permission first.

**Photographed books:** stop once here, before the checkpoint: list the topics found (lessons, page
ranges), gaps and practical tasks, and let the user choose the topics. Then continue with step 3.

### 3. Checkpoint with the user (one message, the only stop before the bank)
Show:
- a table of the sources and the role of each (slides / key / reference / not used, and why);
- `_text/OVERVIEW.md` for photographed pages: page order, gaps, duplicates; which gaps to skip;
- the scope mapped to concrete decks and slide ranges or book pages;
- who the quiz is for and their level (the user at university, or their child and the grade): this sets
  the wording of questions and explanations;
- exam quiz or learning quiz. Exam: the format (number of questions, pass mark, time) taken from the
  slides with the slide cited, otherwise proposed with "please confirm". Learning: no pass mark; the third
  mode is the knowledge check, with a score and a message;
- the default screen language: English / Srpski (latinica) / Српски (ћирилица) / Русский, or any other
  file in `engine/lang/`; the others stay selectable on the page (`language`). Propose the user's own
  language;
- the questions' language and script (`content_language`, from the sources), and whether the Cyrillic-only
  check applies (`cyrillic_only = true` for Cyrillic sources);
- for a book or other non-slide source: the tag for off-source questions (`off_source_label`, e.g.
  „ван ових страна“ / "not in these pages"), since the default tag says "not on the slides";
- the areas (2 to 7, one uppercase ASCII letter each, with a label) and the simulation (N random
  questions, or a fixed mix per area); for an exam a cap on the bank size if wanted;
- the quiz folder (`<subject>/quiz-<slug>`) and title.

Once confirmed, write the short design note `plans/<subject>/YYYY-MM-DD-quiz-<slug>.md` from
`reference/quiz-design-note.md`, create the quiz folder with `quiz.toml` and `bank.py`, and continue without
further stops.

### 4. Coverage terms and book items
- `terms.py`: every claim in the in-scope sources becomes a term with a regex that must match a question
  text or a correct option. When transcriptions mark bold words, start from
  `python E/read_sources.py <sources> --terms` (stem regexes, so inflected forms match), group the terms by
  area and trim them by hand.
- `items.py`: every question-like item in scope with its area: old key questions (`K12`), book review
  questions (`O53-2`), exercises, test tasks (`T73-6`). Each must be covered by a question's `items=(...)`.

### 5. Write the bank
One writer subagent per area, in parallel, with the prompt in `reference/area-writer.md` (filled in
for the area: letter, pages, files, book items, reader, target count). Each writes only its own
`bank_<area>.py`, makes its own pictures, and runs `python E/check.py <quiz> --area <A>` until it
exits 0. `--area` imports only that area's file, so other writers' half-written files cannot break it.
For a small bank (under ~60 questions) write it yourself.

Rules for every question:
- one `why` per option, 1-2 sentences for the agreed reader, citing the source so it matches `citation`;
- wrong options plausible and taken from neighbouring content; never "all of the above" / "none of the
  above" (in any language), double negatives, or wording that gives the answer away;
- exactly one defensible answer set; multi-answer only where natural (at most ~15 %);
- every fact once; counts may exceed the estimate (a 7th-grade biology book: 279 vs ~185), fine for a
  learning quiz;
- with `cyrillic_only`, no Latin letters in visible text (allowed exceptions go in `latin_allowed`).

Pictures (`img`): `python E/pictures.py <quiz> <A_id> <source-image> x0 y0 x1 y1 [--mask x0,y0,x1,y1,N]... [--number x,y,N]...`
- coordinates are in the page preview from `_text/_pages/<page>.jpg`; the source image is the original
  photo (for a PDF page: `_pages/<page>_pN.png`; for HEIC: `_pages/<stem>_heic.jpg`);
- crop without the caption; cover every printed label that names an answer (`--mask`) and ask "What is
  marked with number N?" or "What is shown in the picture?" in the content language;
- use the book's empty numbered circles (`--number`) only where each arrow's target is unambiguous;
- open every output picture and check it; the call is recorded in `images_<A>.json`.

### 6. Mechanical check
`python E/check.py <quiz>` must exit 0: integrity (3-7 options, no duplicates, at least one right and one
wrong, no empty why, no repeated question+picture), citations, pictures present, script, every term
covered, every book/key item covered, simulation not larger than the bank.

### 7. Independent verification
One reviewer subagent per area (two small areas may share one) with `reference/answer-review.md`.
Reviewers read only `_text/`, the pictures and the original page images, and edit nothing. Send each
finding list to that area's writer (SendMessage, so it keeps its context); it applies the fixes and
reruns `check.py --area <A>`. Decide disputed findings yourself against the source. Then rerun the
full `check.py`.

### 8. Build and render check
`python E/build.py <quiz>` writes `<quiz>/<output>`. Then `python E/render_check.py <quiz>/<output>` must
exit 0: it plays every mode headless (with and without localStorage), checks a picture renders, and
switches through every screen language.

### 9. Publish
New quiz: follow the Artifact tool's own instructions for a new page (its `quickstart` / design guidance),
then publish `<quiz>/<output>` as a new private artifact with an `icon` (e.g. "quiz") and a one-line
`description`, and write the returned URL into `artifact` in `quiz.toml`.
Rebuild: first `read` the stored `artifact` URL with the Artifact tool (it refuses a publish to a URL this
conversation has not read), then publish `<quiz>/<output>` with `url` set to it, so the phone link keeps
working. Never publish over another quiz's URL.

### 10. Report
Questions per area and in total, pictures, everything marked `off_source`, `[illegible]` places,
key/slide disagreements, judgment calls the user may want to check, and the link.

## Rebuild

"/buildquiz rebuild <quiz folder>": skip steps 1-5; run `check.py`, `build.py`, `render_check.py`, then
publish to the URL in `quiz.toml` (step 9). This is how engine fixes reach a quiz. Pictures can be
regenerated with `python E/pictures.py <quiz> --rebuild`.

Question ids are positions within an area (K001, K002, ...), and the phone keeps progress by id. If a
question was added, deleted or moved since the last publish, bump `storage_key` (e.g. `-v1` → `-v2`)
before building, so old progress is not attached to the wrong questions. Fixing a question's text in
place needs no bump.

## Screen languages

Screen texts (buttons, modes, results) live in `engine/lang/<code>.json`, one file per language; every
page carries all of them and remembers the phone's choice. Questions, explanations and area labels stay
in the content language. To add a language, copy `en.json`, translate it and run the engine tests (see
README).

## Network

Web searches (e.g. checking an `off_source` answer against public documentation) only with the user's
explicit permission in this conversation, and only the query leaves the machine. Publishing the artifact
is the normal end of the pipeline.
