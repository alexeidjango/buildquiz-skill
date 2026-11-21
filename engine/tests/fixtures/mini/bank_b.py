from bank import Q

Q("B", "Koliko je x posle ove naredbe?",
  [("1", "Dodela upisuje 1 u x.")],
  [("0", "Dodela menja vrednost."), ("x", "Vrednost je broj, ne ime.")],
  off_source=True, code="x = 1")
Q("B", "Glavni grad Srbije je:",
  [("Beograd", "P1, sl. 5: Beograd.")],
  [("Novi Sad", "P1, sl. 5: Novi Sad nije glavni grad."), ("Niš", "P1, sl. 5: Niš nije glavni grad.")],
  note="Pitanje iz geografije.")
