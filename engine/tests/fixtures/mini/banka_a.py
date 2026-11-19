from banka import Q

Q("A", "Koje su boje zastave?",
  [("crvena", "P1, sl. 2: crvena je na zastavi."), ("plava", "P1, sl. 2: plava je na zastavi.")],
  [("zelena", "P1, sl. 2: zelene nema."), ("ljubičasta", "P1, sl. 2: ljubičaste nema.")],
  kljuc=("O1",))
Q("A", "Šta je prikazano na slici?",
  [("crveni pravougaonik", "P1, sl. 3: slika je crveni pravougaonik.")],
  [("plavi krug", "P1, sl. 3: nije krug."), ("zeleni trougao", "P1, sl. 3: nije trougao.")],
  img="A_slika")
