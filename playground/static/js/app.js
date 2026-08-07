import { repositorySkills, skillDetails } from './data.js';
import { initializeCatalog } from './catalog.js';
import { initializeChat } from './chat.js';
import { initializePanelResize } from './resize.js';
import { initializeRatings } from './ratings.js';
import { initializeGitPanel } from './git-panel.js';

let chat;
const repositoryDetails = initializeCatalog({
  skillDetails,
  repositorySkills,
  onRunSkill: path => chat?.selectSkill(path, true),
});

const allDetails = [
  ...Object.values(skillDetails),
  ...Object.values(repositoryDetails),
].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'));

const initialPath = allDetails.some(detail => detail.path === '自创skills/gpt-image')
  ? '自创skills/gpt-image'
  : allDetails[0]?.path;

chat = initializeChat(allDetails, initialPath);
initializePanelResize();
initializeRatings();
initializeGitPanel();
