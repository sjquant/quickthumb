(function () {
  'use strict';
  const config = JSON.parse(document.getElementById('qt-config').textContent);
  const element = id => document.getElementById('qt-' + id);
  const controls = element('controls'), seek = element('seek'), time = element('time');
  const resolution = element('resolution'), status = element('status');
  const frame = element('frame'), stage = element('stage');
  let metadata = null, desired = null, serial = 0, busy = false, stopped = false;
  let displayedUrl = null;
  const seconds = value => Number(value.toFixed(3)).toString();

  function message(text, error) {
    status.textContent = text;
    status.dataset.error = error ? 'true' : 'false';
  }
  function readHash() {
    const values = new URLSearchParams(location.hash.slice(1));
    const value = Number(values.get('t') || 0);
    return {time: Number.isFinite(value) ? value : 0,
      resolution: values.get('resolution') === 'full' ? 'full' : 'proxy'};
  }
  function request(value, mode) {
    if (!metadata || stopped) return;
    const instant = Math.min(metadata.duration, Math.max(0, Number.isFinite(value) ? value : 0));
    desired = {time: instant, resolution: mode === 'full' ? 'full' : 'proxy', serial: ++serial};
    seek.value = String(instant);
    time.value = seconds(instant);
    resolution.value = desired.resolution;
    history.replaceState(null, '', '#t=' + instant + '&resolution=' + desired.resolution);
    message('Rendering ' + seconds(instant) + 's…');
    stage.setAttribute('aria-busy', 'true');
    pump();
  }
  async function pump() {
    if (busy || !desired || stopped) return;
    busy = true;
    const current = desired;
    let candidateUrl = null;
    try {
      const params = new URLSearchParams({time: String(current.time),
        resolution: current.resolution, version: metadata.version});
      const response = await fetch(config.frame_url + '?' + params, {cache: 'no-store'});
      if (response.status === 409) {
        stopped = true;
        location.reload();
        return;
      }
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob();
      if (stopped || desired.serial !== current.serial) return;
      candidateUrl = URL.createObjectURL(blob);
      const candidate = new Image();
      candidate.src = candidateUrl;
      await candidate.decode();
      if (stopped || desired.serial !== current.serial) return;
      frame.src = candidateUrl;
      if (displayedUrl) URL.revokeObjectURL(displayedUrl);
      displayedUrl = candidateUrl;
      candidateUrl = null;
      const sampled = Number(response.headers.get('X-Quickthumb-Time'));
      const slide = Number(response.headers.get('X-Quickthumb-Slide'));
      element('displayed').textContent = 'Displayed: ' + seconds(sampled) + 's · Slide ' +
        (slide + 1) + ' · ' + (current.resolution === 'full' ? 'Full' : 'Proxy');
      message('Ready');
    } catch (error) {
      if (!stopped && desired.serial === current.serial) {
        message('Could not render: ' + error.message + ' · Change the time to retry.', true);
      }
    } finally {
      if (candidateUrl) URL.revokeObjectURL(candidateUrl);
      busy = false;
      if (!stopped && desired.serial !== current.serial) pump();
      else stage.setAttribute('aria-busy', 'false');
    }
  }
  function boundary(label, instant) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = label + ' · ' + seconds(instant) + 's';
    button.addEventListener('click', () => request(instant, resolution.value));
    element('marks').appendChild(button);
  }
  function showSegments() {
    for (const segment of metadata.segments) {
      const length = segment.end - segment.start;
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'segment';
      button.style.flex = String(Math.max(length, 0.000001));
      button.textContent = String(segment.slide + 1);
      button.title = 'Slide ' + (segment.slide + 1) + ': ' + seconds(segment.start) + '–' + seconds(segment.end) + 's';
      button.setAttribute('aria-label', button.title);
      for (const [end, color] of [[segment.animation_end, '#2878b2'], [segment.transition_end, '#8869cd']]) {
        const band = document.createElement('span');
        band.style.width = (length > 0 ? Math.min(100, Math.max(0, (end - segment.start) / length * 100)) : 0) + '%';
        band.style.background = color;
        button.appendChild(band);
      }
      button.addEventListener('click', () => request(segment.start, resolution.value));
      element('segments').appendChild(button);
      boundary('Slide ' + (segment.slide + 1), segment.start);
      if (segment.transition_end > segment.start) boundary('Transition end', segment.transition_end);
      if (segment.animation_end > segment.start) boundary('Motion end', segment.animation_end);
    }
    boundary('End', metadata.duration);
  }
  seek.addEventListener('input', () => request(Number(seek.value), resolution.value));
  time.addEventListener('change', () => request(Number(time.value), resolution.value));
  resolution.addEventListener('change', () => request(desired ? desired.time : 0, resolution.value));
  window.addEventListener('hashchange', () => {
    const saved = readHash();
    request(saved.time, saved.resolution);
  });
  window.addEventListener('pagehide', () => {
    stopped = true;
    if (displayedUrl) URL.revokeObjectURL(displayedUrl);
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) location.reload();
  });
  fetch(config.metadata_url, {cache: 'no-store'}).then(async response => {
    if (!response.ok) throw new Error(await response.text());
    metadata = await response.json();
    if (stopped) return;
    seek.max = time.max = String(metadata.duration);
    element('duration').textContent = seconds(metadata.duration) + 's total · ' + metadata.width + ' × ' + metadata.height;
    for (const warning of metadata.warnings) {
      const item = document.createElement('li');
      item.textContent = warning;
      element('notes').appendChild(item);
    }
    showSegments();
    controls.disabled = false;
    const saved = readHash();
    request(saved.time, saved.resolution);
  }).catch(error => {
    message('Could not load timeline: ' + error.message + ' · Save the source or reload to retry.', true);
    stage.setAttribute('aria-busy', 'false');
  });
})();
