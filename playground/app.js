/* Pernik playground: edit a profile, see it drawn by the real Pernik (Python, in a worker),
   copy the pernik.toml. No framework; the page works from gallery.json before Python loads. */
'use strict';

(() => {
  // ------------------------------------------------------------------ tables
  const KIND_ORDER = ['hero', 'divider', 'heading', 'stack', 'mixtape', 'footer'];
  const BASE_ID = { hero: 'hello', divider: 'line', heading: 'title', stack: 'stack', mixtape: 'tape', footer: 'bye' };
  const CHOICES = {
    'divider.style': ['wave', 'kawung', 'truntum', 'mega-mendung', 'sekar-jagad', 'dots', 'film', 'hearts'],
    'hero.mascot': ['banana', 'none'],
    'heading.align': ['left', 'center', 'right'],
    'heading.color': ['pink', 'jeruk', 'kuning', 'mint', 'langit', 'anggur', 'ink'],
    'mixtape.chords': ['auto', 'keep', 'off'],
    'mixtape.pages': ['docs', '/'],
  };
  const LINES = new Set(['greeting', 'caption']);          // lists typed one item per line
  const ADVANCED = {
    hero: ['chords', 'beat'],
    divider: ['colors', 'ground', 'height', 'seed', 'animate'],
    mixtape: ['link', 'page_dir', 'pages', 'chords', 'video', 'make_video'],
  };
  // options the komik drawings read that aren't in the widget defaults (pernik/widgets/_komik_*.py)
  const EXTRAS = {
    hero: { tagline: '', hp: [], exp: null, exp_label: '', issue: 1 },
    footer: { name: '', link: '' },
  };
  const NUMERIC_LISTS = new Set();
  const ALIGNS = ['left', 'center', 'right'];
  const alignOf = (w) => (ALIGNS.includes(w.opts.align) ? w.opts.align : 'left');
  const START = { mixtape: { song: 'docs/music/demo.mp3' }, text: { md: '' } };
  const BASE_TEXT_ID = 'text';   // what a new widget starts with
  const HINTS = {
    'hero.greeting': 'One or two lines.',
    'hero.chords': 'A chords.json in your repo for the mascot to strum along to.',
    'hero.beat': 'Seconds per strum.',
    'hero.tagline': 'Up to 12 letters print as circled letters.',
    'hero.hp': 'Hearts, e.g. 4 full of 6. Leave both empty for no hearts.',
    'hero.exp': 'EXP bar fill from 0 to 1. Empty hides it.',
    'hero.exp_label': 'Text on the bar’s tab (default EXP).',
    'hero.issue': 'The “No.01” in the header; 0 hides it.',
    'divider.style': 'Batik bands draw themselves in. film and hearts are komik themes only.',
    'divider.colors': 'Colour names or hex, comma separated. Empty: the theme’s.',
    'divider.ground': 'Batik base colour (name or hex). Empty: automatic.',
    'divider.height': 'auto, or a height in px.',
    'divider.seed': 'Empty: from your username and the widget id.',
    'divider.animate': 'Draws itself in once, then a tiny idle glint.',
    'heading.number': 'Numbered badge; 0 hides it.',
    'heading.note': 'A small side note.',
    'heading.color': 'Pill colour (sticker themes).',
    'stack.icons': 'Simple Icons names, comma separated: go, docker, mysql…',
    'stack.columns': '0 = as many as fit in a row.',
    'stack.size': 'Tile width in px (48–140).',
    'footer.name': 'Default: @username.',
    'footer.link': 'Where clicking the footer goes.',
    'mixtape.song': 'A song file in your repo. In the playground the demo song stands in for it.',
    'mixtape.label': 'On the cassette label. Default: “username tape”.',
    'mixtape.caption': 'One or two lines.',
    'mixtape.chords': 'auto works the chords out from the song in the GitHub Action.',
    'mixtape.video': 'A https://github.com/user-attachments/… video you uploaded.',
    'mixtape.make_video': 'The GitHub Action renders the MP4; the playground skips it.',
    'mixtape.link': 'Where the cassette goes. Empty: the tape player page.',
  };
  const KOMIK_ONLY = 'Komik themes only';
  const WORKFLOW = `name: pernik

on:
  push:
    paths:
      - pernik.toml
      - "**.mp3"
      - "**.m4a"
      - "**.ogg"
      - "**.wav"
      - .github/workflows/pernik.yml
  schedule:
    - cron: "23 4 * * 1"      # Mondays 04:23 UTC
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: pernik-\${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    if: github.actor != 'github-actions[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: kocwng/pernik@v0
        with:
          config: pernik.toml
`;
  // GitHub usernames: 1-39 letters/digits, single hyphens, not at either end
  const USER_RE = /^(?=.{1,39}$)[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$/;
  const TEXT_HINT = 'Shown as written, between the pictures. Markdown works: **bold**, *italic*, - lists, [links](https://…), # headings, emoji 🎉.';
  const SONG_MAX = 10 * 1024 * 1024;            // bytes per uploaded song
  const SONG_PATH_RE = /^[A-Za-z0-9_][A-Za-z0-9._/-]{0,120}$/;
  const REPO_URL = 'https://github.com/kocwng/pernik';
  const defaultText = (user) => `Hi! I’m @${user} 👋\n\n- I work on …\n- I’m learning …\n- You can reach me at …\n\n*(Replace these lines with a few words about yourself.)*`;
  const ID_RE = /^[A-Za-z0-9_-]+$/;
  const LOGO_MAX = 200 * 1024;                  // bytes per uploaded logo
  const HASH_MAX = 16 * 1024;                   // share links keep uploaded logos only below this
  const LOGO_PATH_RE = /^assets\/logos\/[a-z0-9][a-z0-9._-]{0,60}\.svg$/;
  const HEX_RE = /^#[0-9a-fA-F]{6}$/;

  // ------------------------------------------------------------------ state
  let gallery = { themes: [], widgets: {}, prerender: {} };
  let specs = {};
  let uidN = 0;
  const state = { user: 'octocat', theme: 'komik', widgets: [] };
  const openSet = new Set();
  const cache = new Map();      // uid -> {key, result, urls: {light, dark}}
  const pending = new Map();    // uid -> key asked of the worker
  let workerReady = false;
  let demoSecs = 0;
  let demoAsked = false;
  let lastMs = null;
  const files = new Map();      // uploaded logos: repo path -> {text, rev}
  const songs = new Map();      // uploaded songs: repo path -> {secs, name, size}
  let lastGen = null;           // what the last "Generate my profile" asked for

  const $ = (s, el = document) => el.querySelector(s);
  const store = {
    get(k) { try { return localStorage.getItem('pernik-playground:' + k); } catch (_) { return null; } },
    set(k, v) { try { localStorage.setItem('pernik-playground:' + k, v); } catch (_) { /* private mode */ } },
  };

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k in el && typeof v !== 'string') el[k] = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
    return el;
  }

  // ------------------------------------------------------------------ options
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  function baseDefaults(kind) {
    return Object.assign({}, (specs[kind] || {}).defaults || {}, EXTRAS[kind] || {});
  }
  function newWidget(kind, id, opts) {
    return { uid: 'w' + (++uidN), kind, id: id || freeId(kind), opts: Object.assign(baseDefaults(kind), START[kind] || {}, opts || {}) };
  }
  function freeId(kind, taken) {
    const used = new Set(taken || state.widgets.map((w) => w.id));
    const base = BASE_ID[kind] || kind;
    if (!used.has(base)) return base;
    for (let i = 2; ; i++) if (!used.has(`${base}-${i}`)) return `${base}-${i}`;
  }
  /** Only the options that differ from Pernik's own defaults (what goes in pernik.toml). */
  function clean(w) {
    if (w.kind === 'text') {
      return alignOf(w) === 'left' ? { md: String(w.opts.md || '') } : { md: String(w.opts.md || ''), align: alignOf(w) };
    }
    const out = {};
    const spec = (specs[w.kind] || {}).defaults || {};
    const extra = EXTRAS[w.kind] || {};
    for (const [k, v] of Object.entries(w.opts)) {
      if (k in spec) {
        if (!same(v, spec[k]) && v !== null) out[k] = v;
      } else if (k in extra) {
        if (v === null || v === '' || (Array.isArray(v) && !v.length) || same(v, extra[k])) continue;
        out[k] = v;
      } else if (v !== null && v !== '' && !(isTable(v) && !Object.keys(v).length)) {
        out[k] = v;
      }
    }
    return out;
  }
  const isTable = (v) => !!v && typeof v === 'object' && !Array.isArray(v);
  function fieldType(kind, key, def) {
    if (CHOICES[`${kind}.${key}`]) return 'select';
    if (typeof def === 'boolean') return 'bool';
    if (typeof def === 'number') return 'number';
    if (Array.isArray(def)) return LINES.has(key) ? 'lines' : 'list';
    if (def === null || def === 'auto') return 'loose';      // text that may be a number
    return 'text';
  }
  function parseValue(type, raw, def, numericList) {
    if (type === 'bool') return !!raw;
    if (type === 'number') { const n = Number(raw); return raw === '' || Number.isNaN(n) ? def : n; }
    if (type === 'list' || type === 'lines') {
      const parts = String(raw).split(type === 'lines' ? /\n/ : /[,\n]/).map((s) => s.trim()).filter(Boolean);
      return numericList ? parts.map(Number).filter((n) => !Number.isNaN(n)) : parts;
    }
    if (type === 'loose') {
      const s = String(raw).trim();
      if (s === '') return def;
      return /^-?\d+(\.\d+)?$/.test(s) ? Number(s) : s;
    }
    return String(raw);
  }
  function showValue(type, v) {
    if (v === null || v === undefined) return '';
    if (type === 'list') return v.join(', ');
    if (type === 'lines') return v.join('\n');
    return String(v);
  }
  function docHints(doc) {
    const out = {};
    for (const line of String(doc || '').split('\n')) {
      const m = line.match(/^\s{2,}(\w+)\s{2,}(.+)$/);
      if (m && !out[m[1]]) out[m[1]] = m[2].trim();
    }
    return out;
  }

  // ------------------------------------------------------------------ worker
  const worker = new Worker('worker.js', { type: 'module' });
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === 'status') setLoading(`Loading the renderer: ${m.text} Showing the default looks meanwhile.`);
    else if (m.type === 'ready') onReady(m);
    else if (m.type === 'fatal') setLoading(`Couldn’t load the renderer (${m.text}). The default looks still show; reload to try again.`, 'failed');
    else if (m.type === 'rendered') onRendered(m);
    else if (m.type === 'zip') (m.profile ? onProfile(m) : onZip(m));
  };
  worker.onerror = (e) => setLoading(`The renderer stopped (${e.message || 'worker error'}). Reload to try again.`, 'failed');
  worker.postMessage({ type: 'init' });

  function setLoading(text, cls) {
    const box = $('#loading');
    $('#loading-text').textContent = text;
    box.classList.remove('done', 'failed');
    if (cls) box.classList.add(cls);
  }
  function onReady(m) {
    workerReady = true;
    setLoading(`Renderer ready: Pernik ${m.version} on Python ${m.python}, running in your browser.`, 'done');
    $('#engine').textContent = `Pernik ${m.version} + Pyodide ${m.pyodide} (Python ${m.python})`;
    $('#download').disabled = false;
    $('#generate').disabled = false;
    flush();
  }
  function measureDemo() {
    if (demoAsked || !state.widgets.some((w) => w.kind === 'mixtape')) return;
    demoAsked = true;
    const a = new Audio();
    a.preload = 'metadata';
    a.addEventListener('loadedmetadata', () => {
      if (!Number.isFinite(a.duration)) return;
      demoSecs = Math.round(a.duration * 100) / 100;
      worker.postMessage({ type: 'demo', secs: demoSecs });
      flush();
    }, { once: true });
    a.src = 'demo.mp3';
  }

  function keyOf(w) {
    const extra = w.kind === 'mixtape' ? [demoSecs, (songs.get(w.opts.song) || {}).secs || 0]
      : w.kind === 'stack' ? Object.values(w.opts.logos || {}).map((sp) => (files.get(logoFile(sp)) || {}).rev || '') : 0;
    return JSON.stringify([state.theme, state.user, w.id, w.kind, clean(w), extra]);
  }
  function flush() {
    measureDemo();
    if (!workerReady) return;
    for (const w of state.widgets) {
      if (w.kind === 'text') continue;            // your own words: drawn by the page, not Pernik
      const key = keyOf(w);
      const c = cache.get(w.uid);
      if ((c && c.key === key) || pending.get(w.uid) === key) continue;
      pending.set(w.uid, key);
      worker.postMessage({
        type: 'render', uid: w.uid, key,
        payload: { user: state.user, theme: state.theme, widget: Object.assign({ id: w.id, kind: w.kind }, clean(w)) },
      });
      paintWidget(w);
    }
    updateStatus();
  }
  let timer = null;
  function schedule(ms = 300) {
    clearTimeout(timer);
    timer = setTimeout(flush, ms);
    refreshOutputs();
  }
  function onRendered({ uid, key, result }) {
    if (pending.get(uid) === key) pending.delete(uid);
    const w = state.widgets.find((x) => x.uid === uid);
    if (!w || keyOf(w) !== key) { updateStatus(); return; }
    const old = cache.get(uid);
    if (old) revoke(old);
    const entry = { key, result, urls: {} };
    if (!result.error) {
      entry.urls.light = URL.createObjectURL(new Blob([result.light], { type: 'image/svg+xml' }));
      entry.urls.dark = result.same ? entry.urls.light
        : URL.createObjectURL(new Blob([result.dark], { type: 'image/svg+xml' }));
    }
    cache.set(uid, entry);
    lastMs = result.ms;
    paintWidget(w);
    paintCard(w);
    updateStatus();
  }
  function revoke(entry) {
    const seen = new Set();
    for (const u of Object.values(entry.urls)) if (u && !seen.has(u)) { seen.add(u); URL.revokeObjectURL(u); }
  }
  function updateStatus() {
    const st = $('#status');
    if (!workerReady) { st.textContent = ''; return; }
    if (pending.size) { st.textContent = `Drawing ${pending.size} widget${pending.size > 1 ? 's' : ''}…`; return; }
    const real = state.widgets.filter((w) => w.kind !== 'text');
    const bad = real.filter((w) => (cache.get(w.uid) || {}).result?.error);
    if (bad.length) st.textContent = `${bad.length} widget${bad.length > 1 ? 's have' : ' has'} a problem: ${bad.map((w) => w.id).join(', ')}.`;
    else st.textContent = `Up to date: ${real.length} widget${real.length === 1 ? '' : 's'}` + (lastMs !== null ? `, last one drawn in ${lastMs} ms.` : '.');
  }

  // ------------------------------------------------------------------ preview
  function buildPreview() {
    for (const mode of ['light', 'dark']) {
      const col = $('#readme-' + mode);
      col.replaceChildren();
      if (!state.widgets.length) {
        col.append(h('p', { class: 'empty', text: 'No widgets yet. Add one from the list.' }));
        continue;
      }
      state.widgets.forEach((w) => {
        col.append(h('div', { class: 'w' + (w.kind === 'text' ? ' md' : ''), 'data-uid': w.uid, 'data-mode': mode }));
      });
    }
    state.widgets.forEach(paintWidget);
  }
  function paintWidget(w) {
    if (w.kind === 'text') {
      const al = alignOf(w);
      for (const box of document.querySelectorAll(`.w[data-uid="${w.uid}"]`)) {
        // GitHub keeps <div align="..."> and centres everything inside it, list items included
        box.replaceChildren(...(al === 'left' ? mdBlocks(w.opts.md) : [h('div', { align: al }, mdBlocks(w.opts.md))]));
      }
      return;
    }
    const c = cache.get(w.uid);
    const fresh = c && c.key === keyOf(w);
    const busy = workerReady && pending.has(w.uid);
    for (const mode of ['light', 'dark']) {
      const box = document.querySelector(`.w[data-uid="${w.uid}"][data-mode="${mode}"]`);
      if (!box) continue;
      let content;
      if (c && c.result && !c.result.error) {
        content = h('img', { src: c.urls[mode], alt: c.result.alt || w.id, width: 900, decoding: 'async' });
      } else if (c && c.result && c.result.error) {
        content = h('div', { class: 'err', role: 'note' },
          h('strong', { text: `${w.id} (${w.kind}): ` }), c.result.error);
      } else {
        const byTheme = (gallery.prerender || {})[state.theme] || {};
        const pre = byTheme[`${w.kind}:${w.opts.style}`] || byTheme[w.kind];
        content = pre && pre[mode]
          ? h('img', { src: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(pre[mode]), alt: pre.alt || w.id, width: 900 })
          : h('div', { class: 'ph', text: workerReady ? `drawing ${w.kind}…` : `${w.kind} appears when the renderer is ready` });
      }
      const cur = box.firstElementChild;
      if (cur && cur.tagName === 'IMG' && content.tagName === 'IMG') {
        if (cur.getAttribute('src') !== content.getAttribute('src')) cur.src = content.src;
        cur.alt = content.alt;
      } else {
        box.replaceChildren(content);
      }
      const chip = box.querySelector('.busy');
      if (busy || (c && !fresh && workerReady)) {
        if (!chip) box.append(h('span', { class: 'busy', 'aria-hidden': 'true', text: 'drawing…' }));
      } else if (chip) chip.remove();
      box.setAttribute('aria-busy', busy ? 'true' : 'false');
    }
  }

  // ------------------------------------------------------------------ editor
  function buildThemes() {
    const box = $('#themes');
    box.replaceChildren();
    for (const t of gallery.themes) {
      const name = typeof t === 'string' ? t : t.name;
      const sw = (typeof t === 'object' && t.swatch && t.swatch.light) || {};
      const colours = sw.paper ? [sw.paper, sw.ink, sw.spot, sw.tint] : (sw.accents || []).slice(0, 4);
      box.append(h('label', { class: 'theme' },
        h('input', { type: 'radio', name: 'theme', value: name, checked: name === state.theme }),
        h('span', { class: 'sw', 'aria-hidden': 'true' }, colours.map((c) => h('i', { style: `background:${c}` }))),
        h('span', { class: 'name', text: name })));
    }
  }
  $('#themes').addEventListener('change', (e) => {
    if (e.target.name !== 'theme') return;
    state.theme = e.target.value;
    state.widgets.forEach(paintWidget);
    schedule(0);
  });

  function buildAdd() {
    const box = $('#add');
    box.replaceChildren();
    for (const kind of kinds()) {
      const doc = ((specs[kind] || {}).doc || '').split('\n')[0];
      box.append(h('button', { class: 'btn', type: 'button', 'data-kind': kind, title: doc, 'aria-label': `Add ${kind}: ${doc}` }, `+ ${kind}`));
    }
    box.append(h('button', { class: 'btn', type: 'button', 'data-kind': 'text', title: 'Your own words, in markdown, between the pictures',
      'aria-label': 'Add text: your own words, in markdown, between the pictures' }, '+ text'));
  }
  function kinds() {
    return Object.keys(specs).sort((a, b) => (KIND_ORDER.indexOf(a) + 1 || 99) - (KIND_ORDER.indexOf(b) + 1 || 99) || a.localeCompare(b));
  }
  $('#add').addEventListener('click', (e) => {
    const b = e.target.closest('[data-kind]');
    if (!b) return;
    const w = newWidget(b.dataset.kind);
    if (w.kind === 'text') w.opts.md = 'Write something here.';
    state.widgets.push(w);
    openSet.add(w.uid);
    structural({ uid: w.uid, focus: 'toggle' });
    announceOut(`Added ${w.kind} “${w.id}” at the end.`);
  });

  function buildList(focus) {
    const list = $('#widgets');
    list.replaceChildren();
    state.widgets.forEach((w, i) => list.append(card(w, i)));
    $('#count').textContent = `(${state.widgets.length})`;
    if (focus) {
      const li = list.querySelector(`[data-uid="${focus.uid}"]`);
      let el = li && li.querySelector(focus.focus === 'toggle' ? '.wtoggle' : `[data-act="${focus.focus}"]`);
      if (el && el.disabled) el = li.querySelector('.wtoggle');
      if (!el && focus.fallback) el = focus.fallback();
      if (el) el.focus();
    }
  }
  function card(w, i) {
    const open = openSet.has(w.uid);
    const n = state.widgets.length;
    const name = w.kind === 'text' ? `text “${snippet(w)}”` : `${w.kind} “${w.id}”`;
    const li = h('li', { class: 'wcard' + (open ? ' open' : ''), 'data-uid': w.uid },
      h('div', { class: 'whead' },
        h('button', { class: 'wtoggle', type: 'button', 'aria-expanded': open ? 'true' : 'false', 'aria-controls': 'wb-' + w.uid, 'data-act': 'toggle', 'aria-label': `${i + 1}. ${name} options` },
          h('span', { class: 'wnum', 'aria-hidden': 'true', text: String(i + 1) }),
          h('span', { class: 'wkind', text: w.kind }),
          h('span', { class: 'wid', id: 'wi-' + w.uid, text: w.kind === 'text' ? snippet(w) : w.id }),
          h('span', { class: 'wstate', id: 'ws-' + w.uid }),
          h('span', { class: 'caret', 'aria-hidden': 'true' })),
        h('button', { class: 'icon', type: 'button', 'data-act': 'up', disabled: i === 0, 'aria-label': `Move ${name} up`, title: 'Move up', text: '↑' }),
        h('button', { class: 'icon', type: 'button', 'data-act': 'down', disabled: i === n - 1, 'aria-label': `Move ${name} down`, title: 'Move down', text: '↓' }),
        h('button', { class: 'icon', type: 'button', 'data-act': 'remove', 'aria-label': `Remove ${name}`, title: 'Remove', text: '✕' })),
      h('div', { class: 'wbody', id: 'wb-' + w.uid, hidden: !open }, open ? form(w) : null));
    paintCardState(li, w);
    return li;
  }
  function form(w) {
    if (w.kind === 'text') {
      const fid = `f-${w.uid}-md`;
      const ta = h('textarea', { id: fid, rows: 6, 'data-key': 'md', 'data-type': 'md', 'aria-describedby': fid + '-h' });
      ta.value = w.opts.md || '';
      const al = alignOf(w);
      return [h('div', { class: 'field' },
        h('label', { class: 'label', for: fid, text: 'your words (markdown)' }), ta,
        h('p', { class: 'hint', id: fid + '-h', text: TEXT_HINT })),
      h('fieldset', { class: 'field align', 'aria-describedby': fid + '-ah' },
        h('legend', { class: 'label', text: 'Align' }),
        h('div', { class: 'seg' }, ALIGNS.map((a) => h('label', {},
          h('input', { type: 'radio', name: `align-${w.uid}`, value: a, checked: a === al, 'data-key': 'align', 'data-type': 'radio' }),
          h('span', { text: a })))),
        h('p', { class: 'hint', id: fid + '-ah', text: 'Tip: centre a short intro, and put lists in their own left-aligned text block, like most profiles do.' }))];
    }
    const spec = specs[w.kind] || { defaults: {}, doc: '' };
    const dh = docHints(spec.doc);
    const fid = (k) => `f-${w.uid}-${k}`;
    const field = (key, def) => {
      if (w.kind === 'hero' && key === 'hp') return heartsField(w, fid);
      const type = fieldType(w.kind, key, def);
      const v = w.opts[key];
      const hint = HINTS[`${w.kind}.${key}`] || dh[key] || '';
      const hid = hint ? fid(key) + '-h' : null;
      const common = { id: fid(key), 'data-key': key, 'data-type': type, 'aria-describedby': hid };
      let input;
      if (type === 'bool') {
        return h('div', { class: 'field' },
          h('label', { class: 'switch', for: fid(key) },
            h('input', Object.assign({ type: 'checkbox', role: 'switch', checked: !!v }, common)),
            h('span', { class: 'track', 'aria-hidden': 'true' }),
            h('span', { class: 'label', text: key.replace(/_/g, ' ') })),
          hint ? h('p', { class: 'hint', id: hid, text: hint }) : null);
      }
      if (type === 'select') {
        const choices = CHOICES[`${w.kind}.${key}`].slice();
        if (v && !choices.includes(v)) choices.push(v);
        input = h('select', common, choices.map((c) => h('option', { value: c, selected: c === v, text: c })));
      } else if (type === 'lines') {
        input = h('textarea', Object.assign({ rows: 2, spellcheck: 'false' }, common));
        input.value = showValue(type, v);
      } else {
        const attrs = Object.assign({ type: type === 'number' ? 'number' : 'text', spellcheck: 'false', autocomplete: 'off' }, common);
        if (type === 'number') { attrs.step = Number.isInteger(def) ? '1' : 'any'; attrs.inputmode = 'decimal'; }
        if (type === 'loose' || type === 'list') attrs.placeholder = def === 'auto' ? 'auto' : (type === 'list' ? '' : 'automatic');
        input = h('input', attrs);
        input.value = showValue(type, v);
      }
      if (NUMERIC_LISTS.has(`${w.kind}.${key}`)) input.dataset.numericList = '1';
      return h('div', { class: 'field' },
        h('label', { class: 'label', for: fid(key), text: key.replace(/_/g, ' ') }), input,
        hint ? h('p', { class: 'hint', id: hid, text: hint }) : null);
    };

    const adv = new Set(ADVANCED[w.kind] || []);
    const main = [], more = [];
    for (const [k, d] of Object.entries(spec.defaults || {})) (adv.has(k) ? more : main).push(field(k, d));
    const extras = Object.entries(EXTRAS[w.kind] || {}).map(([k, d]) => field(k, d));
    const doc = (spec.doc || '').split('\n')[0];
    return [
      doc ? h('p', { class: 'wdoc', text: doc }) : null,
      h('div', { class: 'field' },
        h('label', { class: 'label', for: fid('_id'), text: 'id (README marker)' }),
        h('input', { id: fid('_id'), type: 'text', 'data-key': '_id', value: w.id, spellcheck: 'false', autocomplete: 'off', 'aria-describedby': fid('_id') + '-h' }),
        h('p', { class: 'hint', id: fid('_id') + '-h', text: 'Letters, digits, - and _. Used for file names and <!-- pernik:id -->.' })),
      main,
      w.kind === 'stack' ? logosSection(w) : null,
      w.kind === 'mixtape' ? songSection(w) : null,
      extras.length ? h('details', {}, h('summary', { text: `${KOMIK_ONLY}: more options` }), extras) : null,
      more.length ? h('details', {}, h('summary', { text: 'Advanced' }), more) : null,
      h('ul', { class: 'wlogs', id: 'wl-' + w.uid, hidden: true, 'aria-label': `Notes from ${w.id}` }),
      h('p', { class: 'wfiles', id: 'wf-' + w.uid }),
    ].flat().filter(Boolean);
  }
  function heartsField(w, fid) {
    const hp = Array.isArray(w.opts.hp) ? w.opts.hp : [];
    const num = (part, i) => h('div', { class: 'hp-part' },
      h('label', { class: 'label', for: fid('hp-' + part), text: part }),
      h('input', { id: fid('hp-' + part), type: 'number', min: '0', max: '20', step: '1', inputmode: 'numeric',
        value: Number.isInteger(hp[i]) ? String(hp[i]) : '', 'data-key': 'hp-' + part, 'aria-describedby': fid('hp') + '-h' }));
    return h('fieldset', { class: 'field hp' },
      h('legend', { class: 'label', text: 'hp (hearts)' }),
      h('div', { class: 'hp-row' }, num('full', 0), num('total', 1)),
      h('p', { class: 'hint', id: fid('hp') + '-h', text: HINTS['hero.hp'] }));
  }
  function readHearts(li, w) {
    const get = (part) => li.querySelector(`[data-key="hp-${part}"]`);
    const [f, t] = [get('full'), get('total')];
    const val = (el) => (el.value.trim() === '' ? null : Number(el.value));
    const full = val(f), total = val(t);
    const okNum = (n) => n === null || (Number.isInteger(n) && n >= 0 && n <= 20);
    const hint = li.querySelector(`#${CSS.escape(f.getAttribute('aria-describedby'))}`);
    f.setAttribute('aria-invalid', String(!okNum(full)));
    t.setAttribute('aria-invalid', String(!okNum(total) || (full !== null && total !== null && total < full)));
    let msg = HINTS['hero.hp'];
    if (!okNum(full) || !okNum(total)) msg = 'Use whole numbers from 0 to 20.';
    else if ((full === null) !== (total === null)) msg = 'Fill in both numbers to show hearts (or leave both empty).';
    else if (full !== null && total < full) msg = 'total should be at least as big as full.';
    else if (total === 0) msg = 'total 0 shows no hearts; leave both empty instead.';
    hint.textContent = msg;
    const good = okNum(full) && okNum(total) && full !== null && total !== null && total >= full && total > 0;
    w.opts.hp = good ? [full, total] : [];
  }
  function paintCardState(li, w) {
    const c = cache.get(w.uid);
    const st = li.querySelector('.wstate');
    if (w.kind === 'text') { st.textContent = ''; return; }
    const fresh = c && c.key === keyOf(w);
    st.classList.toggle('bad', !!(c && c.result.error));
    st.textContent = !workerReady ? '' : (pending.has(w.uid) || !fresh) ? 'drawing…'
      : c.result.error ? 'problem' : `${Math.ceil(Math.max(...c.result.bytes) / 1024)} KB`;
    const logs = li.querySelector('.wlogs');
    if (logs) {
      const lines = c ? [...(c.result.error ? [c.result.error] : []), ...(c.result.logs || [])] : [];
      logs.replaceChildren(...lines.map((t) => h('li', { text: t })));
      logs.hidden = !lines.length;
    }
    const links = li.querySelector('.wfiles');
    if (links) {
      links.replaceChildren();
      if (c && !c.result.error) {
        const list = c.result.same ? [['', c.urls.light]] : [['-light', c.urls.light], ['-dark', c.urls.dark]];
        links.append('Download: ', ...list.map(([suffix, url]) => h('a', { href: url, download: `${w.id}${suffix}.svg`, text: `${w.id}${suffix}.svg` })));
      }
    }
    if (w.kind === 'stack') paintLogos(li, w);
    if (w.kind === 'mixtape') paintSong(li, w);
  }
  function paintCard(w) {
    const li = document.querySelector(`.wcard[data-uid="${w.uid}"]`);
    if (li) paintCardState(li, w);
  }

  $('#widgets').addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (!b) return;
    const li = b.closest('[data-uid]');
    const i = state.widgets.findIndex((w) => w.uid === li.dataset.uid);
    const w = state.widgets[i];
    const act = b.dataset.act;
    if (act === 'toggle') {
      if (openSet.has(w.uid)) openSet.delete(w.uid); else openSet.add(w.uid);
      const open = openSet.has(w.uid);
      li.classList.toggle('open', open);
      b.setAttribute('aria-expanded', String(open));
      const body = li.querySelector('.wbody');
      body.hidden = !open;
      if (open && !body.childElementCount) { body.append(...form(w)); paintCardState(li, w); }
      return;
    }
    if (act === 'up' || act === 'down') {
      const j = act === 'up' ? i - 1 : i + 1;
      if (j < 0 || j >= state.widgets.length) return;
      [state.widgets[i], state.widgets[j]] = [state.widgets[j], state.widgets[i]];
      structural({ uid: w.uid, focus: act });
      announceOut(`Moved ${w.kind} “${w.id}” to position ${j + 1} of ${state.widgets.length}.`);
    } else if (act === 'remove') {
      state.widgets.splice(i, 1);
      openSet.delete(w.uid);
      const c = cache.get(w.uid);
      if (c) revoke(c);
      cache.delete(w.uid);
      pending.delete(w.uid);
      gcFiles();
      const next = state.widgets[Math.min(i, state.widgets.length - 1)];
      structural(next ? { uid: next.uid, focus: 'toggle' } : { fallback: () => $('#add .btn') });
      announceOut(`Removed ${w.kind} “${w.id}”.`);
    }
  });

  function onFieldInput(e) {
    const el = e.target;
    const key = el.dataset && el.dataset.key;
    if (!key) return;
    const li = el.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    if (!w) return;
    if (key === '_id') {
      const v = el.value.trim();
      const ok = ID_RE.test(v) && !state.widgets.some((x) => x !== w && x.id === v);
      el.setAttribute('aria-invalid', ok ? 'false' : 'true');
      const hint = document.getElementById(el.id + '-h');
      hint.textContent = ok ? 'Letters, digits, - and _. Used for file names and <!-- pernik:id -->.'
        : (ID_RE.test(v) ? `Another widget already uses “${v}”.` : 'Only letters, digits, - and _ (no spaces).');
      if (!ok) return;
      w.id = v;
      $('#wi-' + w.uid).textContent = v;
      li.querySelectorAll('.whead [aria-label]').forEach((b) => {
        b.setAttribute('aria-label', b.getAttribute('aria-label').replace(/“.*”/, `“${v}”`));
      });
    } else if (key === 'hp-full' || key === 'hp-total') {
      readHearts(li, w);
    } else {
      const type = el.dataset.type;
      const def = baseDefaults(w.kind)[key];
      const raw = type === 'bool' ? el.checked : el.value;
      w.opts[key] = parseValue(type, raw, def, el.dataset.numericList === '1');
      if (w.kind === 'stack' && key === 'icons') paintCard(w);
      if (w.kind === 'text') {
        w.auto = false;
        paintWidget(w);
        $('#wi-' + w.uid).textContent = snippet(w);
        li.querySelectorAll('.whead [aria-label]').forEach((b) => {
          b.setAttribute('aria-label', b.getAttribute('aria-label').replace(/“.*”/, `“${snippet(w)}”`));
        });
      }
    }
    const instant = el.tagName === 'SELECT' || el.type === 'checkbox';
    schedule(instant ? 30 : 300);
  }
  $('#widgets').addEventListener('input', onFieldInput);
  $('#widgets').addEventListener('change', (e) => { if (e.target.tagName === 'SELECT' || e.target.type === 'checkbox') return; onFieldInput(e); });

  $('#user').addEventListener('input', (e) => {
    const v = e.target.value.trim();
    const ok = v === '' || USER_RE.test(v);
    e.target.setAttribute('aria-invalid', ok ? 'false' : 'true');
    $('#user-hint').textContent = ok ? 'Shown as @name and used to seed your batik pattern.'
      : 'GitHub usernames use letters, digits and single hyphens (up to 39).';
    if (!ok) return;
    state.user = v || 'octocat';
    for (const w of state.widgets) {          // the untouched starter text follows the username
      if (w.kind !== 'text' || !w.auto) continue;
      w.opts.md = defaultText(state.user);
      const ta = document.getElementById(`f-${w.uid}-md`);
      if (ta) ta.value = w.opts.md;
      paintWidget(w);
    }
    $('#gen-status').textContent = '';
    schedule(400);
  });

  function structural(focus) {
    buildList(focus);
    buildPreview();
    schedule(30);
  }

  // ------------------------------------------------------------------ own logos (stack)
  const logoFile = (sp) => (typeof sp === 'string' ? sp : (isTable(sp) && typeof sp.file === 'string' ? sp.file : ''));
  const logoColor = (sp) => (isTable(sp) && typeof sp.color === 'string' ? sp.color : '');
  function fileRev(text) {
    let x = 2166136261;
    for (let i = 0; i < text.length; i++) { x ^= text.charCodeAt(i); x = Math.imul(x, 16777619); }
    return (x >>> 0).toString(36) + '.' + text.length.toString(36);
  }
  function putFile(path, text) {
    if (text === null) files.delete(path); else files.set(path, { text, rev: fileRev(text) });
    worker.postMessage({ type: 'file', path, text });
  }
  function referenced() {
    const set = new Set();
    for (const w of state.widgets) {
      if (w.kind !== 'stack') continue;
      for (const sp of Object.values(w.opts.logos || {})) if (logoFile(sp)) set.add(logoFile(sp));
    }
    return set;
  }
  function gcFiles() {
    const used = referenced();
    for (const p of [...files.keys()]) if (!used.has(p)) putFile(p, null);
  }
  function safeName(name) {
    return String(name).toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^[^a-z0-9]+|[-._]+$/g, '').slice(0, 40) || 'logo';
  }
  function pathFor(w, name) {
    const cur = logoFile((w.opts.logos || {})[name]);
    if (LOGO_PATH_RE.test(cur)) return cur;
    const taken = new Set();
    for (const x of state.widgets) {
      for (const [n, sp] of Object.entries(x.opts.logos || {})) if (!(x === w && n === name)) taken.add(logoFile(sp));
    }
    const base = `assets/logos/${safeName(name)}`;
    let p = `${base}.svg`;
    for (let i = 2; taken.has(p); i++) p = `${base}-${i}.svg`;
    return p;
  }
  function setLogo(w, name, spec) {
    const logos = Object.assign({}, w.opts.logos || {});
    if (spec === null) delete logos[name]; else logos[name] = spec;
    w.opts.logos = logos;
  }

  function logosSection(w) {
    return h('fieldset', { class: 'logos', 'aria-describedby': `olh-${w.uid}` },
      h('legend', { class: 'label', text: 'Own logos' }),
      h('p', { class: 'hint', id: `olh-${w.uid}`, text: 'For names Simple Icons doesn’t have, like aws. An SVG file with a viewBox, up to 200 KB; only its <path> shapes are used, in one colour.' }),
      h('div', { class: 'logo-rows', id: `ol-${w.uid}` }),
      h('p', { class: 'hint logo-msg', id: `olm-${w.uid}`, role: 'status' }));
  }
  function logoReport(w) {
    const c = cache.get(w.uid);
    const fresh = !!(c && c.key === keyOf(w) && !c.result.error);
    const missing = new Set();
    const broken = new Map();
    for (const line of (c && c.result.logs) || []) {
      let m = line.match(/^"(.+?)" (?:is not in Simple Icons|has no logo file)/);
      if (m) missing.add(m[1]);
      m = line.match(/logo file "([^"]+)"/);
      if (m) broken.set(m[1], line);
    }
    return { fresh, missing, broken };
  }
  function paintLogos(li, w) {
    const box = li.querySelector('.logo-rows');
    if (!box) return;
    const { fresh, missing, broken } = logoReport(w);
    const logos = w.opts.logos || {};
    const names = [];
    for (const n of Array.isArray(w.opts.icons) ? w.opts.icons : []) if (!names.includes(n)) names.push(n);
    for (const n of Object.keys(logos)) if (!names.includes(n)) names.push(n);
    const rank = (n) => (logoFile(logos[n]) ? 1 : missing.has(n) ? 0 : 2);
    names.sort((a, b) => rank(a) - rank(b));           // names without any logo first
    const rows = names.map((n) => {
      const file = logoFile(logos[n]);
      const status = file
        ? (!files.has(file) ? 'file missing: upload it again' : broken.has(file) ? 'not used: see the notes below' : 'your logo')
        : missing.has(n) ? 'not in Simple Icons' : fresh ? 'from Simple Icons' : '…';
      return { n, file, status, color: logoColor(logos[n]) };
    });
    const sig = JSON.stringify(rows.map((r) => [r.n, r.file, r.status]));
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    const act = document.activeElement;
    const restore = act && box.contains(act) ? [act.dataset.logoName, act.dataset.logoAct] : null;
    box.replaceChildren(...rows.map((r, i) => logoRow(w, r, i)));
    if (!rows.length) box.append(h('p', { class: 'hint', text: 'Add names to icons first.' }));
    if (restore) {
      const pick = (a) => [...box.querySelectorAll('[data-logo-name]')].find((e) => e.dataset.logoName === restore[0] && e.dataset.logoAct === a);
      const el = pick(restore[1]) || pick('upload');
      if (el) el.focus();
    }
  }
  function logoRow(w, r, i) {
    const id = `lg-${w.uid}-${i}`;
    const need = !r.file && r.status === 'not in Simple Icons';
    return h('div', { class: 'logo-row' + (need ? ' need' : '') + (r.file ? ' has' : '') },
      h('div', { class: 'logo-name' },
        h('span', { class: 'name', text: r.n }),
        h('span', { class: 'tag', text: r.status })),
      h('div', { class: 'logo-actions' },
        h('label', { class: 'btn file' + (need ? ' solid' : '') },
          h('span', { 'aria-hidden': 'true', text: r.file ? 'Replace SVG' : 'Upload SVG' }),
          h('input', { type: 'file', accept: '.svg,image/svg+xml', 'data-logo-name': r.n, 'data-logo-act': 'upload',
            'aria-label': `${r.file ? 'Replace' : 'Upload'} an SVG logo for ${r.n}` })),
        r.file ? h('button', { class: 'btn', type: 'button', 'data-logo-name': r.n, 'data-logo-act': 'remove', 'aria-label': `Remove the ${r.n} logo`, text: 'Remove' }) : null),
      r.file ? h('div', { class: 'logo-color' },
        h('label', { class: 'label', for: id + '-c', text: 'colour' }),
        h('span', { class: 'chip', 'aria-hidden': 'true', style: HEX_RE.test(r.color) ? `background:${r.color}` : null }),
        h('input', { id: id + '-c', type: 'text', value: r.color, placeholder: '#rrggbb', maxlength: '7', spellcheck: 'false', autocomplete: 'off',
          'data-logo-name': r.n, 'data-logo-act': 'color', 'aria-describedby': id + '-ch' }),
        h('p', { class: 'hint', id: id + '-ch', text: `Optional, for stiker themes; komik prints logos in ink. File: ${r.file}` })) : null);
  }

  async function onLogoFile(el) {
    const li = el.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    const name = el.dataset.logoName;
    const f = el.files && el.files[0];
    const say = (t) => { li.querySelector('.logo-msg').textContent = t; };
    if (!w || !f) return;
    if (!(/\.svg$/i.test(f.name) || f.type === 'image/svg+xml')) { say(`“${f.name}” isn’t an SVG file. Pick a .svg logo.`); el.value = ''; return; }
    if (f.size > LOGO_MAX) { say(`“${f.name}” is ${Math.ceil(f.size / 1024)} KB; a logo can be at most 200 KB. An optimiser like SVGO usually shrinks it.`); el.value = ''; return; }
    let text;
    try { text = (await f.text()).replace(/^\uFEFF/, ''); } catch (_) { say(`Couldn’t read “${f.name}”.`); return; }
    el.value = '';
    if (!/<svg[\s>]/i.test(text)) { say(`“${f.name}” doesn’t look like an SVG (there is no <svg> tag).`); return; }
    if (!/\sviewBox=["'][^"']+["']/.test(text)) { say(`“${f.name}” has no viewBox. Add one to its <svg> tag, e.g. viewBox="0 0 24 24", and upload it again.`); return; }
    const path = pathFor(w, name);
    putFile(path, text);
    const color = logoColor((w.opts.logos || {})[name]);
    setLogo(w, name, HEX_RE.test(color) ? { file: path, color } : path);
    say(`Using “${f.name}” for ${name}, saved as ${path}. Commit it at that path in your repo.`);
    paintCard(w);
    schedule(30);
  }
  $('#widgets').addEventListener('change', (e) => {
    if (e.target.dataset && e.target.dataset.logoAct === 'upload') onLogoFile(e.target);
  });
  $('#widgets').addEventListener('click', (e) => {
    const b = e.target.closest('[data-logo-act="remove"]');
    if (!b) return;
    const li = b.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    const name = b.dataset.logoName;
    setLogo(w, name, null);
    gcFiles();
    li.querySelector('.logo-msg').textContent = `Removed the ${name} logo.`;
    paintCard(w);
    schedule(30);
  });
  $('#widgets').addEventListener('input', (e) => {
    const el = e.target;
    if (!el.dataset || el.dataset.logoAct !== 'color') return;
    const li = el.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    const name = el.dataset.logoName;
    const v = el.value.trim();
    const ok = v === '' || HEX_RE.test(v);
    el.setAttribute('aria-invalid', ok ? 'false' : 'true');
    if (!ok) return;
    const file = logoFile((w.opts.logos || {})[name]);
    setLogo(w, name, v ? { file, color: v } : file);
    const chip = el.parentElement.querySelector('.chip');
    if (chip) chip.style.background = v || '';
    schedule(300);
  });

  // ------------------------------------------------------------------ text blocks (markdown)
  function snippet(w) {
    const line = String(w.opts.md || '').split('\n').map((l) => l.replace(/[#>*_`[\]()-]+/g, ' ').trim()).find(Boolean) || 'empty';
    return line.length > 28 ? line.slice(0, 27) + '…' : line;
  }
  const SAFE_URL = /^(https?:\/\/|mailto:)/i;
  // a small, safe subset of GitHub markdown, built as DOM nodes (never innerHTML)
  const INLINE = /(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)|\*\*(\S(?:[\s\S]*?\S)?)\*\*|__(\S(?:[\s\S]*?\S)?)__|\*(\S(?:[\s\S]*?\S)?)\*|(?<![A-Za-z0-9])_(\S(?:[\s\S]*?\S)?)_(?![A-Za-z0-9])|\[([^\]]+)\]\(([^)\s]+)\)|(https?:\/\/[^\s<]*[^\s<.,;:!?)\]'"*_])/g;
  function mdInline(text, parent) {
    let last = 0;
    for (const m of text.matchAll(INLINE)) {
      if (m.index > last) parent.append(text.slice(last, m.index));
      if (m[1]) parent.append(h('code', { text: m[2] }));
      else if (m[3] || m[4]) mdInline(m[3] || m[4], parent.appendChild(h('strong')));
      else if (m[5] || m[6]) mdInline(m[5] || m[6], parent.appendChild(h('em')));
      else if (m[7]) {
        if (SAFE_URL.test(m[8])) mdInline(m[7], parent.appendChild(h('a', { href: m[8], target: '_blank', rel: 'noopener noreferrer' })));
        else parent.append(m[0]);
      } else if (m[9]) parent.append(h('a', { href: m[9], target: '_blank', rel: 'noopener noreferrer', text: m[9] }));
      last = m.index + m[0].length;
    }
    if (last < text.length) parent.append(text.slice(last));
    return parent;
  }
  const LIST_UL = /^\s{0,3}[-*+]\s+/;
  const LIST_OL = /^\s{0,3}\d{1,9}[.)]\s+/;
  const BLOCK_START = /^\s{0,3}(#{1,6}\s|[-*+]\s|\d{1,9}[.)]\s|>)/;
  function mdBlocks(src) {
    const out = [];
    const lines = String(src || '').replace(/\r\n?/g, '\n').split('\n');
    let i = 0;
    const paragraph = (rows, el) => {
      rows.forEach((ln, k) => {
        const hard = / {2,}$|\\$/.test(ln);
        mdInline(ln.replace(/ {2,}$|\\$/, '').trim(), el);
        if (k < rows.length - 1) el.append(hard ? h('br') : ' ');
      });
      return el;
    };
    while (i < lines.length) {
      const line = lines[i];
      if (!line.trim()) { i++; continue; }
      const head = line.match(/^\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$/);
      if (head) { out.push(mdInline(head[2], h('h' + head[1].length))); i++; continue; }
      if (/^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/.test(line)) { out.push(h('hr')); i++; continue; }
      const listRe = LIST_UL.test(line) ? LIST_UL : LIST_OL.test(line) ? LIST_OL : null;
      if (listRe) {
        const list = h(listRe === LIST_UL ? 'ul' : 'ol');
        while (i < lines.length && listRe.test(lines[i])) { list.append(mdInline(lines[i].replace(listRe, ''), h('li'))); i++; }
        out.push(list);
        continue;
      }
      if (/^\s{0,3}>/.test(lines[i])) {
        const rows = [];
        while (i < lines.length && /^\s{0,3}>/.test(lines[i])) { rows.push(lines[i].replace(/^\s{0,3}>\s?/, '')); i++; }
        out.push(h('blockquote', {}, paragraph(rows.filter((r) => r.trim()), h('p'))));
        continue;
      }
      const rows = [];
      while (i < lines.length && lines[i].trim() && !(rows.length && BLOCK_START.test(lines[i]))) { rows.push(lines[i]); i++; }
      out.push(paragraph(rows, h('p')));
    }
    return out;
  }

  // ------------------------------------------------------------------ your own song (mixtape)
  const fmtSecs = (t) => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, '0')}`;
  function songSection(w) {
    return h('fieldset', { class: 'logos song' },
      h('legend', { class: 'label', text: 'Your song' }),
      h('p', { class: 'hint', id: `sgh-${w.uid}`, text: 'mp3, m4a, ogg or wav, up to 10 MB, and only a song you have the rights to. Until you add one, the preview plays a demo song and “Generate my profile” leaves this mixtape out.' }),
      h('div', { class: 'song-row', id: `sg-${w.uid}` }),
      h('p', { class: 'hint logo-msg song-msg', role: 'status' }));
  }
  function paintSong(li, w) {
    const box = li.querySelector('.song-row');
    if (!box) return;
    const s = songs.get(w.opts.song);
    const sig = s ? `${w.opts.song}|${s.secs}` : '-';
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    const hadFocus = box.contains(document.activeElement);
    box.replaceChildren(
      s ? h('p', { class: 'song-now' }, h('span', { class: 'name', text: s.name }), h('span', { class: 'tag', text: `${fmtSecs(s.secs)} · ${w.opts.song}` })) : '',
      h('div', { class: 'logo-actions' },
        h('label', { class: 'btn file' + (s ? '' : ' solid') },
          h('span', { 'aria-hidden': 'true', text: s ? 'Replace song' : 'Upload your song' }),
          h('input', { type: 'file', accept: '.mp3,.m4a,.ogg,.wav,audio/mpeg,audio/mp4,audio/x-m4a,audio/ogg,audio/wav,audio/x-wav',
            'data-song-act': 'upload', 'aria-label': s ? 'Replace your song' : 'Upload your song', 'aria-describedby': `sgh-${w.uid}` })),
        s ? h('button', { class: 'btn', type: 'button', 'data-song-act': 'remove', 'aria-label': 'Remove your song', text: 'Remove' }) : ''));
    if (hadFocus) box.querySelector('input[type=file]').focus();
  }
  function audioLength(file) {
    return new Promise((resolve) => {
      const a = new Audio();
      const url = URL.createObjectURL(file);
      const done = (v) => { URL.revokeObjectURL(url); resolve(v); };
      a.preload = 'metadata';
      a.addEventListener('loadedmetadata', () => done(Number.isFinite(a.duration) ? a.duration : 0), { once: true });
      a.addEventListener('error', () => done(0), { once: true });
      setTimeout(() => done(0), 10000);
      a.src = url;
    });
  }
  function dropSong(path) {
    if (!songs.has(path) || state.widgets.some((w) => w.kind === 'mixtape' && w.opts.song === path)) return;
    songs.delete(path);
    worker.postMessage({ type: 'song', path, bytes: null, secs: 0 });
  }
  function setField(li, key, value) {
    const el = li.querySelector(`[data-key="${key}"]`);
    if (el) el.value = value;
  }
  async function onSongFile(el) {
    const li = el.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    const f = el.files && el.files[0];
    const say = (t) => { li.querySelector('.song-msg').textContent = t; };
    if (!w || !f) return;
    const ext = (f.name.match(/\.(mp3|m4a|ogg|wav)$/i) || [])[1];
    el.value = '';
    if (!ext) { say(`“${f.name}” isn’t an mp3, m4a, ogg or wav file.`); return; }
    if (f.size > SONG_MAX) { say(`“${f.name}” is ${(f.size / 1048576).toFixed(1)} MB; a song can be at most 10 MB.`); return; }
    say(`Reading “${f.name}”…`);
    const secs = await audioLength(f);
    if (!secs) { say(`Couldn’t play “${f.name}”. Is it an audio file your browser can play?`); return; }
    const bytes = new Uint8Array(await f.arrayBuffer());
    const cur = String(w.opts.song || '').trim();
    const path = cur && cur !== START.mixtape.song && SONG_PATH_RE.test(cur) && !cur.split('/').includes('..') &&
      cur.toLowerCase().endsWith('.' + ext.toLowerCase())
      ? cur : `docs/music/${safeName(f.name.replace(/\.[^.]+$/, ''))}.${ext.toLowerCase()}`;
    songs.set(path, { secs: Math.round(secs * 100) / 100, name: f.name, size: f.size });
    worker.postMessage({ type: 'song', path, bytes, secs: songs.get(path).secs }, [bytes.buffer]);
    const old = w.opts.song;
    w.opts.song = path;
    w.opts.chords = 'off';                  // no numpy here; the Action can work chords out later
    dropSong(old);
    setField(li, 'song', path);
    setField(li, 'chords', 'off');
    say(`Using “${f.name}” (${fmtSecs(secs)}), saved as ${path}. Chords are off for now; set chords to auto later and the GitHub Action works them out.`);
    paintCard(w);
    schedule(30);
  }
  $('#widgets').addEventListener('change', (e) => {
    if (e.target.dataset && e.target.dataset.songAct === 'upload') onSongFile(e.target);
  });
  $('#widgets').addEventListener('click', (e) => {
    const b = e.target.closest('[data-song-act="remove"]');
    if (!b) return;
    const li = b.closest('[data-uid]');
    const w = state.widgets.find((x) => x.uid === li.dataset.uid);
    const old = w.opts.song;
    w.opts.song = START.mixtape.song;
    dropSong(old);
    setField(li, 'song', w.opts.song);
    li.querySelector('.song-msg').textContent = 'Removed your song; the preview plays the demo song again.';
    paintCard(w);
    schedule(30);
  });

  // ------------------------------------------------------------------ generate my profile
  const genSay = (t) => { $('#gen-status').textContent = t; };
  $('#generate').addEventListener('click', () => {
    const typed = $('#user').value.trim();
    if (!USER_RE.test(typed) || typed.toLowerCase() === 'octocat') {
      genSay('First put your own GitHub username in “GitHub username” at the top. It decides where your profile goes.');
      $('#user').setAttribute('aria-invalid', 'true');
      $('#user').focus();
      return;
    }
    if (!workerReady) { genSay('The renderer is still loading; try again in a moment.'); return; }
    const skipped = state.widgets.filter((w) => w.kind === 'mixtape' && !songs.has(w.opts.song));
    const list = state.widgets.filter((w) => !skipped.includes(w));
    lastGen = { user: state.user, skipped, mixtape: list.some((w) => w.kind === 'mixtape') };
    $('#generate').disabled = true;
    genSay('Drawing your profile with Pernik…');
    worker.postMessage({ type: 'zip', profile: true, toml: tomlText(list, true), readme: readmeText(list), user: state.user });
  });
  function onProfile(m) {
    $('#generate').disabled = false;
    if (m.error) { genSay(`Something went wrong while drawing: ${m.error}`); return; }
    const u = lastGen.user;
    const name = `${u}-profile.zip`;
    const url = URL.createObjectURL(new Blob([m.bytes], { type: 'application/zip' }));
    const a = h('a', { href: url, download: name });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    const repo = `https://github.com/${u}/${u}`;
    $('#step-create').href = `https://github.com/new?name=${encodeURIComponent(u)}&visibility=public&description=${encodeURIComponent('My GitHub profile')}`;
    $('#step-create-note').textContent = `Skip this if you already have a repo called ${u}. It must be public and named exactly like your username.`;
    $('#step-upload').href = `${repo}/upload/main`;
    $('#step-zipname').textContent = name;
    $('#step-done').href = `https://github.com/${u}`;
    $('#step-done').firstChild.nodeValue = `github.com/${u}`;
    $('#step-workflow').href = `${repo}/new/main?filename=${encodeURIComponent('.github/workflows/pernik.yml')}&value=${encodeURIComponent(WORKFLOW)}`;
    $('#step-actions').href = `${repo}/settings/actions`;
    $('#step-pages').hidden = !lastGen.mixtape;
    $('#step-pages-link').href = `${repo}/settings/pages`;
    const p = (m.info && m.info.problems) || [];
    const notes = [];
    if (lastGen.skipped.length) notes.push(`Left out: ${lastGen.skipped.map((w) => `mixtape “${w.id}”`).join(', ')} (add your own song to include it).`);
    if (p.length) notes.push(`Pernik found ${p.length} problem${p.length > 1 ? 's' : ''}: ${p.join('; ')}`);
    $('#steps-summary').textContent = `${name} is in your downloads.` + (notes.length ? ' ' + notes.join(' ') : '');
    $('#steps').hidden = false;
    genSay(`Downloaded ${name}. Next: put it on GitHub, steps below.`);
    $('#steps-title').focus();
  }

  // ------------------------------------------------------------------ outputs
  const tomlKey = (k) => (ID_RE.test(k) ? k : JSON.stringify(String(k)));
  function tomlValue(v) {
    if (Array.isArray(v)) return '[' + v.map(tomlValue).join(', ') + ']';
    if (isTable(v)) return '{ ' + Object.entries(v).map(([k, x]) => `${tomlKey(k)} = ${tomlValue(x)}`).join(', ') + ' }';
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'number') return Number.isFinite(v) ? String(v) : '0';
    return JSON.stringify(String(v)).replace(/\u007f/g, '\\u007F');
  }
  function tomlText(list = state.widgets, profile = false) {
    const out = [
      profile ? `# Edit this to change your widgets; see ${REPO_URL}`
        : '# Pernik settings, made in the playground. Every option: python3 -m pernik list',
      'schema = 1',
      `theme = ${tomlValue(state.theme)}`,
      'output = "pernik"',
      `# user = ${tomlValue(state.user)}   # found automatically in the GitHub Action`,
    ];
    for (const w of list) {
      if (w.kind === 'text') continue;            // your words live in README.md, not here
      out.push('');
      if (w.kind === 'mixtape' && !(profile && songs.has(w.opts.song))) out.push('# put your own song in the repo and point song at it (only songs you have the rights to)');
      if (w.kind === 'stack' && Object.keys(w.opts.logos || {}).length) out.push('# commit your logo files at these paths (the playground’s zip has them)');
      out.push('[[widget]]', `id = ${tomlValue(w.id)}`, `kind = ${tomlValue(w.kind)}`);
      for (const [k, v] of Object.entries(clean(w))) out.push(`${k} = ${tomlValue(v)}`);
    }
    return out.join('\n') + '\n';
  }
  function readmeText(list = state.widgets) {
    const parts = [];
    for (const w of list) {
      if (w.kind === 'text') {
        const md = String(w.opts.md || '').trim();
        if (!md) continue;
        const al = alignOf(w);
        // blank lines around the text, so GitHub still renders the markdown inside the HTML block
        parts.push(al === 'left' ? md : `<div align="${al}">\n\n${md}\n\n</div>`);
      }
      else parts.push(`<!-- pernik:${w.id} -->\n<!-- /pernik:${w.id} -->`);
    }
    return parts.join('\n\n') + '\n';
  }
  function refreshOutputs() {
    $('#out-toml').textContent = tomlText();
    $('#out-readme').textContent = readmeText();
    $('#out-workflow').textContent = WORKFLOW;
    const noSong = state.widgets.filter((w) => w.kind === 'mixtape' && !songs.has(w.opts.song));
    $('#gen-note').hidden = !noSong.length;
    $('#gen-note').textContent = noSong.length
      ? `Add your own song to use mixtape: without one, “Generate my profile” leaves ${noSong.map((w) => `“${w.id}”`).join(', ')} out.` : '';
    const used = [...referenced()].filter((p) => files.has(p));
    $('#logo-note').hidden = !used.length;
    $('#logo-note').textContent = used.length
      ? `Your uploaded logo${used.length > 1 ? 's' : ''}: ${used.join(', ')}. Commit ${used.length > 1 ? 'them' : 'it'} to your profile repo at ${used.length > 1 ? 'those paths' : 'that path'}; “Download SVGs” includes ${used.length > 1 ? 'them' : 'it'}.`
      : '';
    saveHashSoon();
  }

  // tabs (arrow keys move between them)
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function selectTab(tab, focus) {
    for (const t of tabs) {
      const on = t === tab;
      t.setAttribute('aria-selected', String(on));
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    }
    if (focus) tab.focus();
  }
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => selectTab(t));
    t.addEventListener('keydown', (e) => {
      const n = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
      if (n === undefined) return;
      e.preventDefault();
      selectTab(tabs[(n + tabs.length) % tabs.length], true);
    });
  });

  function announceOut(text) { $('#out-status').textContent = text; }
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_) {
      const ta = h('textarea', { 'aria-hidden': 'true', style: 'position:fixed;left:-9999px;top:0' });
      ta.value = text;
      document.body.append(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch (_) { ok = false; }
      ta.remove();
      return ok;
    }
  }
  document.querySelectorAll('[data-copy]').forEach((b) => b.addEventListener('click', async () => {
    const pre = document.getElementById(b.dataset.copy);
    const ok = await copy(pre.textContent);
    const what = pre.getAttribute('aria-label');
    announceOut(ok ? `Copied ${what}.` : `Couldn’t copy ${what}; select the text and copy it by hand.`);
    b.textContent = ok ? 'Copied' : 'Copy failed';
    setTimeout(() => { b.textContent = 'Copy'; }, 1600);
  }));

  $('#download').addEventListener('click', () => {
    if (!workerReady) return;
    $('#download').disabled = true;
    announceOut('Building every widget with pernik build and pernik check…');
    worker.postMessage({ type: 'zip', toml: tomlText(), readme: readmeText(), user: state.user });
  });
  function onZip(m) {
    $('#download').disabled = false;
    if (m.error) { announceOut(`The build failed: ${m.error}`); return; }
    const url = URL.createObjectURL(new Blob([m.bytes], { type: 'application/zip' }));
    const a = h('a', { href: url, download: `pernik-${state.user}.zip` });
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    const p = (m.info && m.info.problems) || [];
    const logos = (m.info && m.info.logos) || [];
    announceOut(`Downloaded pernik-${state.user}.zip (${m.info ? m.info.files : '?'} widgets)` +
      (p.length ? `, with ${p.length} problem(s): see pernik-problems.txt inside.` : '; pernik check passed.') +
      (logos.length ? ` It includes ${logos.join(', ')}: commit ${logos.length > 1 ? 'them' : 'it'} at the same path.` : ''));
  }

  // ------------------------------------------------------------------ share links
  const b64 = {
    enc(bytes) {
      let s = '';
      for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    },
    dec(str) {
      const s = atob(str.replace(/-/g, '+').replace(/_/g, '/'));
      return Uint8Array.from(s, (c) => c.charCodeAt(0));
    },
  };
  const canZip = typeof CompressionStream === 'function' && typeof DecompressionStream === 'function';
  async function pipe(bytes, stream) {
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer());
  }
  async function encodeJson(obj) {
    const raw = new TextEncoder().encode(JSON.stringify(obj));
    if (canZip) {
      try { return 'z=' + b64.enc(await pipe(raw, new CompressionStream('deflate-raw'))); } catch (_) { /* fall through */ }
    }
    return 'j=' + b64.enc(raw);
  }
  /** {hash, dropped}: uploaded logos ride along only while the hash stays under HASH_MAX. */
  async function encodeState() {
    const base = { v: 1, u: state.user, t: state.theme, w: state.widgets.map((w) => [w.id, w.kind, clean(w)]) };
    const f = {};
    for (const p of referenced()) if (files.has(p)) f[p] = files.get(p).text;
    if (!Object.keys(f).length) return { hash: await encodeJson(base), dropped: false };
    const full = await encodeJson(Object.assign({ f }, base));
    if (full.length + 1 <= HASH_MAX) return { hash: full, dropped: false };
    return { hash: await encodeJson(base), dropped: true };
  }
  function shareNote(dropped) {
    const n = $('#share-note');
    const notes = [];
    if (dropped) notes.push('Uploaded logos aren’t included in share links (too big); the link keeps the rest.');
    if (state.widgets.some((w) => w.kind === 'mixtape' && songs.has(w.opts.song))) notes.push('Uploaded songs are never included in share links.');
    n.hidden = !notes.length;
    n.textContent = notes.join(' ');
  }
  async function decodeState(hash) {
    const m = hash.replace(/^#/, '').match(/^([zj])=([A-Za-z0-9_-]+)$/);
    if (!m) return null;
    let bytes = b64.dec(m[2]);
    if (m[1] === 'z') {
      if (!canZip) throw new Error('this browser can’t unpack the link');
      bytes = await pipe(bytes, new DecompressionStream('deflate-raw'));
    }
    const d = JSON.parse(new TextDecoder().decode(bytes));
    if (!d || d.v !== 1 || !Array.isArray(d.w)) throw new Error('not a playground link');
    if (isTable(d.f)) {
      for (const [p, text] of Object.entries(d.f)) {
        if (LOGO_PATH_RE.test(p) && typeof text === 'string' && text.length <= LOGO_MAX) putFile(p, text);
      }
    }
    const taken = [];
    const widgets = [];
    for (const [id, kind, opts] of d.w.slice(0, 40)) {
      if (!specs[kind] && kind !== 'text') continue;
      const wid = ID_RE.test(String(id)) && !taken.includes(String(id)) ? String(id) : freeId(kind, taken);
      taken.push(wid);
      const w = newWidget(kind, wid);
      w.opts = Object.assign(baseDefaults(kind), opts && typeof opts === 'object' ? opts : {});
      widgets.push(w);
    }
    return { user: USER_RE.test(d.u || '') ? d.u : 'octocat', theme: String(d.t || 'komik'), widgets };
  }
  let hashTimer = null;
  function saveHashSoon() {
    clearTimeout(hashTimer);
    hashTimer = setTimeout(async () => {
      const { hash, dropped } = await encodeState();
      shareNote(dropped);
      if (location.hash !== '#' + hash) history.replaceState(null, '', '#' + hash);
    }, 600);
  }
  $('#share').addEventListener('click', async () => {
    const { hash, dropped } = await encodeState();
    const url = location.href.split('#')[0] + '#' + hash;
    history.replaceState(null, '', url);
    shareNote(dropped);
    const ok = await copy(url);
    announceOut(!ok ? 'Couldn’t copy; the link is in the address bar.'
      : dropped ? 'Share link copied. Uploaded logos aren’t included in share links (too big).'
        : 'Share link copied. It holds your whole design.');
  });
  $('#reset').addEventListener('click', () => {
    loadState(defaultState());
    openSet.clear();
    if (state.widgets[0]) openSet.add(state.widgets[0].uid);
    rebuildAll();
    announceOut('Back to the starter profile.');
  });

  // ------------------------------------------------------------------ page chrome
  function applyPageTheme(v) {
    if (v === 'light' || v === 'dark') document.documentElement.dataset.theme = v;
    else delete document.documentElement.dataset.theme;
  }
  const savedPage = store.get('page') || 'auto';
  applyPageTheme(savedPage);
  document.querySelectorAll('input[name="page-theme"]').forEach((r) => {
    r.checked = r.value === savedPage;
    r.addEventListener('change', () => { applyPageTheme(r.value); store.set('page', r.value); });
  });
  const savedView = store.get('view') || 'both';
  document.querySelectorAll('input[name="view"]').forEach((r) => {
    r.checked = r.value === savedView;
    r.addEventListener('change', () => { $('#pages').dataset.view = r.value; store.set('view', r.value); });
  });
  $('#pages').dataset.view = savedView;

  // ------------------------------------------------------------------ start
  function defaultState() {
    return {
      user: 'octocat',
      theme: 'komik',
      widgets: [
        newWidget('hero', 'hello'),
        Object.assign(newWidget('text', 'text', { md: defaultText('octocat') }), { auto: true }),
        newWidget('divider', 'line', { style: 'kawung' }),
        newWidget('heading', 'stack-title'),
        newWidget('stack', 'stack'),
        newWidget('footer', 'bye'),
      ].filter((w) => specs[w.kind] || w.kind === 'text'),
    };
  }
  function loadState(s) {
    for (const c of cache.values()) revoke(c);
    cache.clear();
    pending.clear();
    state.user = s.user;
    state.theme = s.theme;
    state.widgets = s.widgets;
  }
  function rebuildAll() {
    gcFiles();
    $('#user').value = state.user;
    buildThemes();
    buildAdd();
    buildList();
    buildPreview();
    refreshOutputs();
    flush();
  }

  async function start() {
    try {
      const r = await fetch('gallery.json');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      gallery = await r.json();
    } catch (err) {
      setLoading(`Couldn’t load gallery.json (${err.message}); waiting for the renderer instead.`);
    }
    gallery.themes = gallery.themes || [];
    if (!gallery.themes.length) gallery.themes = ['komik'];
    specs = gallery.widgets || {};
    if (!Object.keys(specs).length) {      // no gallery: still offer the built-in kinds
      for (const k of KIND_ORDER) specs[k] = { defaults: {}, doc: '' };
    }
    let s = null;
    if (location.hash.length > 1) {
      try { s = await decodeState(location.hash); } catch (err) {
        announceOut(`Couldn’t read the shared link (${err.message}); starting fresh.`);
      }
    }
    loadState(s || defaultState());
    if (state.widgets[0]) openSet.add(state.widgets[0].uid);
    rebuildAll();
  }
  start();
})();
