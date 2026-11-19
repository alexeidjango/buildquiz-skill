# /buildquiz: study quizzes from course materials, for Claude Code

A Claude Code skill that turns a folder of course materials (lecture slides, old answer keys, scanned or
photographed book pages, Word and PowerPoint files) into a practice quiz you run on your phone. Claude
reads the sources, agrees the scope with you once, writes the questions with an explanation and a source
citation for every option, checks them mechanically and with independent reviewers, and publishes the quiz
as a private Claude artifact (one offline HTML page).

The quiz has three modes: **Uči** (learn: every question, explanation right after each), **Ponovi greške**
(only questions answered wrong or not yet done), and either **Simulacija** (an exam simulation with a pass
mark) or **Provera znanja** (a knowledge check with a score, for school learning). It supports one or more
correct answers, pictures cut from the pages (with labels replaced by numbers), code snippets, an area
filter, light and dark themes, and Serbian Latin or Cyrillic screens. Progress stays on the phone.

## Requirements

- Claude Code, with the Artifact tool (to publish the quiz).
- Windows with Microsoft Edge (the render check runs the quiz headless in Edge; HEIC photos are converted
  with the built-in Windows imaging component).
- Python 3.11 or newer with `pdfplumber` and `Pillow`; `pytest` to run the engine tests.

## Install

Clone this repo into your project's skills folder and start a new Claude Code session there:

    cd <your project>
    git clone https://github.com/alexeidjango/buildquiz-skill .claude/skills/buildquiz

Type `/` in Claude Code and check that `buildquiz` is in the list. A skill added during a session appears
only after a restart.

## Operator guide: making a quiz

### 1. Put the sources in one folder

One folder per exam (or per book chapter range), anywhere in the project, e.g. `zastitamreza/K2/`:

- lecture slides (PDF or pptx), in subfolders if you like;
- old answer keys (docx, PDF): they decide which questions get asked, never the answers;
- photos of book pages or slides (jpg, png, HEIC straight from the iPhone), scans (PDF without text);
- anything else useful (posters, notes, mock tests).

Material for a different exam may sit in the same folder; you will say what belongs in this quiz.

### 2. Ask for the quiz

    /buildquiz take sources from zastitamreza/K2 and build a quiz about everything
    /buildquiz sources in english/klk2, only topics "passive voice" and "reported speech"
    /buildquiz biologija/biologija: a quiz for my child (7th grade), lessons 1 and 3

Say which exam it is for, if the folder holds more than one, and for whom the quiz is if it is not you.

### 3. Answer the questions Claude asks

Claude reads everything first (photos and picture-only slides are read page by page, which takes a while
for a big pile). Then:

- **Photographed books only:** you get a list of the lessons and pages found, gaps and duplicates, and you
  choose the topics.
- **The checkpoint (always, once):** a table of the sources and what each is used for, the scope mapped to
  slides or pages, the exam format (number of questions, pass mark; taken from the slides or proposed), or a
  learning quiz without a pass mark, the reader (you, or a child and the grade), Latin or Cyrillic, the
  areas (topic groups) and the simulation, and the quiz folder name. Correct anything, then confirm.

After you confirm, Claude runs to the end without stopping: writes the questions (several areas in
parallel), checks them, has every answer verified by an independent reviewer against the sources, builds
the page, plays it headless, and publishes it.

### 4. Get the result

The final message gives the link, the number of questions per area, questions marked "van slajdova"
(asked by an old key but not covered by the slides, answered from general knowledge), unreadable places in
the sources, disagreements between keys and slides, and judgment calls worth a look.

On the iPhone: open the link, then Share → Add to Home Screen. Progress is kept on that device only.

### More quizzes from the same sources

Ask again with a different scope ("only Firewall", "only K2 topics"). Each quiz gets its own folder; the
text already read from the sources (in `<sources>/_tekst/`) is reused, so nothing is read twice.

### Fixing a question or updating a quiz

Tell Claude what is wrong ("question K014 has the wrong answer, slide 26 says …"). It edits the question
file and republishes with:

    /buildquiz rebuild zastitamreza/kviz-k2

A rebuild keeps the same link, so the phone shortcut keeps working. Rebuilds also bring engine
improvements to old quizzes.

### Good to know

- Slides (or the textbook) are the only source of truth for answers. Old keys only supply questions.
- Claude makes no internet searches unless you allow it in that conversation (e.g. to check
  "van slajdova" answers against public documentation).
- A question whose answer can only be checked by running code is not written; you are told instead.
- HEIC photos that Windows cannot convert are reported. The fallback (the `pillow-heif` package) is
  installed only with your permission.
- Each quiz folder holds `kviz.toml` (settings), `banka_<area>.py` (questions), `termini.py` (terms that
  must be covered), optional `kljuc.py` (key and book items that must be covered), `slike/` (pictures) and
  the built HTML. `reference/kviz.toml.primer` explains every setting.

## How it works

`SKILL.md` is the pipeline Claude follows. `engine/` holds the tools it runs:

| Tool | Does |
|---|---|
| `citaj.py <sources>` | extracts text into `_tekst/` (PDF, docx, pptx, txt/md), prepares photos and scans for reading (upright preview + full-resolution halves), converts HEIC; never overwrites a transcription |
| `citaj.py <sources> --termini` | a first list of coverage terms from **bold** words in transcriptions |
| `slike.py <quiz> <id> <image> x0 y0 x1 y1 [--maska ...] [--broj ...]` | cuts a picture from a page and covers labels with numbers; `--obnovi` rebuilds all pictures |
| `provera.py <quiz> [--oblast X]` | checks the bank: integrity, citations, pictures, script, coverage, simulation size |
| `izgradi.py <quiz>` | builds the single-file quiz from `sablon.html` |
| `pregled.py <built.html>` | plays every mode in headless Edge (with and without storage, no network) |

`reference/` holds the prompts for page transcription, area writers and answer reviewers, the per-quiz
design note template, and the annotated settings example.

Run the engine tests from the project root:

    python -m pytest .claude/skills/buildquiz/engine/tests -q

A few acceptance tests build the author's own existing quizzes and are skipped when those folders are absent.

## License

MIT, see `LICENSE`.
