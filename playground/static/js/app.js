import { repositorySkills, skillCategories, skillDetails } from './data.js';
import { initializeCatalog } from './catalog.js';
import { initializeChat } from './chat.js';
import { initializePanelResize } from './resize.js';
import { initializeRatings } from './ratings.js';
import { initializeGitPanel } from './git-panel.js';
import { initializeSkillManager } from './skill-manager.js';
import { getSkills } from './api.js';

async function bootstrap() {
  const payload = await getSkills();
  let chat;
  const allDetails = initializeCatalog({
    actualSkills: payload.skills,
    skillDetails,
    repositorySkills,
    skillCategories,
    onRunSkill: path => chat?.selectSkill(path, true),
  }).sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));
  const initialPath = allDetails.some(detail => detail.path === '自创skills/gpt-image')
    ? '自创skills/gpt-image'
    : allDetails[0]?.path;
  chat = initializeChat(allDetails, initialPath);
  initializePanelResize();
  initializeSkillManager();
  await initializeRatings();
  initializeGitPanel();
}

bootstrap().catch(error => {
  document.getElementById('catalog-empty').hidden = false;
  document.getElementById('catalog-empty').textContent = `页面初始化失败：${error.message}`;
});
