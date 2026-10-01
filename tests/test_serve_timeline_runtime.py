"""Browser-independent event tests for the timeline's latest-only request queue."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

RUNTIME = Path("quickthumb/html/serve_timeline.js")

HARNESS = r"""
const vm = require('node:vm');
const assert = require('node:assert/strict');
const runtime = __RUNTIME__;
function setup(hash = '') {
  class Element {
    constructor() { this.textContent = ''; this.value = ''; this.style = {}; this.dataset = {};
      this.children = []; this.listeners = {}; this.attributes = {}; this.disabled = true; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    appendChild(child) { this.children.push(child); return child; }
    setAttribute(key, value) { this.attributes[key] = value; }
    dispatch(name, value) { if (value !== undefined) this.value = value; this.listeners[name]({}); }
  }
  const elements = {}, events = {}, requests = [], decodes = [], revoked = [];
  let reloads = 0, urlCount = 0;
  function el(id) { return elements['qt-' + id] ||= new Element(); }
  el('config').textContent = JSON.stringify({metadata_url: '/meta', frame_url: '/frame'});
  const location = {hash, reload() { reloads++; }};
  const ctx = {console, URLSearchParams, Number, String, JSON, Error, Math,
    document: {getElementById(id) { return elements[id] ||= new Element(); },
      createElement() { return new Element(); }},
    window: {addEventListener(name, callback) { events[name] = callback; }},
    location, history: {replaceState(a, b, next) { location.hash = next; }},
    URL: {createObjectURL() { return 'blob:' + (++urlCount); },
      revokeObjectURL(url) { revoked.push(url); }},
    Image: class { decode() {
      return new Promise((resolve, reject) => decodes.push({resolve, reject})); }},
    fetch(url) { return new Promise((resolve, reject) => requests.push({url, resolve, reject})); }
  };
  vm.runInNewContext(runtime, ctx);
  const metadata = {version: '1:2:0', duration: 3, width: 1080, height: 1920,
    proxy_width: 360, proxy_height: 640, warnings: ['Proxy is approximate'],
    segments: [{slide: 0, start: 0, transition_end: 0, animation_end: 1, end: 3}]};
  function respond(index, options = {}) {
    const code = options.status || 200;
    requests[index].resolve({status: code, ok: code < 400,
      text: async () => options.text || 'Failure <script>',
      json: async () => options.metadata || metadata,
      blob: async () => ({}), headers: {get(name) { return name === 'X-Quickthumb-Time'
        ? String(options.time || 0) : String(options.slide || 0); }}});
  }
  return {el, events, requests, decodes, revoked, location, metadata, respond,
    get reloads() { return reloads; }};
}
async function flush() { for (let i = 0; i < 12; i++) await Promise.resolve(); }
async function load(state, metadata) { state.respond(0, {metadata}); await flush(); }
async function display(state, index, options = {}) {
  state.respond(index, options); await flush(); state.decodes.at(-1).resolve(); await flush();
}
function query(state, index, key) {
  return new URL(state.requests[index].url, 'http://localhost').searchParams.get(key);
}
async function test(name) {
  if (name === 'latest_queue') {
    const s = setup(); await load(s);
    assert.equal(s.requests.length, 2);
    s.el('seek').dispatch('input', '.1'); s.el('seek').dispatch('input', '.9');
    assert.equal(s.requests.length, 2);
    s.respond(1); await flush();
    assert.equal(s.decodes.length, 0); assert.equal(s.requests.length, 3);
    assert.equal(query(s, 2, 'time'), '0.9');
    await display(s, 2, {time: .9});
    assert.match(s.el('displayed').textContent, /Displayed: 0.9s/);
    assert.equal(s.el('status').textContent, 'Ready');
    assert.equal(s.el('stage').attributes['aria-busy'], 'false');
  } else if (name === 'stale_decode_resolution') {
    const s = setup(); await load(s); s.respond(1); await flush();
    s.el('resolution').dispatch('change', 'full');
    s.decodes[0].resolve(); await flush();
    assert.equal(s.el('frame').src, undefined); assert.deepEqual(s.revoked, ['blob:1']);
    assert.equal(query(s, 2, 'resolution'), 'full');
    await display(s, 2); assert.match(s.el('displayed').textContent, /Full/);
    assert.equal(s.el('frame').src, 'blob:2');
  } else if (name === 'error_retry') {
    const s = setup(); await load(s); await display(s, 1);
    const old = s.el('frame').src;
    s.el('seek').dispatch('input', '.5'); s.respond(2, {status: 500}); await flush();
    assert.equal(s.requests.length, 3); assert.equal(s.el('frame').src, old);
    assert.equal(s.el('status').dataset.error, 'true');
    assert.match(s.el('status').textContent, /Failure <script>/);
    assert.match(s.el('displayed').textContent, /Displayed: 0s/);
    s.el('time').dispatch('change', '.5'); await display(s, 3, {time: .5});
    assert.equal(s.el('status').textContent, 'Ready'); assert.deepEqual(s.revoked, [old]);
  } else if (name === 'decode_error') {
    const s = setup(); await load(s); s.respond(1); await flush();
    s.decodes[0].reject(new Error('Cannot decode')); await flush();
    assert.equal(s.el('status').dataset.error, 'true'); assert.deepEqual(s.revoked, ['blob:1']);
    assert.equal(s.requests.length, 2);
  } else if (name === 'stale_version') {
    const s = setup('#t=2&resolution=full'); await load(s);
    assert.equal(query(s, 1, 'version'), s.metadata.version);
    s.respond(1, {status: 409}); await flush();
    assert.equal(s.reloads, 1); assert.equal(s.requests.length, 2);
    assert.equal(s.location.hash, '#t=2&resolution=full');
    s.el('seek').dispatch('input', '1'); assert.equal(s.requests.length, 2);
  } else if (name === 'hash_navigation') {
    const s = setup('#t=999&resolution=full'); await load(s);
    assert.equal(query(s, 1, 'time'), '3'); assert.equal(query(s, 1, 'resolution'), 'full');
    await display(s, 1, {time: 3});
    s.location.hash = '#t=0.125&resolution=proxy'; s.events.hashchange({});
    assert.equal(query(s, 2, 'time'), '0.125');
    await display(s, 2, {time: .125});
    s.location.hash = '#t=NaN&resolution=invalid'; s.events.hashchange({});
    assert.equal(query(s, 3, 'time'), '0'); assert.equal(query(s, 3, 'resolution'), 'proxy');
  } else if (name === 'zero_duration_boundaries') {
    const s = setup('#t=-1'); s.metadata.duration = 0;
    s.metadata.segments = [{slide:0, start:0, transition_end:0, animation_end:0, end:0}];
    await load(s); assert.equal(query(s, 1, 'time'), '0');
    assert.equal(s.el('seek').max, '0'); assert.equal(s.el('controls').disabled, false);
    for (const band of s.el('segments').children[0].children) assert.equal(band.style.width, '0%');
    await display(s, 1);
    s.el('marks').children.at(-1).dispatch('click'); assert.equal(query(s, 2, 'time'), '0');
  } else if (name === 'metadata_failure') {
    const s = setup(); s.respond(0, {status: 500, text:'Bad source'}); await flush();
    assert.equal(s.el('controls').disabled, true); assert.equal(s.requests.length, 1);
    assert.match(s.el('status').textContent, /Bad source/);
  } else if (name === 'navigation_cleanup') {
    const s = setup(); await load(s); await display(s, 1);
    s.el('seek').dispatch('input', '.5'); s.respond(2); await flush();
    s.events.pagehide({}); s.decodes.at(-1).resolve(); await flush();
    assert.deepEqual(s.revoked, ['blob:1', 'blob:2']);
    assert.match(s.el('displayed').textContent, /Displayed: 0s/);
    s.events.pageshow({persisted: true}); assert.equal(s.reloads, 1);
  } else if (name === 'stale_error') {
    const s = setup(); await load(s); s.el('seek').dispatch('input', '.5');
    s.respond(1, {status: 500}); await flush();
    assert.equal(s.el('status').dataset.error, 'false');
    assert.equal(query(s, 2, 'time'), '0.5'); await display(s, 2, {time:.5});
  } else throw new Error('Unknown test: ' + name);
}
test(__SCENARIO__).then(() => console.log('passed')).catch(error => {
  console.error(error); process.exit(1);
});
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js runs browser runtime checks")
@pytest.mark.parametrize(
    "scenario",
    [
        "latest_queue",
        "stale_decode_resolution",
        "error_retry",
        "decode_error",
        "stale_version",
        "hash_navigation",
        "zero_duration_boundaries",
        "metadata_failure",
        "navigation_cleanup",
        "stale_error",
    ],
)
def test_timeline_browser_runtime(scenario):
    script = HARNESS.replace(
        "__RUNTIME__", json.dumps(RUNTIME.read_text(encoding="utf-8"))
    ).replace("__SCENARIO__", json.dumps(scenario))
    result = subprocess.run(["node", "-"], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "passed"
