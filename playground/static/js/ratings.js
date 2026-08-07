import { getRatings, saveRatingLevels, saveSkillRating } from './api.js';

const ratingKeys = ['A', 'B', 'C'];
let state = { rating_levels: {}, skills: {} };
let currentPath = '';

function optionLabel(key) {
  const level = state.rating_levels[key];
  return level ? `${key} · ${level.name}` : key;
}

function paintCards() {
  const filter = document.getElementById('rating-filter').value;
  document.querySelectorAll('[data-skill-path]').forEach(card => {
    const item = state.skills[card.dataset.skillPath];
    let badge = card.querySelector('.rating-badge');
    if (!badge) {
      badge = document.createElement('span');
      badge.className = 'rating-badge';
      card.append(badge);
    }
    badge.textContent = item?.rating || '—';
    badge.title = item?.rating ? optionLabel(item.rating) : '未评分';
    badge.style.backgroundColor = item?.rating ? state.rating_levels[item.rating]?.color || '#65708a' : '#aab3c4';
    card.hidden = filter === 'unrated' ? Boolean(item?.rating) : ratingKeys.includes(filter) ? item?.rating !== filter : false;
  });
}

function fillRatingSelect() {
  const select = document.getElementById('skill-rating');
  select.replaceChildren(new Option('未评分', ''));
  ratingKeys.forEach(key => select.add(new Option(optionLabel(key), key)));
}

function openSkill(path) {
  currentPath = path;
  fillRatingSelect();
  const item = state.skills[path] || {};
  document.getElementById('skill-rating').value = item.rating || '';
  document.getElementById('skill-rating-note').value = item.note || '';
  document.getElementById('rating-feedback').textContent = '';
}

function fillSettings() {
  ratingKeys.forEach(key => {
    const level = state.rating_levels[key];
    document.getElementById(`rating-${key}-name`).value = level.name;
    document.getElementById(`rating-${key}-description`).value = level.description;
    document.getElementById(`rating-${key}-color`).value = level.color;
  });
}

export async function initializeRatings() {
  const filter = document.getElementById('rating-filter');
  const dialog = document.getElementById('rating-dialog');
  const feedback = document.getElementById('rating-feedback');
  try {
    state = await getRatings();
    paintCards();
  } catch (error) {
    feedback.textContent = error.message;
  }

  filter.addEventListener('change', paintCards);
  document.getElementById('skill-dialog').addEventListener('skill-open', event => openSkill(event.detail.path));
  document.getElementById('save-skill-rating').addEventListener('click', async () => {
    if (!currentPath) return;
    feedback.textContent = '正在保存……';
    try {
      state = await saveSkillRating(
        currentPath,
        document.getElementById('skill-rating').value,
        document.getElementById('skill-rating-note').value,
      );
      paintCards();
      feedback.textContent = '评分已保存，可随 Git 同步。';
    } catch (error) {
      feedback.textContent = error.message;
    }
  });

  document.getElementById('open-rating-settings').addEventListener('click', () => {
    fillSettings();
    document.getElementById('rating-settings-feedback').textContent = '';
    dialog.showModal();
  });
  document.getElementById('rating-dialog-close').addEventListener('click', () => dialog.close());
  document.getElementById('save-rating-settings').addEventListener('click', async () => {
    const levels = Object.fromEntries(ratingKeys.map(key => [key, {
      name: document.getElementById(`rating-${key}-name`).value,
      description: document.getElementById(`rating-${key}-description`).value,
      color: document.getElementById(`rating-${key}-color`).value,
    }]));
    const status = document.getElementById('rating-settings-feedback');
    status.textContent = '正在保存……';
    try {
      state = await saveRatingLevels(levels);
      fillRatingSelect();
      paintCards();
      status.textContent = '等级设置已保存。';
    } catch (error) {
      status.textContent = error.message;
    }
  });
}
