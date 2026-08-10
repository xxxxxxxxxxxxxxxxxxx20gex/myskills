import assert from 'node:assert/strict';
import { repositorySkills, skillCategories, skillDetails } from '../static/js/data.js';

const expectedSkills = new Set([
  ...Object.keys(skillDetails),
  ...repositorySkills.map(skill => skill.folder),
]);
const categorizedSkills = skillCategories.flatMap(category => category.skills);

assert.equal(new Set(skillCategories.map(category => category.id)).size, skillCategories.length, '功能分类 ID 不能重复');
assert.equal(new Set(categorizedSkills).size, categorizedSkills.length, '同一个 Skill 不能属于多个功能分类');
assert.deepEqual(new Set(categorizedSkills), expectedSkills, '每个 Skill 必须且只能属于一个功能分类');
assert.ok(repositorySkills.every(skill => skill.category), '收集的 Skill 必须具有功能分类');
assert.ok(Object.values(skillDetails).every(detail => detail.category), '自创 Skill 必须具有功能分类');

console.log(`catalog-data tests passed: ${expectedSkills.size} skills in ${skillCategories.length} categories`);
