import { uploadAttachment } from './api.js';
import { composeAttachmentPrompt } from './attachment-prompt.js';

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

export function initializeAttachments({ input, button, tray, dropZone }) {
  let selected = [];

  function render() {
    tray.hidden = selected.length === 0;
    tray.replaceChildren(...selected.map(item => {
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      const thumb = document.createElement('div');
      thumb.className = 'attachment-thumb';
      if (item.file.type.startsWith('image/')) {
        const image = document.createElement('img');
        image.src = item.url;
        image.alt = '';
        thumb.append(image);
      } else {
        thumb.textContent = '▤';
      }
      const info = document.createElement('div');
      info.className = 'attachment-info';
      const name = document.createElement('strong');
      name.textContent = item.file.name;
      const size = document.createElement('span');
      size.textContent = formatBytes(item.file.size);
      info.append(name, size);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'attachment-remove';
      remove.setAttribute('aria-label', `移除附件 ${item.file.name}`);
      remove.textContent = '×';
      remove.addEventListener('click', () => {
        URL.revokeObjectURL(item.url);
        selected = selected.filter(candidate => candidate.id !== item.id);
        render();
      });
      chip.append(thumb, info, remove);
      return chip;
    }));
  }

  function add(files) {
    selected.push(...[...files].map(file => ({
      id: crypto.randomUUID(),
      file,
      url: URL.createObjectURL(file),
    })));
    render();
  }

  function reset() {
    selected.forEach(item => URL.revokeObjectURL(item.url));
    selected = [];
    input.value = '';
    render();
  }

  button.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    add(input.files || []);
    input.value = '';
  });
  dropZone.addEventListener('dragover', event => {
    event.preventDefault();
    dropZone.classList.add('dragging');
  });
  dropZone.addEventListener('dragleave', event => {
    if (!dropZone.contains(event.relatedTarget)) dropZone.classList.remove('dragging');
  });
  dropZone.addEventListener('drop', event => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
    add(event.dataTransfer?.files || []);
  });

  return {
    hasFiles: () => selected.length > 0,
    setDisabled: value => { button.disabled = value; },
    reset,
    async uploadAndCompose(prompt, conversationId) {
      const uploads = await Promise.all(selected.map(item => uploadAttachment(item.file, conversationId)));
      const composed = composeAttachmentPrompt(prompt, uploads);
      reset();
      return composed;
    },
  };
}
