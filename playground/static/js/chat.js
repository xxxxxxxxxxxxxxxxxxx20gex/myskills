import { apiBase, createRun, getRun, getRunnerConfig } from './api.js';
import { createArtifacts } from './artifacts.js';
import { renderMarkdown } from './markdown.js';

export function initializeChat(details, initialPath) {
  const runnerSkill = document.getElementById('runner-skill');
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
  const detailByPath = Object.fromEntries(details.map(detail => [detail.path, detail]));

  let activeDetail = null;
  let pollTimer = null;
  let runnerConnected = false;
  let runnerConfigured = false;
  let codexSessionId = '';

  runnerSkill.replaceChildren(...details.map(detail => {
    const option = document.createElement('option');
    option.value = detail.path;
    option.textContent = detail.name;
    return option;
  }));

  function setRunnerStatus(state, text) {
    statusDot.className = `status-dot ${state || ''}`;
    statusText.textContent = text;
  }

  function setRunning(running) {
    runButton.disabled = running || !runnerConnected || !runnerConfigured;
    runnerSkill.disabled = running;
    runnerModel.disabled = running;
    newChatButton.disabled = running;
    runButton.textContent = running ? '执行中…' : '发送';
  }

  function resetConversation(seedPrompt = true) {
    codexSessionId = '';
    if (pollTimer) window.clearTimeout(pollTimer);
    pollTimer = null;
    chatMessages.querySelectorAll('.message').forEach(item => item.remove());
    chatEmpty.hidden = false;
    logBox.hidden = true;
    runLogs.textContent = '';
    if (seedPrompt && activeDetail) runnerPrompt.value = activeDetail.examples[0] || '';
    setRunnerStatus(
      runnerConfigured ? 'ready' : 'failed',
      runnerConfigured ? '可以开始对话' : '服务已连接，但未找到 Codex CLI',
    );
  }

  function appendMessage(role, text, artifacts = []) {
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
      bubble.innerHTML = renderMarkdown(text);
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
        option.textContent = `${model.label} · ${model.api_model}`;
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

  async function pollRun(runId) {
    try {
      const run = await getRun(runId);
      logBox.hidden = false;
      runLogs.textContent = (run.logs || []).join('\n');
      if (run.status === 'running') {
        setRunnerStatus('running', '智能体正在执行……');
        pollTimer = window.setTimeout(() => pollRun(runId), 900);
        return;
      }
      setRunning(false);
      if (run.status === 'completed') {
        codexSessionId = run.session_id || codexSessionId;
        setRunnerStatus('ready', '等待你的下一条消息');
        appendMessage('assistant', run.result || '已完成，没有返回文字结果。', run.artifacts || []);
      } else {
        setRunnerStatus('failed', run.error || '执行失败');
        appendMessage('assistant', `执行失败：${run.error || '未知错误'}`);
      }
    } catch (error) {
      setRunning(false);
      setRunnerStatus('failed', error.message);
      appendMessage('assistant', `连接执行服务失败：${error.message}`);
    }
  }

  async function sendPrompt() {
    if (!activeDetail || !runnerConnected) return;
    const prompt = runnerPrompt.value;
    if (!prompt.trim()) {
      runnerPrompt.focus();
      setRunnerStatus('failed', '请先输入任务内容');
      return;
    }
    appendMessage('user', prompt);
    runnerPrompt.value = '';
    setRunning(true);
    setRunnerStatus('running', '正在创建智能体任务……');
    try {
      const run = await createRun({
        skill: activeDetail.path,
        prompt,
        model: runnerModel.value,
        sessionId: codexSessionId,
      });
      pollRun(run.id);
    } catch (error) {
      setRunning(false);
      setRunnerStatus('failed', error.message);
      appendMessage('assistant', `创建任务失败：${error.message}`);
    }
  }

  function selectSkill(path, reset = true) {
    activeDetail = detailByPath[path] || details[0];
    if (!activeDetail) return;
    runnerSkill.value = activeDetail.path;
    runnerPrompt.placeholder = `向 ${activeDetail.name} 描述任务，Enter 发送……`;
    if (reset) resetConversation(true);
    runnerPrompt.focus();
  }

  runButton.addEventListener('click', sendPrompt);
  runnerPrompt.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendPrompt();
    }
  });
  runnerSkill.addEventListener('change', () => selectSkill(runnerSkill.value, true));
  newChatButton.addEventListener('click', () => selectSkill(activeDetail?.path, true));

  selectSkill(initialPath, true);
  loadRunnerConfig();

  return { selectSkill };
}
