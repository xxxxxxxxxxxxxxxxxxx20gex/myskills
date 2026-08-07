export function createArtifacts(artifacts, apiBase) {
  const container = document.createElement('div');
  container.className = 'message-artifacts';

  artifacts.forEach(artifact => {
    const card = document.createElement('article');
    card.className = 'artifact';
    const preview = document.createElement('div');
    preview.className = 'artifact-preview';
    const url = `${apiBase}${artifact.url}`;
    let media;

    if (artifact.mime.startsWith('image/')) {
      media = document.createElement('img');
      media.alt = artifact.name;
      media.loading = 'lazy';
      media.src = url;
    } else if (artifact.mime.startsWith('audio/')) {
      media = document.createElement('audio');
      media.controls = true;
      media.src = url;
    } else if (artifact.mime.startsWith('video/')) {
      media = document.createElement('video');
      media.controls = true;
      media.src = url;
    } else if (artifact.mime === 'text/html') {
      media = document.createElement('iframe');
      media.title = artifact.name;
      media.sandbox = 'allow-scripts';
      media.src = url;
    } else {
      media = document.createElement('span');
      media.textContent = artifact.mime.startsWith('text/') ? '文本文件' : '文件';
    }

    preview.append(media);
    const meta = document.createElement('div');
    meta.className = 'artifact-meta';
    const name = document.createElement('span');
    name.title = artifact.name;
    name.textContent = artifact.name;
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = '打开';
    meta.append(name, link);
    card.append(preview, meta);
    container.append(card);
  });

  return container;
}
