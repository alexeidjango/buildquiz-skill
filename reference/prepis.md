# Transcription prompt (photographed or scanned pages)

Give one subagent about 5 pages. Fill in the `<...>` parts. The headings below are Cyrillic for a Cyrillic
book; for a Latin source use GLAVNI TEKST, BOČNI OKVIRI I BELEŠKE NA MARGINAMA, SLIKE I OZNAKE,
PITANJA I ZADACI, NAPOMENE, [RUKOM: ...], [nečitko], [SUSEDNA STRANA].

---

Transcribe photographed <textbook / slide> pages exactly. The source is <a Serbian (Cyrillic) school biology
textbook>. A study quiz will be built from your transcription, so completeness and accuracy matter more
than speed.

Your pages (copy them from the `ČITAJ <txt> <- <image>` lines of citaj.py):
<for each page: the .txt file, e.g. ...\_tekst\IMG_8149.JPG.txt, and its preview, e.g. ...\_tekst\_slike\IMG_8149.jpg>
Each `[ZA ČITANJE: ...]` placeholder in a .txt names three upright images (paths relative to `_tekst\`):
- the preview (whole page, downscaled, e.g. IMG_8149.jpg or `<pdf name>_p7.jpg`): use it for layout and order;
- `..._a.jpg` (top 55 %, full resolution) and `..._b.jpg` (bottom 55 %, full resolution; overlaps the top):
  use these to read the text, small labels and margins precisely.
Read all three for every page with the Read tool. (Pages of one scanned PDF share one .txt: one helper
gets all of them, so two helpers never edit the same file.)

Replace each page's `[ZA ČITANJE: ...]` line in its .txt (UTF-8) with the transcription below, keeping
everything else in the file (e.g. the `=== pN` markers of a PDF):

    === <photo or page name, e.g. IMG_8149> | страна <printed page number, or ? if not visible>
    НАСЛОВ/ЛЕКЦИЈА: <lesson or section heading(s) on this page, if any>
    --- ГЛАВНИ ТЕКСТ
    <the main body text, verbatim, in reading order, keeping the original spelling; mark words printed in
    bold as **word**; keep paragraph breaks; join words hyphenated across lines>
    --- БОЧНИ ОКВИРИ И БЕЛЕШКЕ НА МАРГИНАМА
    <every box, side column, margin note, "занимљивост", "домаћи задатак", true/false exercise,
    definition box, etc., verbatim, each prefixed with a short label of what it is and where (e.g.
    [оквир десно горе], [маргина лево]). Include any HANDWRITTEN notes, underlining, ticks or highlights by a
    student, clearly marked [РУКОМ: ...].>
    --- СЛИКЕ И ОЗНАКЕ
    <for each figure: its caption verbatim, all labels on it verbatim, and one short line describing what it
    shows. For a diagram with arrows, say exactly where each arrow starts and ends, checked on the
    full-resolution half.>
    --- ПИТАЊА И ЗАДАЦИ
    <any questions/exercises/review items, verbatim (if not already above)>
    --- НАПОМЕНЕ
    <anything uncertain; text from the neighbouring page visible at the edge of the photo (say which edge,
    and transcribe only if it is substantially readable, marked [СУСЕДНА СТРАНА])>

Rules:
- Never guess. A word you cannot read becomes [нечитко]; a partially read word gets [?] after it.
- Do not translate, summarize or correct anything. Verbatim only.
- Do not edit or create any other files. Do not modify images.
- When done, reply with one line per page: X -> page number, lesson heading, and a count of [нечитко] marks.
