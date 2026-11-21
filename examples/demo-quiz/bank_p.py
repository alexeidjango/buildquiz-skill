from bank import Q

Q("P", "Which planet is the largest in the Solar System?",
  [("Jupiter", "Jupiter is the largest planet, with more than twice the mass of all the others together (notes §3).")],
  [("Saturn", "Saturn is a gas giant too, but smaller than Jupiter (notes §2, §3)."),
   ("Neptune", "Neptune is an ice giant, much smaller than Jupiter (notes §2, §3)."),
   ("Earth", "Earth is one of the small rocky inner planets (notes §2).")])

Q("P", "Which planet is the closest to the Sun?",
  [("Mercury", "Mercury is the first planet from the Sun (notes §2, §3).")],
  [("Venus", "Venus is the second planet from the Sun (notes §2)."),
   ("Earth", "Earth is the third planet from the Sun (notes §2)."),
   ("Mars", "Mars is the fourth planet from the Sun (notes §2).")])

Q("P", "Which planet is the hottest?",
  [("Venus", "Its thick carbon dioxide atmosphere traps heat: about 465 °C (notes §4).")],
  [("Mercury", "Mercury is closer to the Sun, but it has almost no atmosphere and loses its heat (notes §4)."),
   ("Mars", "Mars is farther from the Sun than Earth (notes §2)."),
   ("Jupiter", "Jupiter is a gas giant far beyond Mars (notes §2).")])

Q("P", "Which two planets are gas giants?",
  [("Jupiter", "Jupiter and Saturn are the gas giants (notes §2)."),
   ("Saturn", "Jupiter and Saturn are the gas giants (notes §2).")],
  [("Uranus", "Uranus is an ice giant, not a gas giant (notes §2)."),
   ("Neptune", "Neptune is an ice giant, not a gas giant (notes §2)."),
   ("Mars", "Mars is a small rocky inner planet (notes §2).")])

Q("P", "How many planets does the Solar System have?",
  [("Eight", "Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus and Neptune (notes §2, §10).")],
  [("Nine", "Pluto used to be counted, but since 2006 it is a dwarf planet (notes §10)."),
   ("Seven", "There are eight planets (notes §2)."),
   ("Ten", "There are eight planets (notes §2).")])

Q("P", "Since 2006, what is Pluto?",
  [("A dwarf planet", "The International Astronomical Union reclassified Pluto as a dwarf planet in 2006 (notes §10).")],
  [("The ninth planet", "Pluto lost that status in 2006 (notes §10)."),
   ("A comet", "Comets are listed separately from dwarf planets such as Pluto (notes §1)."),
   ("A moon of Neptune", "Pluto is a dwarf planet bound to the Sun, not a moon (notes §1, §10).")])

Q("P", "Which planet is marked with number 3?",
  [("Earth", "Earth is the third planet from the Sun (notes §2).")],
  [("Venus", "Venus is the second planet from the Sun, number 2 (notes §2)."),
   ("Mars", "Mars is the fourth planet from the Sun, number 4 (notes §2)."),
   ("Mercury", "Mercury is the first planet from the Sun, number 1 (notes §2).")],
  img="P_inner_planets")

Q("P", "Which planet is marked with number 1?",
  [("Mercury", "Mercury is the closest planet to the Sun (notes §2, §3).")],
  [("Venus", "Venus is the second planet, number 2 (notes §2)."),
   ("Earth", "Earth is the third planet, number 3 (notes §2)."),
   ("Mars", "Mars is the fourth planet, number 4 (notes §2).")],
  img="P_inner_planets")

Q("P", "Which planet has the brightest and largest rings?",
  [("Saturn", "Saturn's rings are by far the brightest and largest (notes §9).")],
  [("Jupiter", "Jupiter has rings, but they are faint (notes §9)."),
   ("Uranus", "Uranus has rings, but they are faint (notes §9)."),
   ("Mars", "Mars is a rocky inner planet; only the four giants have rings (notes §2, §9).")])
