export function composeAttachmentPrompt(prompt, uploads) {
  const attachmentText = uploads.length
    ? `附件：\n${uploads.map(item => `- ${item.path}`).join('\n')}`
    : '';
  return [prompt, attachmentText].filter(value => value.trim()).join('\n\n');
}
