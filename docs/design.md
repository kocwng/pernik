# Pernik design rules: the "komik" style

The look is a two-colour risograph comic page: black ink and one spot colour printed on soft paper, laid out in panels like a manga chapter, with game-UI details. Every widget follows the rules below. Most of them are borrowed from designers who did this well.

## 1. Colour: ink, one spot, paper (and nothing else)

> "In the beginning, there were only a few colours." Massimo Vignelli limited himself to a handful of colours so that what he did use carried meaning.

Each theme has exactly four values:

| Token | Role | komik (default) |
|---|---|---|
| `paper` | the page every widget is printed on | `#FAF3F8` |
| `ink` | every outline, all type, solid label bars | `#1C1520` |
| `spot` | the single accent: fills, halftones, highlights | `#E0569B` |
| `tint` | spot at about 35%, for large quiet areas | `#F4BCD8` |

- No gradients. Tone comes from **halftone dots**, the way a two-colour press makes it.
- No third hue. Changing the theme swaps the spot colour and everything follows.
- White is not used; paper is the lightest value.

## 2. Line: three weights only

> Dieter Rams: "Less, but better." One consistent line makes a set of drawings look like one hand drew them.

| Weight | px | Used for |
|---|---|---|
| frame | 4 | panel borders, the outside of every widget |
| line | 2.5 | drawings, badges, bars |
| hair | 1.5 | details, speed lines, inner rules |

Lines are ink, round-capped and round-joined. Corners of panels: radius 6. Labels: radius 2. Nothing else gets a radius.

## 3. Grid: everything sits on 8

> Josef Müller-Brockmann: the grid makes order visible.

- All positions and sizes are multiples of 8 (4 for small details).
- Gutters between panels: 16. Inside padding: 16 or 24.
- Widgets are 900 wide, the width GitHub gives a README column, and their heights are multiples of 8.

## 4. Type: three roles, each with one job

| Role | Font stack | Used for |
|---|---|---|
| display | `'Arial Rounded MT Bold', 'Nunito', 'Varela Round', sans-serif`, weight 800 | the one big word in a widget |
| label | `'Arial Black', 'Helvetica Neue', Arial, sans-serif`, uppercase, tracking +0.04em | panel titles, bars, buttons |
| mono | `ui-monospace, 'SF Mono', Menlo, Consolas, monospace` | small UI text: `EXP`, `No.01`, captions in quotes |

- One display word per widget at most. Hierarchy comes from size and weight contrast (at least 2.5×), not from more fonts.
- Display text gets the **print shadow**: an ink copy offset 4,4 behind a spot fill with an ink outline.

## 5. Light and dark

Every widget is printed on its own piece of `paper` with an ink frame, plus a 4 px paper margin outside the frame. On GitHub light the margin disappears into the white page. On GitHub dark it reads as the edge of a printed card. Light and dark files are therefore identical (`same=True`): one file, half the bytes.

## 6. Ornament with a reason

> Paul Rand: "Don't try to be original, just try to be good."

Every decoration must do one of three things: guide the eye, say something about the person, or show state.

| Device | When |
|---|---|
| halftone burst behind an object | to make one thing the hero of a panel |
| speed lines | movement or emphasis; never more than one set per panel |
| hearts row / `EXP` bar | to show a real value (from config or data), never random numbers |
| numbered badge ①②③ | when the order of items means something |
| `▶▶` button | only where there is something to go to next |
| kamboja (frangipani) petals | the falling-petal accent, our version of sakura; at most 7 per widget |
| circled letters | one short tagline, at most 12 letters |

Batik motifs are drawn as two-colour stamps (`spot` on `paper` with `ink` lines), the way cap batik is printed.

## 7. Words

- English UI words, short and lowercase in captions (`"to be continued..."`), uppercase in labels.
- No fake Japanese. Pernik is Indonesian, so local words are welcome where they mean something (`lanjut`, `tamat`), always with the meaning clear from context.
- Never invent stats. A hearts row shows a value the user set or that comes from data.

## 8. Motion

Print doesn't move much, so animation stays small.

- Things **arrive** once: panels stamp in (scale 1.04→1), lines draw in.
- **Idle motion** is limited to one loop per widget: the mascot bobs, the reels spin, or petals fall. Never all at once.
- Respect `prefers-reduced-motion`. The still frame must be a finished picture.

## 9. Checklist before shipping a widget

- [ ] Only `paper`, `ink`, `spot`, `tint` (and halftones of them)
- [ ] Only 4 / 2.5 / 1.5 lines
- [ ] Coordinates on the 8 grid
- [ ] At most one display word, at most three type roles
- [ ] Every ornament passes the "reason" test
- [ ] One idle loop at most
- [ ] Reads at 50% size (GitHub on a phone)
- [ ] Under 25 KB, `pernik check` passes
