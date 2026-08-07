import { commitAndPushGit, fetchGitUpdates, getGitDiff, getGitStatus, pullGitUpdates, saveGitProxyPort } from './api.js';

let currentStatus = null;
const actionTimers = new WeakMap();

function setActionState(id, state, label) {
  const button = document.getElementById(id);
  const previousTimer = actionTimers.get(button);
  if (previousTimer) window.clearTimeout(previousTimer);
  button.dataset.defaultLabel ||= button.textContent;
  button.classList.remove('is-loading', 'is-success', 'is-error');
  button.classList.add(`is-${state}`);
  button.textContent = label;
  button.disabled = state === 'loading';
  button.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');

  if (state === 'success' || state === 'error') {
    const timer = window.setTimeout(() => {
      button.classList.remove(`is-${state}`);
      button.textContent = button.dataset.defaultLabel;
      button.disabled = id !== 'git-refresh' && Boolean(currentStatus?.active_runs);
      actionTimers.delete(button);
    }, 1600);
    actionTimers.set(button, timer);
  }
}

function setFeedback(message, failed = false) {
  const target = document.getElementById('git-feedback');
  target.textContent = message;
  target.classList.toggle('error', failed);
}

function renderStatus(status) {
  currentStatus = status;
  const summary = document.getElementById('git-summary');
  summary.replaceChildren();
  const values = [
    ['分支', status.branch || '—'],
    ['上游', status.upstream || '未设置'],
    ['同步', `领先 ${status.ahead} / 落后 ${status.behind}`],
    ['凭据', status.gcm_configured ? 'Git Credential Manager' : '未检测到 GCM'],
  ];
  values.forEach(([label, value]) => {
    const item = document.createElement('div');
    const strong = document.createElement('strong');
    strong.textContent = label;
    const span = document.createElement('span');
    span.textContent = value;
    item.append(strong, span);
    summary.append(item);
  });
  document.getElementById('git-remote').textContent = status.remote || '未配置 origin';
  document.getElementById('git-proxy-port').value = String(status.proxy_port || 0);
  document.getElementById('git-proxy-help').textContent = status.proxy_enabled
    ? `当前启用 http://${status.proxy_host}:${status.proxy_port}，仅影响此 Playground 的 Git 远程操作。`
    : '代理已关闭；填写 1–65535 端口并保存即可启用。';

  const list = document.getElementById('git-file-list');
  list.replaceChildren();
  if (!status.files.length) {
    const empty = document.createElement('p');
    empty.className = 'git-empty';
    empty.textContent = '工作区没有改动。';
    list.append(empty);
  }
  status.files.forEach(file => {
    const row = document.createElement('label');
    row.className = 'git-file';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = file.path;
    checkbox.disabled = !file.safe || file.staged;
    checkbox.title = !file.safe ? '敏感或运行文件不能从网页提交' : file.staged ? '已有暂存改动，需在终端处理' : '选择本次要提交的文件';
    const code = document.createElement('code');
    code.textContent = file.status;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = file.path;
    button.addEventListener('click', async event => {
      event.preventDefault();
      document.getElementById('git-diff').textContent = '正在读取差异……';
      try {
        const result = await getGitDiff(file.path);
        document.getElementById('git-diff').textContent = result.diff;
      } catch (error) {
        document.getElementById('git-diff').textContent = error.message;
      }
    });
    row.append(checkbox, code, button);
    list.append(row);
  });

  const blocked = status.active_runs;
  ['git-fetch', 'git-pull', 'git-commit-push'].forEach(id => document.getElementById(id).disabled = blocked);
  if (blocked) setFeedback('有 Skill 智能体正在运行，Git 写操作暂时禁用。', true);
}

async function refresh(showButtonState = false) {
  if (showButtonState) setActionState('git-refresh', 'loading', '刷新中…');
  setFeedback('正在读取 Git 状态……');
  try {
    renderStatus(await getGitStatus());
    if (!currentStatus.active_runs) setFeedback('Git 状态已刷新。');
    if (showButtonState) setActionState('git-refresh', 'success', '✓ 刷新成功');
  } catch (error) {
    setFeedback(error.message, true);
    if (showButtonState) setActionState('git-refresh', 'error', '刷新失败');
  }
}

export function initializeGitPanel() {
  const dialog = document.getElementById('git-dialog');
  document.getElementById('open-git-panel').addEventListener('click', () => {
    dialog.showModal();
    refresh();
  });
  document.getElementById('git-dialog-close').addEventListener('click', () => dialog.close());
  document.getElementById('git-refresh').addEventListener('click', () => refresh(true));
  document.getElementById('git-save-proxy').addEventListener('click', async () => {
    const input = document.getElementById('git-proxy-port');
    const port = Number(input.value);
    if (!Number.isInteger(port) || port < 0 || port > 65535) {
      setFeedback('代理端口必须是 0–65535 的整数。', true);
      return;
    }
    setFeedback('正在保存 Git 代理……');
    try {
      renderStatus(await saveGitProxyPort(port));
      setFeedback(port ? `Git 代理已设为 http://127.0.0.1:${port}。` : 'Git 代理已关闭。');
    } catch (error) {
      setFeedback(error.message, true);
    }
  });
  document.getElementById('git-fetch').addEventListener('click', async () => {
    setActionState('git-fetch', 'loading', '检查中…');
    setFeedback('正在检查远程更新……');
    try {
      const result = await fetchGitUpdates();
      renderStatus(result.status);
      setFeedback(result.message || '远程状态已更新。');
      setActionState('git-fetch', 'success', '✓ 检查完成');
    } catch (error) {
      setFeedback(error.message, true);
      setActionState('git-fetch', 'error', '检查失败');
    }
  });
  document.getElementById('git-pull').addEventListener('click', async () => {
    if (!window.confirm('仅在工作区干净时执行 git pull --ff-only。继续吗？')) return;
    setActionState('git-pull', 'loading', '拉取中…');
    setFeedback('正在拉取最新代码……');
    try {
      const result = await pullGitUpdates();
      renderStatus(result.status);
      setFeedback(`${result.message}。服务代码可能已变化，请随后重启 Playground。`);
      setActionState('git-pull', 'success', '✓ 拉取成功');
    } catch (error) {
      setFeedback(error.message, true);
      setActionState('git-pull', 'error', '拉取失败');
    }
  });
  document.getElementById('git-commit-push').addEventListener('click', async () => {
    const files = [...document.querySelectorAll('#git-file-list input:checked')].map(item => item.value);
    const message = document.getElementById('git-commit-message').value.trim();
    if (!files.length || !message) {
      setFeedback('请填写提交信息并至少选择一个文件。', true);
      return;
    }
    if (!window.confirm(`将提交 ${files.length} 个文件并立即推送到 origin/${currentStatus?.branch || '当前分支'}。继续吗？`)) return;
    setFeedback('正在提交并推送，请勿关闭页面……');
    try {
      const result = await commitAndPushGit(message, files);
      renderStatus(result.status);
      document.getElementById('git-commit-message').value = '';
      setFeedback(`${result.message}（commit ${result.commit}）`);
    } catch (error) {
      const message = error.message;
      try {
        renderStatus(await getGitStatus());
      } catch (_) {
        // Preserve the original commit/push error; a status refresh is secondary.
      }
      setFeedback(message, true);
    }
  });
}
