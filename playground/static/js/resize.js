const STORAGE_KEY = 'myskills.chat-width';
const DEFAULT_WIDTH = 400;
const MIN_CHAT_WIDTH = 320;
const MIN_CATALOG_WIDTH = 420;
const MAX_CHAT_WIDTH = 760;

export function initializePanelResize() {
  const shell = document.querySelector('.app-shell');
  const handle = document.getElementById('panel-resizer');
  if (!shell || !handle) return;

  let dragging = false;

  function bounds() {
    return {
      min: MIN_CHAT_WIDTH,
      max: Math.max(
        MIN_CHAT_WIDTH,
        Math.min(MAX_CHAT_WIDTH, shell.clientWidth - MIN_CATALOG_WIDTH - handle.offsetWidth),
      ),
    };
  }

  function applyWidth(width, persist = false) {
    const { min, max } = bounds();
    const nextWidth = Math.round(Math.min(max, Math.max(min, width)));
    shell.style.setProperty('--chat-width', `${nextWidth}px`);
    handle.setAttribute('aria-valuemin', String(min));
    handle.setAttribute('aria-valuemax', String(max));
    handle.setAttribute('aria-valuenow', String(nextWidth));
    if (persist) localStorage.setItem(STORAGE_KEY, String(nextWidth));
  }

  function currentWidth() {
    return parseFloat(getComputedStyle(shell).getPropertyValue('--chat-width')) || DEFAULT_WIDTH;
  }

  const savedWidth = Number(localStorage.getItem(STORAGE_KEY));
  applyWidth(Number.isFinite(savedWidth) && savedWidth > 0 ? savedWidth : DEFAULT_WIDTH);

  handle.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    dragging = true;
    handle.setPointerCapture(event.pointerId);
    document.body.classList.add('resizing-panels');
    event.preventDefault();
  });

  handle.addEventListener('pointermove', event => {
    if (!dragging) return;
    applyWidth(shell.getBoundingClientRect().right - event.clientX);
  });

  const finishDragging = event => {
    if (!dragging) return;
    dragging = false;
    if (handle.hasPointerCapture(event.pointerId)) handle.releasePointerCapture(event.pointerId);
    document.body.classList.remove('resizing-panels');
    applyWidth(currentWidth(), true);
  };

  handle.addEventListener('pointerup', finishDragging);
  handle.addEventListener('pointercancel', finishDragging);
  handle.addEventListener('dblclick', () => applyWidth(DEFAULT_WIDTH, true));
  handle.addEventListener('keydown', event => {
    let nextWidth = currentWidth();
    if (event.key === 'ArrowLeft') nextWidth += 24;
    else if (event.key === 'ArrowRight') nextWidth -= 24;
    else if (event.key === 'Home') nextWidth = bounds().min;
    else if (event.key === 'End') nextWidth = bounds().max;
    else return;
    event.preventDefault();
    applyWidth(nextWidth, true);
  });

  window.addEventListener('resize', () => applyWidth(currentWidth()));
}
