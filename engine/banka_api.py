"""Question schema shared by every quiz bank.

A question is {id, g, q, opts: [{t, why}], ok: [indices], multi, note?, van?, code?, img?, kljuc?}.
A quiz's banka.py does:  from banka_api import Banka; B = Banka(); Q = B.q; BANKA = B.pitanja
"""


class Banka:
    def __init__(self):
        self.pitanja: list[dict] = []
        self._brojac: dict[str, int] = {}

    def q(self, g: str, q: str, tacni: list[tuple[str, str]], pogresni: list[tuple[str, str]], *,
          note: str | None = None, kljuc: tuple[str | int, ...] = (), van: bool = False,
          code: str | None = None, img: str | None = None) -> dict:
        """tacni and pogresni are lists of (text, why). Correct options come first; more than one = multi."""
        self._brojac[g] = self._brojac.get(g, 0) + 1
        opts = [{"t": t, "why": w} for t, w in (*tacni, *pogresni)]
        p = {"id": f"{g}{self._brojac[g]:03d}", "g": g, "q": q, "opts": opts,
             "ok": list(range(len(tacni))), "multi": len(tacni) > 1}
        if note:
            p["note"] = note
        if kljuc:
            p["kljuc"] = list(kljuc)
        if van:
            p["van"] = True
        if code is not None:
            p["code"] = code
        if img:
            p["img"] = img
        self.pitanja.append(p)
        return p


def normalize(p: dict) -> dict:
    """Copy of p with ok as a list of indices and multi set from it (English/Verovatnoća store ok as an int)."""
    p = dict(p)
    ok = p["ok"]
    p["ok"] = [ok] if isinstance(ok, int) else list(ok)
    p["multi"] = len(p["ok"]) > 1
    return p
