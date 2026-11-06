/* The native dialog supplies focus containment, Escape, and focus restoration. */
(() => {
  const drawer = document.querySelector('#qt-navigation');
  const menuTrigger = document.querySelector('[data-qt-menu]');
  const searchToggle = document.querySelector('#__search');
  let searchTrigger;

  // Instant navigation replaces head metadata, while the shared header stays mounted.
  window.document$?.subscribe(updateLanguageLinks);
  window.location$?.subscribe(updateLanguageLinks);
  window.addEventListener('hashchange', updateLanguageLinks);
  updateLanguageLinks();

  document.addEventListener('click', (event) => {
    document.querySelectorAll('.qt-language-switch[open]').forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('.qt-language-switch[open]').forEach((menu) => {
      menu.open = false;
      menu.querySelector('summary').focus();
    });
  });

  if (!drawer) return;

  // Material leaves the header and search runtime mounted during instant navigation.
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link) return;
    const destination = new URL(link.href);
    if (destination.origin !== window.location.origin) return;
    const prefix = destination.pathname.match(/^\/(ko|ja|zh)(?:\/|$)/)?.[1] || 'en';
    const locale = prefix === 'zh' ? 'zh-CN' : prefix;
    if (locale !== document.documentElement.lang && !link.hasAttribute('target')) {
      link.target = '_self';
    }
  }, true);

  document.addEventListener('click', (event) => {
    const target = event.target.closest('button, a');
    if (!target) return;

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

  function updateLanguageLinks() {
    document.querySelectorAll('[data-qt-language]').forEach((link) => {
      const current = link.dataset.qtLanguage === document.documentElement.lang;
      if (current) {
        link.setAttribute('aria-current', 'page');
        const menu = link.closest('.qt-language-switch');
        menu.querySelector('[data-qt-language-current]').textContent = link.textContent;
        menu.querySelector('summary').setAttribute('aria-label',
          `${menu.querySelector('nav').getAttribute('aria-label')}: ${link.textContent}`);
      } else {
        link.removeAttribute('aria-current');
      }
      const alternate = document.querySelector(`link[rel="alternate"][hreflang="${link.dataset.qtLanguage}"]`);
      if (!alternate) return;
      const destination = new URL(alternate.href);
      destination.search = window.location.search;
      destination.hash = window.location.hash;
      link.href = destination.href;
    });
  }
})();
