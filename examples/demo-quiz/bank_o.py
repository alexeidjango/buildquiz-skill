from bank import Q

Q("O", "How long does Earth take to orbit the Sun once?",
  [("About 365.25 days", "One orbit of the Sun is a year, about 365.25 days (notes §7).")],
  [("About 24 hours", "24 hours is one turn on Earth's axis, a day (notes §7)."),
   ("About 27.3 days", "27.3 days is how long the Moon takes to orbit Earth (notes §6)."),
   ("About 29.5 days", "29.5 days is the cycle of the Moon's phases (notes §6).")])

Q("O", "What causes the seasons on Earth?",
  [("The tilt of Earth's axis", "The seasons come from the tilt of Earth's axis, about 23.4° (notes §7).")],
  [("Earth's changing distance from the Sun", "The notes say explicitly that distance is not the cause (notes §7)."),
   ("The phases of the Moon", "The phases are about the Moon's light, not Earth's seasons (notes §6, §7)."),
   ("The Sun's rings", "The Sun has no rings (notes §9); the seasons come from the tilt (notes §7).")])

Q("O", "What shape are the planets' orbits around the Sun?",
  [("Ellipses", "Planets move around the Sun in ellipses (notes §8).")],
  [("Perfect circles", "The orbits are ellipses (notes §8)."),
   ("Spirals toward the Sun", "The planets keep moving in ellipses (notes §8)."),
   ("Figure-eights", "The orbits are ellipses (notes §8).")])

Q("O", "Which planet has the longest year?",
  [("Neptune", "Neptune is the farthest planet; its year is about 165 Earth years (notes §2, §8).")],
  [("Mercury", "Mercury has the shortest year, 88 days (notes §8)."),
   ("Jupiter", "Jupiter is closer to the Sun than Neptune, so its year is shorter (notes §2, §8)."),
   ("Saturn", "Saturn is closer to the Sun than Neptune, so its year is shorter (notes §2, §8).")])

Q("O", "Which two statements about Earth are true?",
  [("It turns once on its axis in about 24 hours", "That turn is a day, about 24 hours (notes §7)."),
   ("Its axis is tilted by about 23.4°", "The tilt is about 23.4° and causes the seasons (notes §7).")],
  [("It is the second planet from the Sun", "Earth is the third planet; Venus is the second (notes §2)."),
   ("Its year is about 88 days", "88 days is Mercury's year; Earth's is about 365.25 days (notes §7, §8).")])
