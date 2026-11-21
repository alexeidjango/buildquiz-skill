# Per-quiz design note template

Save as `plans/<subject>/YYYY-MM-DD-quiz-<slug>.md` right after the checkpoint is confirmed. Write it in
English; quote names in the sources' language as they appear. Keep it short: it records what was agreed.

---

# <Subject>: quiz for <exam / learning goal>

Agreed in conversation on <date>. <Exam: date, form (e.g. live on an online platform), N questions, time,
pass mark, with the slide that states it — or "learning quiz, no exam">. Reader: <the user / their child,
grade>. Built with /buildquiz (engine in `.claude/skills/buildquiz/engine`).

## Sources
- <file or deck>: <role: slides / key / reference / not used>, <why>, <what it covers>.
- `_text/OVERVIEW.md`: <page order, gaps skipped by the user, replaced photos> (photographed pages only).

## Scope
<decks and slide ranges / book pages>; left out: <what and why (other exam, practical tasks, ...)>.

## Rules for answers
- Slides/book are the only source of truth; keys give the questions, not the answers.
- Key/slide disagreements: <the known ones>; the slide wins and the note says so.
- Off-source questions: <which, roughly how many>; answered from <general knowledge / public sources, if
  the user allowed a search on <date>>.
- Citation format: <`P3, sl. N` / `стр. N` / `p. N`>; `citation = '<regex>'`.

## Coverage
- `terms.py`: <how the terms were made, e.g. from bold words + slide claims>, about <N> terms.
- `items.py`: <key questions / review questions / test tasks>, about <N> items.
- Expected bank size: about <N> questions (may grow: every fact once).

## Areas and simulation
<letter: label (pages)>, ... Simulation: <count N | mix {...}>, <pass_mark P | knowledge check>.
Screen language (default): <en / sr-Latn / sr-Cyrl / ru>; content language: <...>; cyrillic_only: <yes/no>.
Quiz folder: `<subject>/quiz-<slug>`, output `<output>`.

## Steps
1. Sources read (`read_sources.py`, transcriptions), checkpoint confirmed.
2. `terms.py`, `items.py`; area writers in parallel (`check.py --area X`).
3. Independent review per area, fixes, full `check.py`.
4. `build.py`, `render_check.py`, publish as a private artifact; URL in `quiz.toml`.
