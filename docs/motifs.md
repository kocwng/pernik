# The batik motifs in `divider`

The `divider` widget can draw a band inspired by four batik motifs: `kawung`, `truntum`,
`mega-mendung` and `sekar-jagad`. This page explains where each one comes from and what it
is usually said to mean, and how the band is made.

**These are procedural designs inspired by the motifs. They are not reproductions of any
particular cloth.** Each band is drawn from simple shapes by code, in the Pernik sticker
palette, and varied by a seed. Real batik is made by hand: hot wax is drawn on cloth with a
*canting* (batik tulis) or stamped with a *cap*, then the cloth is dyed. The draw-in
animation is a small nod to the canting. If you want the real thing, buy batik from the
people who make it.

Indonesian batik is on UNESCO's list of Intangible Cultural Heritage (inscribed 2009).

## How sure are these notes?

The notes below summarise what is commonly written about each motif. Most stories about
where a batik motif came from are passed on as tradition, and sources often disagree, so
each section says how confident we are. Corrections from people who know the tradition
are very welcome. Please open an issue.

---

## Kawung

Kawung is four ovals arranged around a centre point, repeated in a grid. It is one of the
oldest known Javanese patterns. Kawung-like patterns are commonly reported on stone
statues and temple reliefs from Java's Hindu-Buddhist period, for example in the Prambanan
area.

- **Meaning:** The ovals are usually linked to the fruit of the aren (sugar palm), and
  sometimes to the lotus. The motif is commonly associated with purity, self-control and
  wisdom. Some writers read the four ovals and the centre as the four directions around a
  centre (*sedulur papat lima pancer*).
- **Confidence:** High that it is very old and widely used. Medium on the specific meanings,
  which vary from source to source.
- **A caution:** Several sources list kawung among the motifs that were reserved for the
  royal family and nobles at the Yogyakarta court (*batik larangan*) in the past. Today
  kawung is very common and is worn freely, but you may want to keep that history in mind.
  (Medium confidence. We have not checked the original court decrees.)
- **What Pernik draws:** Fat ovals in a diagonal lattice, with cream "wax" outlines, an
  inner vein in each oval, a small dot at each centre and small cream stars where the oval
  tips meet. The seed changes the lattice size, how fat the ovals are, the colour order and
  the colour scheme. The middle row steps through your colours, and the rows above and below
  use a softer tint.

## Truntum

Truntum is small star- or jasmine-like blossoms scattered evenly over the cloth, often
with tiny dots between them. It is associated with the Surakarta (Solo) court.

- **Origin story:** By tradition it was created by Kanjeng Ratu Kencana (also called Ratu
  Beruk), a consort of Sunan Pakubuwana III, in the 18th century. The story says she made it
  while the king's love for her was blossoming again.
- **Meaning:** The name is often linked to *tumaruntum*, "to grow again, to keep on". This is
  read as love that blossoms again and lasts. The parents of the bride and groom
  traditionally wear truntum at Javanese weddings. It stands for the parents' love and their
  guidance as the couple start out.
- **Confidence:** High on the wedding use and the meaning of renewed love. Medium on who
  created it, because that is a traditional story.
- **What Pernik draws:** Eight- and six-petal blossoms on a staggered two-row grid, with a
  little jitter in position, size and rotation. Small cream stars or three-dot *cecek* sit
  between them. Tall bands repeat the two-row unit.

## Mega mendung

Mega mendung comes from Cirebon, on the north coast of West Java, especially the Trusmi
batik village. It shows layered cloud forms. Each cloud is outlined by several bands of one
colour family that step from dark to light (*gradasi*). Classic pieces use blue or red
tones.

- **Influence:** The cloud forms are widely described as showing Chinese influence. Cirebon
  was a port with a long Chinese presence. A popular story links this to the marriage of
  Sunan Gunung Jati and a Chinese princess, but treat that as tradition, not documented
  history.
- **Meaning:** *Mega mendung* means "overcast sky, rain clouds". It is commonly read as
  patience and keeping a cool head: clouds bring cooling rain that gives life.
- **Confidence:** High on Cirebon, the cloud forms with stepped colour bands, and Chinese
  influence in general. Medium on the meaning. Low on the specific origin story.
- **What Pernik draws:** Lobed cloud outlines with cusps between the lobes. Each cloud has 3
  to 7 bands of real, even width (inset strokes clipped to the cloud), from a deepened
  colour at the edge to almost cream in the core. The clouds overlap in a drifting row,
  some flipped. The seed picks the number of bands, the cloud shapes, and one or two colour
  families. Pale yellows are avoided because they turn muddy.

## Sekar jagad

Sekar jagad is a patchwork of irregular, island-like areas. Each area is filled with a
different small motif, so the cloth looks like a map made of many patterns. It is
associated with Central Java (Yogyakarta and Surakarta) and is also made in other batik
centres.

- **Meaning:** *Sekar* means "flower" and *jagad* means "world", so "flowers of the world".
  It is usually read as celebrating diversity: many different beauties living together. A
  common explanation says *kar* comes from the Dutch *kaart* ("map"), giving "map of the
  world".
- **Confidence:** High on the meaning of the name and the diversity reading. Medium on the
  *kaart* explanation, which is widely repeated but hard to check.
- **What Pernik draws:** Columns with wavy, seeded borders, some of them split in two. Each
  cell gets a colour and a small fill pattern that differs from its neighbour's. Some
  patterns are named after real *isen-isen* (filler motifs): *cecek* (dots), *sisik*
  (scales), *gringsing* and *ukel* (curls). Others are simple descriptive fills: tiny
  kawung, small flowers, waves. The cell borders are a cream double line, like the
  outlined islands on the cloth.

---

## Motifs that are left out on purpose

Some motifs were historically restricted by the Yogyakarta and Surakarta courts
(*batik larangan*), meaning only the ruler and close family were meant to wear them. The
best known are **parang** (including parang rusak and parang barong) and the diagonal
**lereng** family. Others named in such lists include semen gedhe sawat gurdha and udan
liris.

Pernik does not offer these. Asking for `style = "parang"` or `"lereng"` gives an
explanatory error instead of a picture. The sources differ on exactly which motifs were on
each court's list, so this is a cautious choice, not a complete list.

## Wave and dots

`wave` (a striped sticker ribbon) and `dots` are plain Pernik ornaments with no cultural
reference.
