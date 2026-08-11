import assert from 'node:assert/strict';
import { renderMarkdown } from '../static/js/markdown.js';

const table = renderMarkdown(`| 名称 | 状态 | 数量 |
| :--- | :---: | ---: |
| **文档** | 正常 | 12 |
| 图片 | \`生成中\` | 3 |`);

assert.match(table, /<div class="markdown-table-wrap"><table>/, '表格应使用可横向滚动的容器');
assert.match(table, /<th class="align-left">名称<\/th>/, '左对齐表头应正确渲染');
assert.match(table, /<th class="align-center">状态<\/th>/, '居中表头应正确渲染');
assert.match(table, /<td class="align-right">12<\/td>/, '右对齐单元格应正确渲染');
assert.match(table, /<strong>文档<\/strong>/, '单元格应支持安全的行内 Markdown');
assert.match(table, /<code>生成中<\/code>/, '表格单元格应支持行内代码');

const tasks = renderMarkdown(`- [ ] 待处理
- [x] **已完成**
- 普通条目`);

assert.match(tasks, /type="checkbox" disabled>待处理/, '未完成任务应显示禁用复选框');
assert.match(tasks, /type="checkbox" disabled checked><strong>已完成<\/strong>/, '完成任务应显示勾选状态');
assert.match(tasks, /<li>普通条目<\/li>/, '任务列表中应继续支持普通条目');

const escaped = renderMarkdown('| 字段 | 内容 |\n| --- | --- |\n| 安全 | <script>alert(1)</script> |');
assert.ok(!escaped.includes('<script>'), '表格内容不得执行原始 HTML');
assert.match(escaped, /&lt;script&gt;/, '表格内容应转义原始 HTML');

console.log('markdown tests passed');
