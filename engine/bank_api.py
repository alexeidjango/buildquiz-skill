"""Question schema shared by every quiz bank.

A question is {id, area, q, opts: [{t, why}], ok: [indices], multi, note?, off_source?, code?, img?, items?}.
A quiz's bank.py does:  from bank_api import Bank; B = Bank(); Q = B.q; BANK = B.questions
"""


class Bank:
    def __init__(self):
        self.questions: list[dict] = []
        self._counter: dict[str, int] = {}

    def q(self, area: str, text: str, correct: list[tuple[str, str]], wrong: list[tuple[str, str]], *,
          note: str | None = None, items: tuple[str | int, ...] = (), off_source: bool = False,
          code: str | None = None, img: str | None = None) -> dict:
        """correct and wrong are lists of (option text, why). Correct options come first; more than one = multi."""
        self._counter[area] = self._counter.get(area, 0) + 1
        opts = [{"t": t, "why": w} for t, w in (*correct, *wrong)]
        p = {"id": f"{area}{self._counter[area]:03d}", "area": area, "q": text, "opts": opts,
             "ok": list(range(len(correct))), "multi": len(correct) > 1}
        if note:
            p["note"] = note
        if items:
            p["items"] = list(items)
        if off_source:
            p["off_source"] = True
        if code is not None:
            p["code"] = code
        if img:
            p["img"] = img
        self.questions.append(p)
        return p


def normalize(p: dict) -> dict:
    """Copy of p with ok as a list of indices and multi set from it (some hand-built banks store ok as an int)."""
    p = dict(p)
    ok = p["ok"]
    p["ok"] = [ok] if isinstance(ok, int) else list(ok)
    p["multi"] = len(p["ok"]) > 1
    return p
