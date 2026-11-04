/* The native dialog supplies focus containment, Escape, and focus restoration. */
(() => {
  const drawer = document.querySelector('#qt-navigation');
  const menuTrigger = document.querySelector('[data-qt-menu]');
  const searchToggle = document.querySelector('#__search');
  let searchTrigger;
  if (!drawer) return;

  // Instant navigation replaces head metadata, while the shared header stays mounted.
  window.document$?.subscribe(() => {
    document.querySelectorAll('[data-qt-language]').forEach((link) => {
      const alternate = document.querySelector(`link[rel="alternate"][hreflang="${link.dataset.qtLanguage}"]`);
      if (alternate) link.href = alternate.href;
    });
  });

  document.addEventListener('click', (event) => {
    const target = event.target.closest('button, a');
    if (!target) return;

    if (target.matches('[data-qt-language]')) {
      const destination = new URL(target.href);
      destination.hash = window.location.hash;
      target.href = destination.href;
      return;
    }

    if (target.matches('[data-qt-menu]')) {
      drawer.showModal();
      menuTrigger.setAttribute('aria-expanded', 'true');
    } else if (target.matches('[data-qt-close]')) {
      drawer.close();
    } else if (target.matches('[data-qt-search]')) {
      if (drawer.open) drawer.close();
      searchTrigger = drawer.contains(target) ? menuTrigger : target;
      searchToggle.checked = true;
      searchToggle.dispatchEvent(new Event('change', { bubbles: true }));
      requestAnimationFrame(() => document.querySelector('[data-md-component="search-query"]').focus());
    } else if (target.matches('[data-qt-theme]')) {
      document.querySelector('.qt-header [data-md-component="palette"] label:not([hidden])').click();
    } else if (target.matches('[data-qt-play]')) {
      const video = target.previousElementSibling;
      video.focus();
      video.play();
    } else if (drawer.open && drawer.contains(target) && target.matches('a')) {
      drawer.close();
    }
  });

  // play does not bubble; capture also catches the video's native controls.
  document.addEventListener('play', (event) => {
    const button = event.target.parentElement.querySelector('[data-qt-play]');
    if (button) button.hidden = true;
  }, true);

  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey &&
        !event.target.closest('input, textarea, [contenteditable]') && !drawer.open) {
      event.preventDefault();
      document.querySelector('.qt-header [data-qt-search]').click();
    }
  });

  drawer.addEventListener('click', (event) => {
    if (event.target !== drawer) return;
    const bounds = drawer.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) drawer.close();
  });
  searchToggle.addEventListener('change', () => {
    if (!searchToggle.checked && searchTrigger) searchTrigger.focus();
  });
  drawer.addEventListener('close', () => menuTrigger.setAttribute('aria-expanded', 'false'));
  window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024 && drawer.open) drawer.close();
  });
})();
