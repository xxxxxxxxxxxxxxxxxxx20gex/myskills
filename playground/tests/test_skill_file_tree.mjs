import assert from 'node:assert/strict';
import { groupFileTreeEntries } from '../static/js/skill-file-tree.js';

const grouped = groupFileTreeEntries([
  { path: 'assets/icons/logo.svg', name: 'logo.svg', type: 'file' },
  { path: 'SKILL.md', name: 'SKILL.md', type: 'file', readable: true },
  { path: 'assets', name: 'assets', type: 'directory' },
  { path: 'assets/icons', name: 'icons', type: 'directory' },
]);

assert.deepEqual(grouped.get('').map(entry => entry.path), ['assets', 'SKILL.md']);
assert.deepEqual(grouped.get('assets').map(entry => entry.path), ['assets/icons']);
assert.deepEqual(grouped.get('assets/icons').map(entry => entry.path), ['assets/icons/logo.svg']);

console.log('skill file tree tests passed');
