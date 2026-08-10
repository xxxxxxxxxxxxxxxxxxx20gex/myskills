import assert from 'node:assert/strict';
import { createConversationState } from '../static/js/conversation-state.js';

const state = createConversationState();
const firstToken = state.begin();
assert.equal(firstToken, 0);
assert.equal(state.running, true);
assert.equal(state.begin(), null, '同一对话不能重复启动任务');

state.reset();
assert.equal(state.running, false);
assert.equal(state.isCurrent(firstToken), false, '重置后旧任务必须失效');
assert.equal(state.finish(firstToken), false, '旧任务不能结束新对话的状态');

const secondToken = state.begin();
assert.equal(secondToken, 1);
assert.equal(state.finish(secondToken), true);
assert.equal(state.running, false);

console.log('conversation-state tests passed');
