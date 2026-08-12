import { analyzeSkill } from './api.js';

const statusNames = { tested: '已测', pending: '待测', unclassified: '自创' };
const categoryVisuals = {
  office: ['▤', 'blue'], visual: ['✦', 'purple'], academic: ['⌕', 'green'],
  media: ['▶', 'orange'], development: ['⌘', 'blue'], system: ['⌑', 'green'],
};

function appendTextElement(parent, tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function listItems(id, items, placeholder = '尚未分析') {
  const values = Array.isArray(items) && items.length ? items : [placeholder];
  document.getElementById(id).replaceChildren(...values.map(item => {
    const entry = document.createElement('li');
    entry.textContent = item;
    return entry;
  }));
}

function renderAnalysis(detail) {
  const analysis = detail.analysis;
  const empty = '点击“AI 分析”后生成并持久化此信息';
  listItems('dialog-conditions', analysis?.usage_conditions, empty);
  listItems('dialog-inputs', analysis?.input_requirements, analysis ? '旧版分析未包含输入要求，请重新分析' : empty);
  listItems('dialog-problems', analysis?.problems_solved, empty);
  listItems('dialog-scenes', analysis?.use_cases, empty);
  listItems('dialog-results', analysis?.final_results, empty);

  const attachment = analysis?.attachments;
  const attachmentState = { yes: '会生成文件', no: '不生成文件', conditional: '部分任务会生成文件' }[attachment?.produces] || empty;
  const attachmentItems = attachment ? [
    attachmentState,
    ...(attachment.types || []),
    ...(attachment.notes ? [attachment.notes] : []),
  ] : [empty];
  listItems('dialog-attachments', attachmentItems, empty);

  const risk = analysis?.risk_assessment;
  const levelNames = { low: '低风险', medium: '中风险', high: '高风险' };
  const riskItems = risk ? [
    `风险等级：${levelNames[risk.level] || risk.level}`,
    ...(risk.summary ? [risk.summary] : []),
    ...(risk.risks || []).map(item => `风险：${item}`),
  ] : [empty];
  listItems('dialog-risks', riskItems, empty);
  const meta = document.getElementById('analysis-meta');
  meta.textContent = analysis ? `由 ${analysis.model} 分析 · ${analysis.updated_at}` : '尚未生成 AI 分析';
}

function createCard(detail) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'card repo-card';
  card.dataset.skill = detail.path;
  card.dataset.skillPath = detail.path;
  const top = appendTextElement(card, 'div', 'card-top', '');
  appendTextElement(top, 'div', `icon ${detail.color}`, detail.icon);
  const title = appendTextElement(top, 'div', '', '');
  appendTextElement(title, 'h3', '', detail.name);
  appendTextElement(title, 'p', 'slug', detail.slug);
  appendTextElement(card, 'span', `status-label ${detail.status === 'unclassified' ? 'self' : detail.status}`, statusNames[detail.status]);
  appendTextElement(card, 'p', 'desc', detail.summary);
  const flow = appendTextElement(card, 'div', 'flow', '');
  appendTextElement(flow, 'strong', '', detail.analysis ? '已完成 AI 分析' : '待 AI 分析');
  appendTextElement(flow, 'span', 'arrow', '→');
  flow.append(document.createTextNode(detail.analysis?.final_results?.[0] || '查看 Skill 文件与用途'));
  const more = appendTextElement(card, 'span', 'more', '查看详细信息 ');
  appendTextElement(more, 'span', '', '→');
  return card;
}

function buildDetails(actualSkills, skillDetails, repositorySkills, skillCategories) {
  const curatedByPath = new Map(Object.values(skillDetails).map(detail => [detail.path, detail]));
  const repositoryByPath = new Map(repositorySkills.map(skill => [
    `${skill.status === 'tested' ? '已测skills' : '待测skills'}/${skill.folder}`, skill,
  ]));
  const knownCategories = Object.fromEntries(
    skillCategories.flatMap(category => category.skills.map(skill => [skill, category.id])),
  );
  return actualSkills.map(skill => {
    const curated = curatedByPath.get(skill.path);
    const repository = repositoryByPath.get(skill.path);
    const category = skill.category || curated?.category || repository?.category || knownCategories[skill.folder] || 'system';
    const [defaultIcon, defaultColor] = categoryVisuals[category] || ['◇', 'blue'];
    return {
      name: curated?.name || repository?.title || skill.title,
      slug: skill.name,
      icon: curated?.icon || defaultIcon,
      color: curated?.color || defaultColor,
      category,
      source: skill.source,
      status: skill.status,
      summary: curated?.summary || repository?.summary || skill.summary,
      path: skill.path,
      analysis: skill.analysis || null,
    };
  });
}

function initializeFilters(skillCategories, cards, sectionByCategory) {
  const tabs = [...document.querySelectorAll('.tab')];
  const sourceFilter = document.getElementById('source-filter');
  const statusFilter = document.getElementById('status-filter');
  const ratingFilter = document.getElementById('rating-filter');
  const searchInput = document.getElementById('skill-search');
  const empty = document.getElementById('catalog-empty');
  let activeCategory = 'all';
  const totalByCategory = Object.fromEntries(skillCategories.map(category => [category.id, cards.filter(card => card.dataset.category === category.id).length]));
  tabs.forEach(tab => {
    const category = skillCategories.find(item => item.id === tab.dataset.filter);
    tab.textContent = `${category?.label || '全部'} ${category ? totalByCategory[category.id] : cards.length}`;
  });
  function applyFilters() {
    const query = searchInput.value.trim().toLocaleLowerCase('zh-CN');
    let visibleTotal = 0;
    cards.forEach(card => {
      const rating = card.dataset.rating;
      const matches = (activeCategory === 'all' || card.dataset.category === activeCategory)
        && (sourceFilter.value === 'all' || card.dataset.source === sourceFilter.value)
        && (statusFilter.value === 'all' || card.dataset.status === statusFilter.value)
        && (ratingFilter.value === 'all' || (ratingFilter.value === 'unrated' ? !rating : rating === ratingFilter.value))
        && (!query || card.dataset.search.includes(query));
      card.hidden = !matches;
      if (matches) visibleTotal += 1;
    });
    sectionByCategory.forEach(({ section, grid, count }) => {
      const visible = [...grid.children].filter(card => !card.hidden).length;
      section.hidden = visible === 0;
      count.textContent = `${visible} 个`;
    });
    empty.hidden = visibleTotal !== 0;
  }
  tabs.forEach(tab => tab.addEventListener('click', () => {
    activeCategory = tab.dataset.filter;
    tabs.forEach(item => item.setAttribute('aria-selected', String(item === tab)));
    applyFilters();
  }));
  [sourceFilter, statusFilter, ratingFilter].forEach(filter => filter.addEventListener('change', applyFilters));
  searchInput.addEventListener('input', applyFilters);
  document.addEventListener('catalog-rating-updated', applyFilters);
  applyFilters();
}

export function initializeCatalog({ actualSkills, skillDetails, repositorySkills, skillCategories, onRunSkill }) {
  const details = buildDetails(actualSkills, skillDetails, repositorySkills, skillCategories);
  const detailsByPath = new Map(details.map(detail => [detail.path, detail]));
  document.querySelectorAll('[data-status-section]').forEach(section => section.remove());
  const root = document.getElementById('catalog-sections');
  root.replaceChildren();
  const sectionByCategory = new Map();
  skillCategories.forEach(category => {
    const section = document.createElement('section');
    section.dataset.categorySection = category.id;
    const head = appendTextElement(section, 'div', 'section-head', '');
    appendTextElement(head, 'h2', '', category.label);
    appendTextElement(head, 'span', '', category.description);
    const count = appendTextElement(head, 'strong', 'section-count', '0 个');
    const grid = appendTextElement(section, 'div', 'grid', '');
    sectionByCategory.set(category.id, { section, grid, count });
    root.append(section);
  });
  const cards = details.map(detail => {
    const card = createCard(detail);
    card.dataset.category = detail.category;
    card.dataset.source = detail.source;
    card.dataset.status = detail.status;
    card.dataset.rating = '';
    card.dataset.search = [detail.name, detail.slug, detail.summary].join(' ').toLocaleLowerCase('zh-CN');
    sectionByCategory.get(detail.category)?.grid.append(card);
    return card;
  });
  initializeFilters(skillCategories, cards, sectionByCategory);

  const dialog = document.getElementById('skill-dialog');
  let lastTrigger = null;
  let dialogDetail = null;
  let focusChatAfterClose = false;
  function openDetail(card, detail) {
    lastTrigger = card;
    dialogDetail = detail;
    document.getElementById('dialog-name').textContent = detail.name;
    document.getElementById('dialog-slug').textContent = detail.slug;
    document.getElementById('dialog-summary').textContent = detail.summary;
    document.getElementById('dialog-path').textContent = detail.path;
    const icon = document.getElementById('dialog-icon');
    icon.textContent = detail.icon;
    icon.className = `icon ${detail.color}`;
    renderAnalysis(detail);
    document.getElementById('analysis-feedback').textContent = '';
    dialog.dispatchEvent(new CustomEvent('skill-open', { detail: { path: detail.path } }));
    dialog.showModal();
  }
  cards.forEach(card => card.addEventListener('click', () => openDetail(card, detailsByPath.get(card.dataset.skillPath))));
  document.getElementById('dialog-analyze').addEventListener('click', async event => {
    if (!dialogDetail) return;
    const button = event.currentTarget;
    const feedback = document.getElementById('analysis-feedback');
    button.disabled = true;
    button.textContent = '分析中…';
    feedback.textContent = '正在调用本机 Codex 分析 Skill 文件，通常需要几十秒。';
    try {
      const model = document.getElementById('runner-model').value;
      dialogDetail.analysis = await analyzeSkill(dialogDetail.path, model);
      renderAnalysis(dialogDetail);
      feedback.textContent = '分析结论已保存到 skill-insights.yaml。';
      const card = cards.find(item => item.dataset.skillPath === dialogDetail.path);
      if (card) card.querySelector('.flow').replaceChildren(Object.assign(document.createElement('strong'), { textContent: '已完成 AI 分析' }), document.createTextNode(` → ${dialogDetail.analysis.final_results[0]}`));
    } catch (error) {
      feedback.textContent = error.message;
      feedback.classList.add('error');
    } finally {
      button.disabled = false;
      button.textContent = 'AI 分析';
    }
  });
  document.getElementById('dialog-run-shortcut').addEventListener('click', () => {
    focusChatAfterClose = true;
    dialog.close();
    if (dialogDetail) onRunSkill(dialogDetail.path);
  });
  document.getElementById('dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => {
    if (!focusChatAfterClose && lastTrigger) lastTrigger.focus();
    focusChatAfterClose = false;
  });
  return details;
}
