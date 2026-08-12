import { apiBase, cancelRun, createRun, getRun, getRunnerConfig } from './api.js';
import { initializeAttachments } from './attachments.js';
import { createArtifacts } from './artifacts.js';
import { createConversationState } from './conversation-state.js';
import { renderMarkdown } from './markdown.js';

const POLL_RETRY_LIMIT = 8;
const POLL_RETRY_DELAY_MS = 1200;

export function initializeChat(details, initialPath) {
  const runnerSkill = document.getElementById('runner-skill');
  const runnerSkillSearch = document.getElementById('runner-skill-search');
  const runnerSkillToggle = document.getElementById('runner-skill-toggle');
  const runnerSkillOptions = document.getElementById('runner-skill-options');
  const runnerModel = document.getElementById('runner-model');
  const runnerPrompt = document.getElementById('runner-prompt');
  const runButton = document.getElementById('run-button');
  const newChatButton = document.getElementById('new-chat');
  const chatMessages = document.getElementById('chat-messages');
  const chatEmpty = document.getElementById('chat-empty');
  const statusDot = document.getElementById('runner-status-dot');
  const statusText = document.getElementById('runner-status-text');
  const logBox = document.getElementById('log-box');
  const runLogs = document.getElementById('run-logs');
  const attachmentInput = document.getElementById('attachment-input');
  const attachmentButton = document.getElementById('attachment-button');
  const attachmentTray = document.getElementById('attachment-tray');
  const composer = document.querySelector('.chat-composer');
  const detailByPath = Object.fromEntries(details.map(detail => [detail.path, detail]));
  const conversation = createConversationState();

  let activeDetail = null;
  let pollTimer = null;
  let runnerConnected = false;
  let runnerConfigured = false;
  let codexSessionId = '';
  let activeRunId = '';
  let conversationUploadId = crypto.randomUUID();
  const attachments = initializeAttachments({
    input: attachmentInput,
    button: attachmentButton,
    tray: attachmentTray,
    dropZone: composer,
  });

  const skillOptions = details.map(detail => {
    const option = document.createElement('option');
    option.value = detail.path;
    option.textContent = detail.name;
    return option;
  });
  runnerSkill.replaceChildren(...skillOptions);

  let skillPickerOpen = false;
  let highlightedSkillIndex = -1;

  function filteredSkillDetails() {
    const query = runnerSkillSearch.value.trim().toLocaleLowerCase();
    return details.filter(detail => !query || `${detail.name} ${detail.path}`.toLocaleLowerCase().includes(query));
  }

  function renderSkillOptions() {
    const filtered = filteredSkillDetails();
    runnerSkillOptions.replaceChildren();
    filtered.forEach((detail, index) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'skill-picker-option';
      item.setAttribute('role', 'option');
      item.dataset.path = detail.path;
      item.textContent = detail.name;
      item.setAttribute('aria-selected', detail.path === runnerSkill.value ? 'true' : 'false');
      if (index === highlightedSkillIndex) item.classList.add('highlighted');
      item.addEventListener('mousedown', event => event.preventDefault());
      item.addEventListener('click', () => selectSkill(detail.path, true));
      runnerSkillOptions.append(item);
    });
    if (!filtered.length) {
      const empty = document.createElement('p');
      empty.className = 'skill-picker-empty';
      empty.textContent = '没有匹配的 Skill';
      runnerSkillOptions.append(empty);
    }
  }

  function setSkillPickerOpen(open) {
    skillPickerOpen = open;
    runnerSkillOptions.hidden = !open;
    runnerSkillSearch.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.getElementById('skill-picker').classList.toggle('open', open);
    if (open) {
      highlightedSkillIndex = Math.max(0, filteredSkillDetails().findIndex(detail => detail.path === runnerSkill.value));
      renderSkillOptions();
    }
  }

  function setRunnerStatus(state, text) {
    statusDot.className = `status-dot ${state || ''}`;
    statusText.textContent = text;
  }

  function renderRunning(running) {
    runButton.disabled = running ? !activeRunId : !runnerConnected || !runnerConfigured;
    runnerSkill.disabled = running;
    runnerSkillSearch.disabled = running;
    runnerSkillToggle.disabled = running;
    runnerModel.disabled = running;
    newChatButton.disabled = running;
    attachments.setDisabled(running);
    runButton.textContent = running ? '停止' : '发送';
    runButton.classList.toggle('stop', running);
  }

  function resetConversation() {
    codexSessionId = '';
    activeRunId = '';
    conversationUploadId = crypto.randomUUID();
    conversation.reset();
    if (pollTimer) window.clearTimeout(pollTimer);
    pollTimer = null;
    chatMessages.querySelectorAll('.message').forEach(item => item.remove());
    chatEmpty.hidden = false;
    logBox.hidden = true;
    runLogs.textContent = '';
    runnerPrompt.value = '';
    attachments.reset();
    renderRunning(false);
    setRunnerStatus(
      runnerConfigured ? 'ready' : 'failed',
      runnerConfigured ? '可以开始对话' : '服务已连接，但未找到 Codex CLI',
    );
  }

  function appendMessage(role, text, artifacts = [], runId = '') {
    chatEmpty.hidden = true;
    const message = document.createElement('article');
    message.className = `message ${role}`;
    const label = document.createElement('span');
    label.className = 'message-label';
    label.textContent = role === 'user' ? '你' : (activeDetail?.name || 'Skill 智能体');
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    if (role === 'assistant') {
      bubble.classList.add('markdown-body');
      bubble.innerHTML = renderMarkdown(text, {
        resolveFile: path => runId ? `${apiBase}/api/runs/${runId}/workspace?path=${encodeURIComponent(path)}` : '',
      });
    } else {
      bubble.textContent = text;
    }
    message.append(label, bubble);
    if (artifacts.length) message.append(createArtifacts(artifacts, apiBase));
    chatMessages.append(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  async function loadRunnerConfig() {
    try {
      const config = await getRunnerConfig();
      runnerModel.replaceChildren(...config.models.map(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.label;
        option.selected = model.id === config.default_model;
        return option;
      }));
      runnerConnected = true;
      runnerConfigured = config.configured;
      runButton.disabled = !runnerConfigured;
      setRunnerStatus(
        config.configured ? 'ready' : 'failed',
        config.configured ? '本机 Codex CLI 已连接' : '服务已连接，但未找到 Codex CLI',
      );
    } catch (_) {
      runnerConnected = false;
      runnerConfigured = false;
      runButton.disabled = true;
      setRunnerStatus('failed', '执行服务未启动，请运行 start-playground.ps1');
    }
  }

  async function pollRun(runId, token, retryCount = 0) {
    try {
      const run = await getRun(runId);
      if (!conversation.isCurrent(token)) return;
      logBox.hidden = false;
      runLogs.textContent = (run.logs || []).join('\n');
      if (run.status === 'running') {
        setRunnerStatus('running', '智能体正在执行……');
        pollTimer = window.setTimeout(() => pollRun(runId, token), 900);
        return;
      }
      conversation.finish(token);
      activeRunId = '';
      renderRunning(false);
      if (run.status === 'completed') {
        codexSessionId = run.session_id || codexSessionId;
        setRunnerStatus('ready', '等待你的下一条消息');
        appendMessage('assistant', run.result || '已完成，没有返回文字结果。', run.artifacts || [], run.id);
      } else if (run.status === 'canceled') {
        setRunnerStatus('ready', '任务已停止，可以继续输入');
        appendMessage('assistant', run.result || '任务已停止。', run.artifacts || [], run.id);
      } else {
        setRunnerStatus('failed', run.error || '执行失败');
        appendMessage('assistant', `执行失败：${run.error || '未知错误'}`);
      }
    } catch (error) {
      const retryable = !error.status || error.status >= 500;
      if (conversation.isCurrent(token) && retryable && retryCount < POLL_RETRY_LIMIT) {
        setRunnerStatus('running', `执行服务短暂断开，正在重新连接（${retryCount + 1}/${POLL_RETRY_LIMIT}）……`);
        pollTimer = window.setTimeout(
          () => pollRun(runId, token, retryCount + 1),
          POLL_RETRY_DELAY_MS,
        );
        return;
      }
      if (!conversation.finish(token)) return;
      activeRunId = '';
      renderRunning(false);
      setRunnerStatus('failed', error.message);
      appendMessage('assistant', `连接执行服务失败：${error.message}`);
    }
  }

  async function sendPrompt() {
    if (!activeDetail || !runnerConnected || !runnerConfigured || conversation.running) return;
    const prompt = runnerPrompt.value;
    if (!prompt.trim() && !attachments.hasFiles()) {
      runnerPrompt.focus();
      setRunnerStatus('failed', '请输入任务内容或添加附件');
      return;
    }
    const token = conversation.begin();
    if (token === null) return;
    renderRunning(true);
    setRunnerStatus('running', attachments.hasFiles() ? '正在上传本地附件……' : '正在创建智能体任务……');
    try {
      const composedPrompt = await attachments.uploadAndCompose(prompt, conversationUploadId);
      appendMessage('user', composedPrompt);
      runnerPrompt.value = '';
      setRunnerStatus('running', '正在创建智能体任务……');
      const run = await createRun({
        skill: activeDetail.path,
        prompt: composedPrompt,
        model: runnerModel.value,
        sessionId: codexSessionId,
      });
      if (!conversation.isCurrent(token)) return;
      activeRunId = run.id;
      renderRunning(true);
      pollRun(run.id, token);
    } catch (error) {
      if (!conversation.finish(token)) return;
      activeRunId = '';
      renderRunning(false);
      setRunnerStatus('failed', error.message);
      appendMessage('assistant', `创建任务失败：${error.message}`);
    }
  }

  async function stopRun() {
    if (!conversation.running || !activeRunId) return;
    runButton.disabled = true;
    setRunnerStatus('running', '正在停止当前任务……');
    try {
      await cancelRun(activeRunId);
    } catch (error) {
      if (!conversation.running) return;
      runButton.disabled = false;
      setRunnerStatus('failed', `停止失败：${error.message}`);
    }
  }

  function selectSkill(path, reset = true) {
    activeDetail = detailByPath[path] || details[0];
    if (!activeDetail) return;
    runnerSkill.value = activeDetail.path;
    runnerSkillSearch.value = activeDetail.name;
    setSkillPickerOpen(false);
    runnerPrompt.placeholder = `向 ${activeDetail.name} 描述任务，Enter 发送……`;
    if (reset) resetConversation();
    runnerPrompt.focus();
  }

  runButton.addEventListener('click', () => {
    if (conversation.running) stopRun();
    else sendPrompt();
  });
  runnerPrompt.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendPrompt();
    }
  });
  runnerSkill.addEventListener('change', () => selectSkill(runnerSkill.value, true));
  runnerSkillSearch.addEventListener('focus', () => {
    if (!conversation.running) setSkillPickerOpen(true);
  });
  runnerSkillSearch.addEventListener('input', () => {
    highlightedSkillIndex = 0;
    setSkillPickerOpen(true);
  });
  runnerSkillSearch.addEventListener('keydown', event => {
    const filtered = filteredSkillDetails();
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!skillPickerOpen) setSkillPickerOpen(true);
      if (filtered.length) {
        highlightedSkillIndex = (highlightedSkillIndex + (event.key === 'ArrowDown' ? 1 : -1) + filtered.length) % filtered.length;
        renderSkillOptions();
      }
    } else if (event.key === 'Enter' && skillPickerOpen && filtered[highlightedSkillIndex]) {
      event.preventDefault();
      selectSkill(filtered[highlightedSkillIndex].path, true);
    } else if (event.key === 'Escape') {
      setSkillPickerOpen(false);
      runnerSkillSearch.value = activeDetail?.name || '';
    }
  });
  runnerSkillToggle.addEventListener('click', () => {
    if (!conversation.running) {
      setSkillPickerOpen(!skillPickerOpen);
      runnerSkillSearch.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!document.getElementById('skill-picker').contains(event.target)) setSkillPickerOpen(false);
  });
  newChatButton.addEventListener('click', () => selectSkill(activeDetail?.path, true));

  selectSkill(initialPath, true);
  loadRunnerConfig();

  return { selectSkill };
}
