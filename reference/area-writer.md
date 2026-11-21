# Area writer prompt (step 5)

One subagent per area, all started in parallel. Fill in every `<...>`. `E` =
`<project root>\.claude\skills\buildquiz\engine`. The examples below show a Serbian Cyrillic book quiz and a
Serbian Latin slides quiz; write the questions in the quiz's content language.

---

You are writing part of a phone study quiz for <reader: e.g. a 7th-grade child in Serbia / a university
student>, from <source: the biology textbook / the course slides>. Everything the reader sees in the
questions is in <content language and script, e.g. Serbian CYRILLIC / Serbian Latin / English>, in <the
book's own simple wording / the slides' terminology>.

YOUR AREA: <A> = "<area label>", <pages / slide ranges>.
Sources (the ONLY source of truth): <list of _text .txt files with their page/slide numbers>. Read them
fully first. Page images (upright previews): <_text\_pages\X.jpg ...> (plus X_a/X_b full-resolution
top/bottom halves for detail; for PDF pages the original is X.png).

Quiz folder: <project root>\<subject>\quiz-<slug>\
- bank.py: do not edit. Questions are written as
  `Q("<A>", "question", [(correct, why), ...], [(wrong, why), ...], note=None, items=(), off_source=False, code=None, img=None)`
  (keyword arguments after the two lists). Correct options first; more than one = multi-answer.
- YOU WRITE ONLY bank_<a>.py. It starts with `from bank import Q`. Every question uses "<A>".
- Pictures: `python E\pictures.py <quiz folder> <A>_<name> <source image> x0 y0 x1 y1 [--mask x0,y0,x1,y1,N]... [--number x,y,N]...`
  (run with no arguments for help). Ids MUST start with "<A>_" and be ASCII lowercase (e.g. <A>_paramecium).
  Coordinates are in the preview X.jpg; the source image is the original <photo / X.png>.
- items.py: book/key items you must cover: <ids>. Tag questions with items=("<id>",).
- terms.py: the terms in the "<A>" block must each appear in a question text or a correct option.
- Check: `python E\check.py <quiz folder> --area <A>` must exit 0 at the end (no ERROR lines).
  Other helpers write the other areas' files at the same time; --area never imports them, so their
  half-written files cannot break your check.
Do NOT edit any other file. If a tool seems broken, say so in your report instead of changing it.

WHAT TO WRITE (aim for about <N> questions; more is fine if every fact needs it):
- Cover every fact in your sources: main text, every side box, figure content, tables, and every review
  question / key question / exercise listed above (turn each into one or more multiple-choice questions).
- Mostly ONE correct answer out of 4 options. Several correct answers only where natural, max ~15 %.
- Wrong options: plausible, taken from neighbouring material, never silly, never "all of the above" /
  "none of the above" (in any language: „све наведено“, „ништа од наведеног“), no double negatives, no
  wording that gives the answer away. Exactly one defensible answer set: if a wrong option could be argued
  correct, change it.
- Every option's why: 1-2 short sentences <the reader> understands, and it MUST cite the source as
  <„стр. N“ / "P3, sl. N" / "p. N"> (e.g. „Тачно: парамецијум има две контрактилне вакуоле које раде
  наизменично (стр. 51).“). For wrong options say briefly why not / what it actually is.
- Off-source questions (off_source=True) only for <key questions whose topic is not in the sources / nothing>.
- <area-specific notes: homework that needs internet research, tables to turn into questions, etc.>

PICTURES (about <M> questions with pictures):
- Labelled diagrams: crop the drawing WITHOUT the caption, cover every printed label with a number
  (--mask over the label text, number N). Then ask "What is marked with number 3?" in the content
  language (e.g. „Шта је на слици означено бројем 3?“, "Šta je označeno brojem 3?"), with options = other
  structures from the same drawing. Reuse one picture id for several questions.
- The book's EMPTY numbered circles: write numbers with --number ONLY where you can see unambiguously which
  structure each circle's arrow points to (look at the full-resolution halves). If you cannot tell for a
  circle, leave it empty and don't ask about it.
- Photos of objects or organisms: crop WITHOUT the caption (it gives the answer away) and ask "What is
  shown in the picture?" (e.g. „Шта је приказано на слици?“) or a question about what is shown.
- After EVERY pictures.py call, open the output image (Read tool) and check: the crop is right, no caption
  or label text giving away the answer remains visible, numbers sit on the right labels. Fix and rerun.

WORKFLOW: read sources → plan the question list → make pictures → write bank_<a>.py →
`check.py --area <A>` → fix until exit 0 → re-read every question once against the source for
correctness and ambiguity.

REPORT (short): number of questions, pictures made (ids and what they show), anything you skipped and why,
any place where the source is unclear.
