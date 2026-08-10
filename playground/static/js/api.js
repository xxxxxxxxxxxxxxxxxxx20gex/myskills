export const apiBase = window.location.origin;

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, options);
  let payload;
  try {
    payload = await response.json();
  } catch (_) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.error || `请求失败：HTTP ${response.status}`);
  }
  return payload;
}

export function getRunnerConfig() {
  return requestJson('/api/config');
}

export function createRun({ skill, prompt, model, sessionId }) {
  return requestJson('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skill, prompt, model, session_id: sessionId }),
  });
}

export function getRun(runId) {
  return requestJson(`/api/runs/${runId}`);
}

export function getRatings() {
  return requestJson('/api/ratings');
}

export function saveRatingLevels(ratingLevels) {
  return requestJson('/api/ratings/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating_levels: ratingLevels }),
  });
}

export function saveSkillRating(path, rating, note) {
  return requestJson('/api/ratings/skill', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, rating, note }),
  });
}

export function getGitStatus() {
  return requestJson('/api/git/status');
}

export function getGitDiff(path) {
  return requestJson(`/api/git/diff?path=${encodeURIComponent(path)}`);
}

export function fetchGitUpdates() {
  return requestJson('/api/git/fetch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
}

export function pullGitUpdates() {
  return requestJson('/api/git/pull', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
}

export function commitAndPushGit(message, files) {
  return requestJson('/api/git/commit-push', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, files }),
  });
}

export function saveGitProxyPort(port) {
  return requestJson('/api/git/proxy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ port }),
  });
}

export function getSkills() {
  return requestJson('/api/skills');
}

export function getSkillTree(path) {
  return requestJson(`/api/skills/tree?path=${encodeURIComponent(path)}`);
}

export function getSkillFile(path, file) {
  return requestJson(`/api/skills/file?path=${encodeURIComponent(path)}&file=${encodeURIComponent(file)}`);
}

export function analyzeSkill(path, model) {
  return requestJson('/api/skills/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, model }),
  });
}

export function deleteSkill(path) {
  return requestJson('/api/skills/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, confirmation: path }),
  });
}

export function moveSkill(path, source) {
  return requestJson('/api/skills/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, source }),
  });
}

export function importSkill(file, source, category) {
  return requestJson(`/api/skills/import?source=${encodeURIComponent(source)}&category=${encodeURIComponent(category)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/zip' },
    body: file,
  });
}

export function skillExportUrl(path) {
  return `${apiBase}/api/skills/export?path=${encodeURIComponent(path)}`;
}

export function uploadAttachment(file, conversationId) {
  return requestJson(`/api/uploads?conversation_id=${encodeURIComponent(conversationId)}&name=${encodeURIComponent(file.name)}`, {
    method: 'POST',
    headers: { 'Content-Type': file.type || 'application/octet-stream' },
    body: file,
  });
}
