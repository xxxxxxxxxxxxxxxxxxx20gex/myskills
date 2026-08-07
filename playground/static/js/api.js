export const apiBase = window.location.protocol === 'file:'
  ? 'http://127.0.0.1:8765'
  : window.location.origin;

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
