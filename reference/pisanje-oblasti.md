# Area writer prompt (step 5)

One subagent per area, all started in parallel. Fill in every `<...>`. `E` =
`<project root>\.claude\skills\buildquiz\engine`. Keep the Cyrillic examples for a Cyrillic quiz; for a
Latin quiz use the Latin forms ("Šta je označeno brojem 3?", "P3, sl. 26").

---

You are writing part of a phone study quiz for <reader: e.g. a 7th-grade child in Serbia / a university
student>, from <source: the biology textbook / the course slides>. Everything the reader sees is in
<Serbian CYRILLIC / Serbian Latin>, in <the book's own simple wording / the slides' terminology>.

YOUR AREA: <A> = "<area label>", <pages / slide ranges>.
Sources (the ONLY source of truth): <list of _tekst .txt files with their page/slide numbers>. Read them
fully first. Page images (upright previews): <_tekst\_slike\X.jpg ...> (plus X_a/X_b full-resolution
top/bottom halves for detail; for PDF pages the original is X.png).

Quiz folder: <project root>\<subject>\kviz-<slug>\
- banka.py: do not edit. Questions are written as
  `Q("<A>", "question", [(correct, why), ...], [(wrong, why), ...], note=None, kljuc=(), van=False, code=None, img=None)`
  (keyword arguments after the two lists). Correct options first; more than one = multi-answer.
- YOU WRITE ONLY banka_<a>.py. It starts with `from banka import Q`. Every question uses "<A>".
- Pictures: `python E\slike.py <quiz folder> <A>_<name> <source image> x0 y0 x1 y1 [--maska x0,y0,x1,y1,N]... [--broj x,y,N]...`
  (run with no arguments for help). Ids MUST start with "<A>_" and be ASCII lowercase (e.g. <A>_paramecijum).
  Coordinates are in the preview X.jpg; the source image is the original <photo / X.png>.
- kljuc.py: book/key items you must cover: <ids>. Tag questions with kljuc=("<id>",).
- termini.py: the terms in the "<A>" block must each appear in a question text or a correct option.
- Check: `python E\provera.py <quiz folder> --oblast <A>` must exit 0 at the end (no GREŠKA lines).
  Other helpers write the other areas' files at the same time; --oblast never imports them, so their
  half-written files cannot break your check.
Do NOT edit any other file. If a tool seems broken, say so in your report instead of changing it.

WHAT TO WRITE (aim for about <N> questions; more is fine if every fact needs it):
- Cover every fact in your sources: main text, every side box, figure content, tables, and every review
  question / key question / exercise listed above (turn each into one or more multiple-choice questions).
- Mostly ONE correct answer out of 4 options. Several correct answers only where natural, max ~15 %.
- Wrong options: plausible, taken from neighbouring material, never silly, never „све наведено“ /
  „ништа од наведеног“, no double negatives, no wording that gives the answer away. Exactly one defensible
  answer set: if a wrong option could be argued correct, change it.
- Every option's why: 1-2 short sentences <the reader> understands, and it MUST cite the source as
  <„стр. N“ / "P3, sl. N"> (e.g. „Тачно: парамецијум има две контрактилне вакуоле које раде наизменично (стр. 51).“).
  For wrong options say briefly why not / what it actually is.
- Off-source questions (van=True) only for <key questions whose topic is not in the sources / nothing>.
- <area-specific notes: homework that needs internet research, tables to turn into questions, etc.>

PICTURES (about <M> questions with pictures):
- Labelled diagrams: crop the drawing WITHOUT the caption, cover every printed label with a number
  (--maska over the label text, number N). Then ask „Шта је на слици означено бројем 3?“ (options = other
  structures from the same drawing). Reuse one picture id for several questions.
- The book's EMPTY numbered circles: write numbers with --broj ONLY where you can see unambiguously which
  structure each circle's arrow points to (look at the full-resolution halves). If you cannot tell for a
  circle, leave it empty and don't ask about it.
- Photos of objects or organisms: crop WITHOUT the caption (it gives the answer away) and ask
  „Шта је приказано на слици?“ or a question about what is shown.
- After EVERY slike.py call, open the output image (Read tool) and check: the crop is right, no caption or
  label text giving away the answer remains visible, numbers sit on the right labels. Fix and rerun.

WORKFLOW: read sources → plan the question list → make pictures → write banka_<a>.py →
`provera.py --oblast <A>` → fix until exit 0 → re-read every question once against the source for
correctness and ambiguity.

REPORT (short): number of questions, pictures made (ids and what they show), anything you skipped and why,
any place where the source is unclear.
