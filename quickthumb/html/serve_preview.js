(function () {
  'use strict';
  const config = JSON.parse(document.getElementById('qt-config').textContent);
  const element = id => document.getElementById('qt-' + id);
  const controls = element('controls'), seek = element('seek'), time = element('time');
  const resolution = element('resolution'), status = element('status');
  const frame = element('frame'), stage = element('stage'), presentation = element('presentation');
  const seconds = value => Number(value.toFixed(3)).toString();
  const saved = readHash();
  let selected = saved.slide, mode = saved.mode;
  let metadata = null, metadataRequest = null, desired = null;
  let serial = 0, busy = false, stopped = false, displayedUrl = null, slideObserver = null;
  let embeddedDocument = null;

  buildThumbnails();
  resolution.value = saved.resolution;
  element('mode-presentation').addEventListener('click', () => setMode('presentation'));
  element('mode-inspect').addEventListener('click', () => setMode('inspect'));
  element('motion-hint').addEventListener('click', () => setMode('inspect'));
  element('previous').addEventListener('click', () => selectSlide(selected - 1));
  element('next').addEventListener('click', () => selectSlide(selected + 1));
  element('present').addEventListener('click', () => {
    setMode('presentation');
    if (stage.requestFullscreen) stage.requestFullscreen().catch(() => {
      message('Fullscreen could not open. The presentation is still available here.', true);
    });
  });
  presentation.addEventListener('load', connectPresentation);
  seek.addEventListener('input', () => request(Number(seek.value), resolution.value));
  time.addEventListener('change', () => request(Number(time.value), resolution.value));
  resolution.addEventListener('change', () => request(desired ? desired.time : 0, resolution.value));
  window.addEventListener('hashchange', () => {
    const next = readHash();
    selected = next.slide;
    setMode(next.mode, next.time, next.resolution);
  });
  window.addEventListener('keydown', event => {
    if (event.target && event.target.closest('input, select, button, a, summary')) return;
    if (!['ArrowRight', 'ArrowLeft', ' '].includes(event.key)) return;
    event.preventDefault();
    if (mode === 'presentation' && embeddedDocument) {
      embeddedDocument.dispatchEvent(new KeyboardEvent('keydown', {key: event.key, bubbles: true}));
      if (config.slides.length === 1 && event.key !== 'ArrowLeft') {
        embeddedDocument.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      }
    } else if (event.key !== ' ') selectSlide(selected + (event.key === 'ArrowLeft' ? -1 : 1));
  });
  window.addEventListener('qt:source-status', event => {
    const live = element('live');
    live.dataset.error = event.detail ? 'false' : 'true';
    const label = live.querySelector('span'), text = event.detail ? 'Live' : 'Reconnecting';
    if (label.textContent !== text) label.textContent = text;
  });
  window.addEventListener('resize', fitStage);
  if (window.ResizeObserver) new ResizeObserver(fitStage).observe(element('viewport'));
  window.addEventListener('pagehide', () => {
    stopped = true;
    if (displayedUrl) URL.revokeObjectURL(displayedUrl);
    if (slideObserver) slideObserver.disconnect();
  });
  window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
  setMode(mode, saved.time, saved.resolution);

  function readHash() {
    const values = new URLSearchParams(location.hash.slice(1));
    const slide = Number(values.get('slide') || 0), value = Number(values.get('t'));
    return {
      slide: Number.isInteger(slide) ? Math.min(config.slides.length - 1, Math.max(0, slide)) : 0,
      time: values.has('t') ? (Number.isFinite(value) ? Math.max(0, value) : 0) : null,
      mode: values.has('mode') ? (values.get('mode') === 'inspect' ? 'inspect' : 'presentation') : config.mode,
      resolution: values.get('resolution') === 'full' ? 'full' : 'proxy'
    };
  }
  function remember() {
    const values = new URLSearchParams({slide: String(selected), mode,
      resolution: resolution.value || 'proxy'});
    if (desired) values.set('t', String(desired.time));
    history.replaceState(null, '', (mode === 'inspect' ? '/timeline' : '/') + '#' + values);
  }
  function setMode(next, instant = null, quality = resolution.value) {
    mode = next;
    serial++;
    document.body.dataset.mode = mode;
    element('inspector').hidden = mode !== 'inspect';
    presentation.hidden = mode === 'inspect';
    frame.hidden = mode !== 'inspect';
    for (const value of ['presentation', 'inspect']) {
      element('mode-' + value).setAttribute('aria-pressed', String(mode === value));
    }
    updateSelection();
    remember();
    if (mode === 'inspect') {
      message('Loading rendered timeline…');
      ensureMetadata().then(() => {
        if (mode !== 'inspect' || stopped) return;
        const segment = metadata.segments[selected];
        const prior = desired && slideAt(desired.time) === selected ? desired.time : null;
        request(instant === null ? (prior === null ? segment.transition_end : prior) : instant, quality);
      }).catch(error => message('Could not load timeline: ' + error.message + ' · Save the source or reload to retry.', true));
    } else {
      if (!presentation.getAttribute('src')) {
        message('Loading presentation…');
        presentation.src = config.presentation_url;
      } else {
        navigatePresentation();
        message('Ready');
      }
      stage.setAttribute('aria-busy', 'false');
    }
    fitStage();
  }
  function buildThumbnails() {
    config.slides.forEach((slide, index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'slide-button';
      button.setAttribute('aria-label', 'Slide ' + (index + 1));
      const number = document.createElement('span');
      number.className = 'slide-number'; number.textContent = String(index + 1).padStart(2, '0');
      const thumbnail = document.createElement('span'); thumbnail.className = 'thumbnail';
      const image = document.createElement('img'); image.alt = ''; image.loading = 'lazy';
      image.src = config.thumbnail_url + '?' + new URLSearchParams({slide: String(index), version: config.version});
      image.addEventListener('error', () => { image.hidden = true; });
      thumbnail.appendChild(image); button.appendChild(number); button.appendChild(thumbnail);
      button.addEventListener('click', () => selectSlide(index));
      element('thumbnails').appendChild(button);
    });
  }
  function selectSlide(index) {
    selected = Math.min(config.slides.length - 1, Math.max(0, index));
    updateSelection();
    if (mode === 'inspect' && metadata) request(metadata.segments[selected].transition_end, resolution.value);
    else if (mode === 'presentation') navigatePresentation();
    remember();
  }
  function updateSelection() {
    element('count').textContent = 'Slide ' + (selected + 1) + ' of ' + config.slides.length;
    element('previous').disabled = selected === 0;
    element('next').disabled = selected === config.slides.length - 1;
    Array.from(element('thumbnails').children).forEach((button, index) => {
      button.setAttribute('aria-current', String(index === selected));
    });
    const slide = config.slides[selected];
    element('motion-hint').hidden = !slide.static_motion || mode === 'inspect';
    const notes = slide.motion_notes;
    element('motion-notice').hidden = !notes.length;
    element('fallback-summary').textContent = notes[0] || '';
    element('fallback-notes').replaceChildren();
    for (const note of notes) {
      const item = document.createElement('li'); item.textContent = note;
      element('fallback-notes').appendChild(item);
    }
    if (metadata) {
      Array.from(element('segments').children).forEach((button, index) => {
        button.setAttribute('aria-current', String(index === selected));
      });
      showBoundaries();
    }
    fitStage();
  }
  function fitStage() {
    const viewer = element('viewport');
    const width = viewer.clientWidth - (viewer.clientWidth <= 650 ? 24 : 44);
    const height = viewer.clientHeight - (viewer.clientWidth <= 650 ? 24 : 44);
    if (!(width > 0 && height > 0)) return;
    const size = mode === 'inspect' && metadata ? metadata : config.slides[selected];
    const ratio = size.width / size.height;
    const fittedWidth = Math.min(width, height * ratio);
    stage.style.width = fittedWidth + 'px';
    stage.style.height = fittedWidth / ratio + 'px';
  }
  function connectPresentation() {
    if (!presentation.getAttribute('src')) return;
    if (slideObserver) slideObserver.disconnect();
    embeddedDocument = presentation.contentDocument;
    if (!embeddedDocument || !embeddedDocument.querySelector('.qt-stage')) {
      message('The HTML presentation could not load. Inspect rendered frames or save the source to retry.', true);
      return;
    }
    const stages = Array.from(embeddedDocument.querySelectorAll('.qt-stage'));
    const observe = () => {
      if (mode !== 'presentation') return;
      const visible = stages.filter(item => !item.hidden && item.style.display !== 'none');
      if (visible.length !== 1) return;
      const index = stages.indexOf(visible[0]);
      if (index !== selected) { selected = index; updateSelection(); remember(); }
    };
    slideObserver = new MutationObserver(observe);
    for (const slide of stages) slideObserver.observe(slide, {attributes: true, attributeFilter: ['hidden', 'style']});
    navigatePresentation();
    message('Ready');
  }
  function navigatePresentation() {
    if (!embeddedDocument) return;
    embeddedDocument.dispatchEvent(new CustomEvent('qt:preview-select', {detail: selected}));
  }
  function message(text, error) {
    status.textContent = text;
    status.hidden = text === 'Ready';
    status.dataset.error = error ? 'true' : 'false';
  }
  function slideAt(instant) {
    for (let index = metadata.segments.length - 1; index >= 0; index--) {
      if (instant >= metadata.segments[index].start) return index;
    }
    return 0;
  }
  function request(value, quality) {
    if (!metadata || stopped || mode !== 'inspect') return;
    const instant = Math.min(metadata.duration, Math.max(0, Number.isFinite(value) ? value : 0));
    desired = {time: instant, resolution: quality === 'full' ? 'full' : 'proxy', serial: ++serial};
    selected = slideAt(instant);
    seek.value = String(instant); time.value = seconds(instant); resolution.value = desired.resolution;
    updateSelection(); remember();
    message('Rendering ' + seconds(instant) + 's…');
    stage.setAttribute('aria-busy', 'true');
    pump();
  }
  async function pump() {
    if (busy || !desired || stopped || mode !== 'inspect') return;
    busy = true;
    const current = desired;
    let candidateUrl = null;
    try {
      const params = new URLSearchParams({time: String(current.time), resolution: current.resolution, version: metadata.version});
      const response = await fetch(config.frame_url + '?' + params, {cache: 'no-store'});
      if (response.status === 409) { stopped = true; location.reload(); return; }
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob();
      if (stopped || desired.serial !== current.serial || mode !== 'inspect') return;
      candidateUrl = URL.createObjectURL(blob);
      const candidate = new Image(); candidate.src = candidateUrl;
      await candidate.decode();
      if (stopped || desired.serial !== current.serial || mode !== 'inspect') return;
      frame.src = candidateUrl;
      if (displayedUrl) URL.revokeObjectURL(displayedUrl);
      displayedUrl = candidateUrl; candidateUrl = null;
      const sampled = Number(response.headers.get('X-Quickthumb-Time'));
      const slide = Number(response.headers.get('X-Quickthumb-Slide'));
      element('displayed').textContent = 'Displayed: ' + seconds(sampled) + 's · Slide ' +
        (slide + 1) + ' · ' + (current.resolution === 'full' ? 'Full' : 'Proxy');
      message('Ready');
    } catch (error) {
      if (!stopped && desired.serial === current.serial && mode === 'inspect') {
        message('Could not render: ' + error.message + ' · Change the time to retry.', true);
      }
    } finally {
      if (candidateUrl) URL.revokeObjectURL(candidateUrl);
      busy = false;
      if (!stopped && mode === 'inspect' && desired.serial !== current.serial) pump();
      else stage.setAttribute('aria-busy', 'false');
    }
  }
  function showBoundaries() {
    element('marks').replaceChildren();
    const segment = metadata.segments[selected];
    const boundaries = [['Slide start', segment.start]];
    if (segment.transition_end > segment.start) boundaries.push(['Transition end', segment.transition_end]);
    if (segment.animation_end > segment.transition_end) boundaries.push(['Motion end', segment.animation_end]);
    if (segment.end > segment.animation_end) boundaries.push(['Slide end', segment.end]);
    for (const [label, instant] of boundaries) {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = label + ' · ' + seconds(instant) + 's';
      button.addEventListener('click', () => request(instant, resolution.value));
      element('marks').appendChild(button);
    }
  }
  function showSegments() {
    for (const segment of metadata.segments) {
      const length = segment.end - segment.start;
      const button = document.createElement('button'); button.type = 'button'; button.className = 'segment';
      button.style.flex = String(Math.max(length, 0.000001)); button.textContent = String(segment.slide + 1);
      button.title = 'Slide ' + (segment.slide + 1) + ': ' + seconds(segment.start) + '–' + seconds(segment.end) + 's';
      button.setAttribute('aria-label', button.title);
      for (const [end, color] of [[segment.animation_end, '#82c8c3'], [segment.transition_end, '#b0a0d7']]) {
        const band = document.createElement('span');
        band.style.width = (length > 0 ? Math.min(100, Math.max(0, (end - segment.start) / length * 100)) : 0) + '%';
        band.style.background = color; button.appendChild(band);
      }
      button.addEventListener('click', () => request(segment.start, resolution.value));
      element('segments').appendChild(button);
    }
  }
  async function ensureMetadata() {
    if (metadata) return;
    if (metadataRequest) return metadataRequest;
    metadataRequest = (async () => {
      const response = await fetch(config.metadata_url, {cache: 'no-store'});
      if (!response.ok) throw new Error(await response.text());
      const result = await response.json();
      if (result.version !== config.version) { stopped = true; location.reload(); return; }
      metadata = result;
      seek.max = time.max = String(metadata.duration);
      element('duration').textContent = seconds(metadata.duration) + 's';
      for (const warning of metadata.warnings) {
        const item = document.createElement('li'); item.textContent = warning;
        element('notes').appendChild(item);
      }
      showSegments(); updateSelection(); controls.disabled = false;
    })();
    try { await metadataRequest; } finally { metadataRequest = null; }
  }
})();
