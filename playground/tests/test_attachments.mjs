import assert from 'node:assert/strict';
import { composeAttachmentPrompt } from '../static/js/attachment-prompt.js';

assert.equal(composeAttachmentPrompt('原始输入', []), '原始输入');
assert.equal(
  composeAttachmentPrompt('请分析', [
    { path: 'C:\\work\\one.pdf' },
    { path: 'C:\\work\\two.png' },
  ]),
  '请分析\n\n附件：\n- C:\\work\\one.pdf\n- C:\\work\\two.png',
);
assert.equal(
  composeAttachmentPrompt('', [{ path: 'C:\\work\\only.docx' }]),
  '附件：\n- C:\\work\\only.docx',
);

console.log('attachment tests passed');
