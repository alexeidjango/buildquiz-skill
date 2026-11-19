# Per-quiz design note template

Save as `plans/<subject>/YYYY-MM-DD-kviz-<slug>.md` right after the checkpoint is confirmed. Write it in
English (project rule); quote Serbian names as they appear. Keep it short: it records what was agreed.

---

# <Subject>: quiz for <exam / learning goal>

Agreed in conversation on <date>. <Exam: date, form (e.g. live on mTutor), N questions, time, pass mark,
with the slide that states it — or "learning quiz, no exam">. Reader: <the user / their child, grade>.
Built with /buildquiz (engine in `.claude/skills/buildquiz/engine`).

## Sources
- <file or deck>: <role: slides / key / reference / not used>, <why>, <what it covers>.
- `_tekst/PREGLED.md`: <page order, gaps skipped by the user, replaced photos> (photographed pages only).

## Scope
<decks and slide ranges / book pages>; left out: <what and why (other exam, practical tasks, ...)>.

## Rules for answers
- Slides/book are the only source of truth; keys give the questions, not the answers.
- Key/slide disagreements: <the known ones>; the slide wins and the note says so.
- Off-source (`van`) questions: <which, roughly how many>; answered from <general knowledge / public
  sources, if the user allowed a search on <date>>.
- Citation format: <`P3, sl. N` / `стр. N`>; `izvor = '<regex>'`.

## Coverage
- `termini.py`: <how the terms were made, e.g. from bold words + slide claims>, about <N> terms.
- `kljuc.py`: <key questions / review questions / test tasks>, about <N> items.
- Expected bank size: about <N> questions (may grow: every fact once).

## Areas and simulation
<letter: label (pages)>, ... Simulation: <broj N | sastav {...}>, <prolaz P | learning check>.
Script: <lat / cyr>. Quiz folder: `<subject>/kviz-<slug>`, output `<izlaz>`.

## Steps
1. Sources read (`citaj.py`, transcriptions), checkpoint confirmed.
2. `termini.py`, `kljuc.py`; area writers in parallel (`provera.py --oblast X`).
3. Independent review per area, fixes, full `provera.py`.
4. `izgradi.py`, `pregled.py`, publish as a private artifact; URL in `kviz.toml`.
