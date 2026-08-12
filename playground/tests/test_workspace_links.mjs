import assert from 'node:assert/strict';
import { renderMarkdown } from '../static/js/markdown.js';

const html = renderMarkdown('文件：C:\\Users\\WUJIEAI\\Desktop\\myskills\\demo.png', {
  resolveFile: path => `/api/runs/demo/workspace?path=${encodeURIComponent(path)}`,
});
assert.match(html, /workspace-file-link/, '工作区绝对路径应渲染为可点击链接');
assert.match(html, /api\/runs\/demo\/workspace/, '工作区链接应指向受限预览接口');

const markdownLink = renderMarkdown('[查看报告](C:/Users/WUJIEAI/Desktop/myskills/report.pdf)', {
  resolveFile: path => `view?path=${encodeURIComponent(path)}`,
});
assert.match(markdownLink, /<a href="view\?path=/, 'Markdown 本地路径链接应可点击');

console.log('workspace-link tests passed');
