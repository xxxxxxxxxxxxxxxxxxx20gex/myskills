const statusNames = { tested: '已测', pending: '待测' };
const statusFolders = { tested: '已测skills', pending: '待测skills' };

function fillList(id, items) {
  document.getElementById(id).innerHTML = items.map(item => `<li>${item}</li>`).join('');
}

function renderRepositoryCards(repositorySkills) {
  const details = {};
  ['tested', 'pending'].forEach(status => {
    const icon = status === 'tested' ? '✓' : '◌';
    const color = status === 'tested' ? 'green' : 'orange';
    const target = document.getElementById(`${status}-grid`);
    const items = repositorySkills.filter(skill => skill.status === status);
    target.innerHTML = items.map(skill => {
      const key = `repo:${status}:${skill.folder}`;
      const count = skill.headings.length;
      details[key] = {
        name: skill.title,
        slug: skill.name,
        icon,
        color,
        summary: skill.summary,
        capabilities: skill.headings.slice(0, 4).length
          ? skill.headings.slice(0, 4)
          : ['阅读 SKILL.md 了解完整工作流'],
        examples: ['根据该 skill 的触发范围处理对应任务', '调用前检查所需依赖、服务配置与权限'],
        outputs: ['具体产出由用户请求和 skill 工作流决定', `SKILL.md 中记录了 ${count} 个主要主题章节`],
        notes: [`维护状态：${statusNames[status]}`, ...skill.headings.slice(4, 8)],
        path: `${statusFolders[status]}/${skill.folder}`,
      };
      return `<button type="button" class="card repo-card" data-skill="${key}"><div class="card-top"><div class="icon ${color}">${icon}</div><div><h3>${skill.title}</h3><p class="slug">${skill.name}</p></div></div><span class="status-label ${status}">${statusNames[status]}</span><p class="desc">${skill.summary}</p><div class="flow"><strong>${skill.name}</strong><span class="arrow">→</span>SKILL.md<span class="arrow">→</span><strong>${count} 个主题章节</strong></div><span class="more">查看详细信息 <span>→</span></span></button>`;
    }).join('');
    target.querySelectorAll('[data-skill]').forEach(card => {
      const detail = details[card.dataset.skill];
      if (detail) card.dataset.skillPath = detail.path;
    });
  });
  return details;
}

export function initializeCatalog({ skillDetails, repositorySkills, onRunSkill }) {
  const repositoryDetails = renderRepositoryCards(repositorySkills);
  document.querySelectorAll('[data-skill]').forEach(card => {
    const detail = skillDetails[card.dataset.skill] || repositoryDetails[card.dataset.skill];
    if (detail) card.dataset.skillPath = detail.path;
  });
  const tabs = [...document.querySelectorAll('.tab')];
  const sections = [...document.querySelectorAll('[data-status-section]')];
  tabs.forEach(tab => tab.addEventListener('click', () => {
    const filter = tab.dataset.filter;
    tabs.forEach(item => item.setAttribute('aria-selected', String(item === tab)));
    sections.forEach(section => {
      section.hidden = filter !== 'all' && section.dataset.statusSection !== filter;
    });
  }));

  const dialog = document.getElementById('skill-dialog');
  const closeButton = document.getElementById('dialog-close');
  const runShortcut = document.getElementById('dialog-run-shortcut');
  let lastTrigger = null;
  let dialogDetail = null;
  let focusChatAfterClose = false;

  document.querySelectorAll('[data-skill]').forEach(card => card.addEventListener('click', () => {
    const detail = skillDetails[card.dataset.skill] || repositoryDetails[card.dataset.skill];
    if (!detail) return;
    lastTrigger = card;
    dialogDetail = detail;
    document.getElementById('dialog-name').textContent = detail.name;
    document.getElementById('dialog-slug').textContent = detail.slug || card.dataset.skill;
    document.getElementById('dialog-summary').textContent = detail.summary;
    document.getElementById('dialog-path').textContent = detail.path;
    const icon = document.getElementById('dialog-icon');
    icon.textContent = detail.icon;
    icon.className = `icon ${detail.color}`;
    fillList('dialog-capabilities', detail.capabilities);
    fillList('dialog-examples', detail.examples);
    fillList('dialog-outputs', detail.outputs);
    fillList('dialog-notes', detail.notes);
    dialog.dispatchEvent(new CustomEvent('skill-open', { detail: { path: detail.path } }));
    dialog.showModal();
  }));

  runShortcut.addEventListener('click', () => {
    focusChatAfterClose = true;
    dialog.close();
    if (dialogDetail) onRunSkill(dialogDetail.path);
  });
  closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    if (!focusChatAfterClose && lastTrigger) lastTrigger.focus();
    focusChatAfterClose = false;
  });

  return repositoryDetails;
}
