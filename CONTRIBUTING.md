# Contributing to Pernik

Thank you for helping! You can add three kinds of things: themes, widgets and mascots.

## Ground rules for every picture

GitHub shows README pictures through its image proxy, inside `<img>`. So every SVG must:

- be self-contained: no scripts, no `<foreignObject>`, no outside images, fonts or CSS;
- animate only with CSS `@keyframes` or SMIL, and show or hide things by scaling, not by fading (fades look muddy on dark pages);
- read well on both `#ffffff` (GitHub light) and `#0d1117` (GitHub dark). The sticker look does this with a cream outline and a soft ink shadow. Never put ink-coloured detail directly on the transparent background;
- stay under about 25 KB;
- have a `<title>`, a `<desc>` and a useful `alt`.

`python -m pernik check` tests all of this, and `python -m pernik preview` shows every widget on both backgrounds.

## Add a theme

Copy `pernik/themes/pastel.toml`. Use `extends = "pernik"` and change only what you need: `accents`, `[colors]`, `[sticker]`, `[light]` and `[dark]`. Then build the example profile with your theme and check the preview:

```bash
python3 -m pernik preview examples/profile/pernik.toml
```

## Add a widget

1. Create `pernik/widgets/<kind>.py`:

   ```python
   from pernik.widgets import widget, Out
   from pernik.svg import doc, sticker, text_sticker

   @widget('badge', defaults={'text': 'hi'})
   def badge(opts, ctx):
       """A one-line description shown by `python -m pernik list`."""
       pal = ctx.pal  # colours for ctx.mode, 'light' or 'dark'
       body = sticker(f'<rect x="10" y="10" width="200" height="60" rx="30" fill="{pal.color("pink")}"/>', pal)
       return Out(svg=doc(230, 90, body, title=opts['text'], pal=pal), alt=opts['text'])
   ```

2. Use only the Python standard library. If you truly need more, mark the widget `heavy=True` and import the package inside the function, as `mixtape` does.
3. Use `ctx.seed` for anything random, so a profile looks the same on every build.
4. Add the widget to `examples/profile/pernik.toml` and to the widget list in `README.md`.
5. Run `python3 -m unittest discover -s tests`. It builds every widget with its defaults.

## Add a mascot

Mascots live in `pernik/mascots/`. Each one is a module that returns its SVG group and CSS for a palette. Put your name and the licence (CC BY 4.0) in a comment at the top of the file.

Design an original character. Don't copy someone else's mascot.

## Cultural care

Pernik draws on Indonesian traditions, so please be careful with them.

- **Batik:** don't add parang, lereng or other motifs that were historically restricted to the courts. Describe new motifs in `docs/motifs.md`, say where they come from, and call them designs *inspired by* the motif.
- **Wayang:** design original wayang-*style* figures. Don't use specific characters, the gunungan, or ritual figures.
- **Aksara:** a transliteration should be checked by someone who reads the script, and there must always be a way for users to type their own spelling.
