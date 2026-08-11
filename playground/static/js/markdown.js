function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderInline(value) {
  const protectedFragments = [];
  const protect = html => `\u0000${protectedFragments.push(html) - 1}\u0000`;
  let text = escapeHtml(value);

  text = text.replace(/`([^`\n]+)`/g, (_, code) => protect(`<code>${code}</code>`));
  text = text.replace(/\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g, (_, label, href) => (
    protect(`<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`)
  ));
  text = text
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_\n]+)__/g, '<strong>$1</strong>')
    .replace(/~~([^~\n]+)~~/g, '<del>$1</del>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/(^|[^_])_([^_\n]+)_/g, '$1<em>$2</em>');

  return text.replace(/\u0000(\d+)\u0000/g, (_, index) => protectedFragments[Number(index)]);
}

function splitTableRow(line) {
  let value = String(line).trim();
  if (value.startsWith('|')) value = value.slice(1);
  if (value.endsWith('|') && !value.endsWith('\\|')) value = value.slice(0, -1);

  const cells = [];
  let cell = '';
  let inCode = false;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (character === '`') {
      inCode = !inCode;
      cell += character;
      continue;
    }
    if (character === '\\' && value[index + 1] === '|') {
      cell += '|';
      index += 1;
      continue;
    }
    if (character === '|' && !inCode) {
      cells.push(cell.trim());
      cell = '';
      continue;
    }
    cell += character;
  }
  cells.push(cell.trim());
  return cells;
}

function tableAlignment(delimiter) {
  const value = delimiter.trim();
  if (!/^:?-{3,}:?$/.test(value)) return null;
  if (value.startsWith(':') && value.endsWith(':')) return 'center';
  if (value.endsWith(':')) return 'right';
  return 'left';
}

function readTable(lines, start) {
  if (!lines[start]?.includes('|') || !lines[start + 1]?.includes('|')) return null;
  const headers = splitTableRow(lines[start]);
  const delimiters = splitTableRow(lines[start + 1]);
  if (headers.length < 2 || delimiters.length !== headers.length) return null;
  const alignments = delimiters.map(tableAlignment);
  if (alignments.some(alignment => alignment === null)) return null;

  const rows = [];
  let index = start + 2;
  while (index < lines.length && lines[index].trim() && lines[index].includes('|')) {
    const cells = splitTableRow(lines[index]).slice(0, headers.length);
    while (cells.length < headers.length) cells.push('');
    rows.push(cells);
    index += 1;
  }
  return { headers, alignments, rows, nextIndex: index };
}

function startsBlock(line) {
  return /^\s*$|^```|^#{1,6}\s+|^\s*>\s?|^\s*[-*+]\s+|^\s*\d+[.)]\s+|^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line);
}

export function renderMarkdown(markdown) {
  const lines = String(markdown ?? '').replaceAll('\r\n', '\n').split('\n');
  const output = [];
  let index = 0;
  let listType = '';

  const closeList = () => {
    if (!listType) return;
    output.push(`</${listType}>`);
    listType = '';
  };

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      closeList();
      index += 1;
      continue;
    }

    const table = readTable(lines, index);
    if (table) {
      closeList();
      const header = table.headers.map((cell, cellIndex) => (
        `<th class="align-${table.alignments[cellIndex]}">${renderInline(cell)}</th>`
      )).join('');
      const body = table.rows.map(row => `<tr>${row.map((cell, cellIndex) => (
        `<td class="align-${table.alignments[cellIndex]}">${renderInline(cell)}</td>`
      )).join('')}</tr>`).join('');
      output.push(`<div class="markdown-table-wrap"><table><thead><tr>${header}</tr></thead>${body ? `<tbody>${body}</tbody>` : ''}</table></div>`);
      index = table.nextIndex;
      continue;
    }

    const fence = line.match(/^```\s*([\w+-]*)\s*$/);
    if (fence) {
      closeList();
      const code = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const language = fence[1] ? ` class="language-${escapeHtml(fence[1])}"` : '';
      output.push(`<pre><code${language}>${escapeHtml(code.join('\n'))}</code></pre>`);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
      closeList();
      output.push('<hr>');
      index += 1;
      continue;
    }

    const quote = line.match(/^\s*>\s?(.*)$/);
    if (quote) {
      closeList();
      const quoteLines = [quote[1]];
      index += 1;
      while (index < lines.length) {
        const nextQuote = lines[index].match(/^\s*>\s?(.*)$/);
        if (!nextQuote) break;
        quoteLines.push(nextQuote[1]);
        index += 1;
      }
      output.push(`<blockquote>${quoteLines.map(renderInline).join('<br>')}</blockquote>`);
      continue;
    }

    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      const nextType = unordered ? 'ul' : 'ol';
      const content = (unordered || ordered)[1];
      const task = content.match(/^\[([ xX])]\s+(.+)$/);
      if (listType !== nextType) {
        closeList();
        listType = nextType;
        output.push(`<${listType}>`);
      }
      if (task) {
        const checked = task[1].toLowerCase() === 'x' ? ' checked' : '';
        output.push(`<li class="task-list-item"><input class="task-list-checkbox" type="checkbox" disabled${checked}>${renderInline(task[2])}</li>`);
      } else {
        output.push(`<li>${renderInline(content)}</li>`);
      }
      index += 1;
      continue;
    }

    closeList();
    const paragraph = [line];
    index += 1;
    while (index < lines.length && !startsBlock(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    output.push(`<p>${paragraph.map(renderInline).join('<br>')}</p>`);
  }

  closeList();
  return output.join('');
}
