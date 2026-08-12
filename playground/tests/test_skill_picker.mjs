import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../../skills-showcase.html', import.meta.url), 'utf8');
const chat = fs.readFileSync(new URL('../static/js/chat.js', import.meta.url), 'utf8');
const app = fs.readFileSync(new URL('../static/js/app.js', import.meta.url), 'utf8');

assert.match(html, /id="runner-skill-search"/, '页面应提供可搜索的 Skill 输入框');
assert.match(html, /id="runner-skill-options"/, '页面应提供 Skill 浮层选项列表');
assert.match(chat, /filteredSkillDetails/, '对话模块应按关键词过滤 Skill');
assert.match(chat, /ArrowDown|ArrowUp/, 'Skill 选择器应支持键盘导航');
assert.match(app, /自创skills\/manage-myskills/, '默认 Skill 应为项目管理 Skill');
assert.match(chat, /activeDetail\?\.name/, '选择器应同步当前 Skill 名称');

console.log('skill-picker tests passed');
