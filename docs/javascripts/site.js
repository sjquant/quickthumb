/* The native dialog supplies focus containment, Escape, and focus restoration. */
(() => {
  const drawer = document.querySelector('#qt-navigation');
  const menuTrigger = document.querySelector('[data-qt-menu]');
  const searchToggle = document.querySelector('#__search');
  let searchTrigger;

  document.addEventListener('click', async (event) => {
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
    } else if (target.matches('[data-qt-copy]')) {
      const status = target.parentElement.querySelector('[role="status"]');
      try {
        await navigator.clipboard.writeText(target.dataset.qtCopy);
        status.textContent = 'Copied';
        setTimeout(() => { status.textContent = ''; }, 2500);
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(target.parentElement.querySelector('code'));
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = 'Select text to copy';
      }
    } else if (drawer.open && drawer.contains(target) && target.matches('a')) {
      drawer.close();
    }
  });

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
