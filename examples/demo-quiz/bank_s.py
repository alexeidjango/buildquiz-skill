from bank import Q

Q("S", "What is the Sun?",
  [("A star", "The Sun is a star, made mostly of hydrogen and helium (notes §5).")],
  [("A planet", "The planets orbit the Sun; the Sun itself is a star (notes §1, §5)."),
   ("A gas giant", "Gas giants are planets such as Jupiter and Saturn (notes §2)."),
   ("A comet", "Comets are small bodies bound to the Sun (notes §1).")])

Q("S", "How does the Sun produce its energy?",
  [("By nuclear fusion of hydrogen into helium", "In its core the Sun turns hydrogen into helium by nuclear fusion (notes §5).")],
  [("By burning coal and gas", "The Sun's energy comes from nuclear fusion, not burning (notes §5)."),
   ("By reflecting the light of other stars", "Reflecting light is how the Moon shines, not the Sun (notes §5, §6)."),
   ("By its rings spinning", "The Sun has no rings; only the giant planets do (notes §9).")])

Q("S", "About how long does sunlight take to reach Earth?",
  [("About 8 minutes", "Sunlight takes about 8 minutes to reach Earth (notes §5).")],
  [("About 8 seconds", "It takes about 8 minutes, not seconds (notes §5)."),
   ("About 8 hours", "It takes about 8 minutes, not hours (notes §5)."),
   ("About one day", "It takes about 8 minutes (notes §5).")])

Q("S", "Why does the Moon shine?",
  [("It reflects sunlight", "The Moon makes no light of its own; it reflects sunlight (notes §6).")],
  [("It produces light by nuclear fusion", "Fusion is how the Sun makes energy, not the Moon (notes §5, §6)."),
   ("It is hot enough to glow", "The Moon shines only by reflecting sunlight (notes §6)."),
   ("It reflects the light of Earth's cities", "The Moon reflects sunlight (notes §6).")])

Q("S", "Why do we always see the same side of the Moon?",
  [("It turns once on its axis in the same time as it orbits Earth",
    "Both take about 27.3 days, so the same side always faces Earth (notes §6).")],
  [("It does not turn at all", "It does turn, once in about 27.3 days (notes §6)."),
   ("Earth's shadow always hides the other side", "The same side faces Earth because of how the Moon turns (notes §6)."),
   ("The other side never gets any sunlight", "The same side faces Earth because the Moon turns once per orbit (notes §6).")])

Q("S", "About how often do the Moon's phases repeat?",
  [("About every 29.5 days", "The phases repeat about every 29.5 days (notes §6).")],
  [("About every 24 hours", "24 hours is one turn of Earth, a day (notes §7)."),
   ("About every 365 days", "About 365.25 days is Earth's year (notes §7)."),
   ("About every 7 days", "The phases repeat about every 29.5 days (notes §6).")])

Q("S", "In which year did people first land on the Moon?",
  [("1969", "Apollo 11 landed on the Moon in July 1969.")],
  [("1957", "1957 is the year of Sputnik 1, the first artificial satellite."),
   ("1961", "In 1961 Yuri Gagarin became the first person in space, without landing anywhere."),
   ("1975", "The last crewed Moon landing was Apollo 17 in 1972; none happened in 1975.")],
  off_source=True, note="Not in the lesson notes: answered from general knowledge.")
