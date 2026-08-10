import { deleteSkill, getSkillFile, getSkillTree, importSkill, moveSkill, skillExportUrl } from './api.js';

const categoryLabels = {
  office: '办公文档', visual: '图像演示', academic: '学术研究',
  media: '内容媒体', development: '开发工具', system: '系统效率',
};

function setFeedback(element, message, error = false) {
  element.textContent = message;
  element.classList.toggle('error', error);
}

export function initializeSkillManager() {
  const detailDialog = document.getElementById('skill-dialog');
  const managerDialog = document.getElementById('skill-manager-dialog');
  const tree = document.getElementById('skill-file-tree');
  const preview = document.getElementById('skill-file-preview');
  const fileTitle = document.getElementById('skill-file-title');
  let currentPath = '';

  async function loadTree(path) {
    tree.textContent = '正在读取目录…';
    preview.textContent = '选择左侧文件查看内容。';
    fileTitle.textContent = '文件预览';
    try {
      const payload = await getSkillTree(path);
      tree.replaceChildren(...payload.entries.map(entry => {
        const row = document.createElement(entry.readable ? 'button' : 'div');
        if (entry.readable) row.type = 'button';
        row.className = `file-tree-row ${entry.type}${entry.readable ? ' readable' : ''}`;
        row.style.setProperty('--depth', String(entry.path.split('/').length - 1));
        row.textContent = `${entry.type === 'directory' ? '▸' : entry.readable ? '▤' : '·'} ${entry.name}`;
        row.title = entry.readable ? entry.path : (entry.type === 'file' ? '二进制、大文件或敏感文件不可预览' : entry.path);
        if (entry.readable) row.addEventListener('click', async () => {
          fileTitle.textContent = entry.path;
          preview.textContent = '正在加载…';
          try {
            const file = await getSkillFile(path, entry.path);
            preview.textContent = file.content;
          } catch (error) {
            preview.textContent = error.message;
          }
        });
        return row;
      }));
    } catch (error) {
      tree.textContent = error.message;
    }
  }

  detailDialog.addEventListener('skill-open', event => {
    currentPath = event.detail.path;
    const source = currentPath.startsWith('自创skills/')
      ? 'self'
      : currentPath.startsWith('已测skills/') ? 'tested' : 'pending';
    document.getElementById('skill-maintenance-label').value = source;
    setFeedback(document.getElementById('skill-location-feedback'), '');
    loadTree(currentPath);
  });
  document.getElementById('update-skill-label').addEventListener('click', async event => {
    if (!currentPath) return;
    const button = event.currentTarget;
    const feedback = document.getElementById('skill-location-feedback');
    button.disabled = true;
    button.textContent = '更新中…';
    setFeedback(feedback, '正在移动 Skill 目录并同步维护数据…');
    try {
      const result = await moveSkill(currentPath, document.getElementById('skill-maintenance-label').value);
      if (!result.changed) {
        setFeedback(feedback, '维护标签没有变化。');
        button.disabled = false;
        button.textContent = '更新标签';
        return;
      }
      setFeedback(feedback, `已移动到 ${result.new_path}，页面即将刷新。`);
      window.setTimeout(() => window.location.reload(), 500);
    } catch (error) {
      setFeedback(feedback, error.message, true);
      button.disabled = false;
      button.textContent = '更新标签';
    }
  });
  document.getElementById('dialog-export').addEventListener('click', () => {
    if (currentPath) window.location.href = skillExportUrl(currentPath);
  });
  document.getElementById('dialog-delete').addEventListener('click', async () => {
    if (!currentPath || !window.confirm(`确认删除 ${currentPath}？\n\n文件会移动到本地 .skill-trash，可手动恢复。`)) return;
    const feedback = document.getElementById('analysis-feedback');
    setFeedback(feedback, '正在移动到本地回收站…');
    try {
      await deleteSkill(currentPath);
      detailDialog.close();
      window.location.reload();
    } catch (error) {
      setFeedback(feedback, error.message, true);
    }
  });

  document.getElementById('open-skill-manager').addEventListener('click', () => managerDialog.showModal());
  document.getElementById('skill-manager-close').addEventListener('click', () => managerDialog.close());
  managerDialog.addEventListener('click', event => { if (event.target === managerDialog) managerDialog.close(); });
  const category = document.getElementById('import-category');
  Object.entries(categoryLabels).forEach(([value, label]) => category.add(new Option(label, value)));
  document.getElementById('import-skill-button').addEventListener('click', async event => {
    const input = document.getElementById('import-skill-file');
    const feedback = document.getElementById('skill-manager-feedback');
    const button = event.currentTarget;
    const file = input.files?.[0];
    if (!file) {
      setFeedback(feedback, '请先选择一个 ZIP 文件。', true);
      return;
    }
    button.disabled = true;
    button.textContent = '导入中…';
    setFeedback(feedback, '正在校验并导入 Skill…');
    try {
      const result = await importSkill(file, document.getElementById('import-source').value, category.value);
      setFeedback(feedback, `已导入 ${result.path}，页面即将刷新。`);
      window.setTimeout(() => window.location.reload(), 500);
    } catch (error) {
      setFeedback(feedback, error.message, true);
      button.disabled = false;
      button.textContent = '导入 Skill';
    }
  });
}
