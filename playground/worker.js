/* Pernik playground worker: runs Pernik (Python) with Pyodide off the main thread.

   page -> worker                          worker -> page
   {type:'init'}                           {type:'status', text}  while loading
                                           {type:'ready', version, python, pyodide}
   {type:'demo', secs}                     the demo song's length (measured by the page)
   {type:'file', path, text|null}          an uploaded logo (assets/logos/*.svg), or remove it
   {type:'render', uid, key, payload}      {type:'rendered', uid, key, result}
   {type:'zip', toml, readme, user}        {type:'zip', bytes, info} or {type:'zip', error}
                                           {type:'fatal', text}  if loading failed

   Renders run one at a time. A newer render for the same widget replaces one still waiting.
   Started as a module worker: new Worker('worker.js', {type: 'module'}). */

const PYODIDE_VERSION = '314.0.7';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const HOME = '/lib/pernik-web';

let py = null;
let bridge = null;
let ready = null;
const queue = [];
let busy = false;
let demo = null;      // Uint8Array of demo.mp3 once loaded
let demoSecs = 0;

const post = (msg, transfer) => self.postMessage(msg, transfer || []);
const status = (text) => post({ type: 'status', text });

async function init() {
  status('downloading Python (about 12 MB, first time only)…');
  // a module worker with import(): pyodide.mjs then loads the rest with import() too, which works
  // in browsers (and embedded browser panes) that refuse cross-origin importScripts()
  const { loadPyodide } = await import(PYODIDE_URL + 'pyodide.mjs');
  const [pyodide, zip, src] = await Promise.all([
    loadPyodide({ indexURL: PYODIDE_URL }),
    grab('pernik.zip').then((r) => r.arrayBuffer()),
    grab('bridge.py').then((r) => r.text()),
  ]);
  py = pyodide;
  status('unpacking Pernik…');
  py.FS.mkdirTree(HOME);
  py.unpackArchive(zip, 'zip', { extractDir: HOME });
  py.FS.writeFile(HOME + '/pernik_bridge.py', src);
  py.runPython(`import sys\nif ${JSON.stringify(HOME)} not in sys.path: sys.path.insert(0, ${JSON.stringify(HOME)})`);
  bridge = py.pyimport('pernik_bridge');
  const info = JSON.parse(bridge.setup());
  post({ type: 'ready', version: info.version, python: info.python, pyodide: PYODIDE_VERSION });
}

async function grab(name) {
  const r = await fetch(new URL(name, self.location));
  if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
  return r;
}

self.onmessage = (e) => {
  const m = e.data || {};
  if (m.type === 'init') {
    if (!ready) {
      ready = init().then(() => true, (err) => {
        console.error(err);
        post({ type: 'fatal', text: String((err && err.message) || err).split('\n').slice(-3).join(' ') });
        return false;
      });
    }
    return;
  }
  if (m.type === 'render') {
    // drop a waiting render of the same widget and queue this one last, so it runs after
    // any file messages (uploaded logos) sent before it
    const i = queue.findIndex((q) => q.type === 'render' && q.uid === m.uid);
    if (i >= 0) queue.splice(i, 1);
    queue.push(m);
  } else {
    queue.push(m);
  }
  pump();
};

async function pump() {
  if (busy || !ready) return;
  busy = true;
  try {
    if (!(await ready)) { queue.length = 0; return; }
    while (queue.length) {
      const m = queue.shift();
      try {
        await handle(m);
      } catch (err) {
        const text = String((err && err.message) || err).trim().split('\n').slice(-1)[0];
        if (m.type === 'render') post({ type: 'rendered', uid: m.uid, key: m.key, result: { error: text, logs: [] } });
        else if (m.type === 'zip') post({ type: 'zip', error: text });
      }
      // let new messages in (and replace queued renders) between widgets
      await new Promise((r) => setTimeout(r, 0));
    }
  } finally {
    busy = false;
  }
}

async function handle(m) {
  const needsSong = (m.type === 'render' && m.payload.widget.kind === 'mixtape') ||
    (m.type === 'zip' && /kind\s*=\s*"mixtape"/.test(m.toml));
  if (needsSong && !demo) {
    demo = new Uint8Array(await (await grab('demo.mp3')).arrayBuffer());
    bridge.set_demo(demo, demoSecs);
  }
  if (m.type === 'render') {
    const result = JSON.parse(bridge.render(JSON.stringify(m.payload)));
    post({ type: 'rendered', uid: m.uid, key: m.key, result });
  } else if (m.type === 'file') {
    bridge.put_file(m.path, m.text === undefined ? null : m.text);
  } else if (m.type === 'demo') {
    demoSecs = m.secs || 0;
    if (demo) bridge.set_demo(demo, demoSecs);
  } else if (m.type === 'zip') {
    const proxy = bridge.make_zip(m.toml, m.readme, m.user);
    const bytes = proxy.toJs();
    proxy.destroy();
    const info = JSON.parse(bridge.last_build());
    post({ type: 'zip', bytes, info }, [bytes.buffer]);
  }
}
