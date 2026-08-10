export function groupFileTreeEntries(entries) {
  const childrenByParent = new Map([['', []]]);
  entries.forEach(entry => {
    const separator = entry.path.lastIndexOf('/');
    const parent = separator === -1 ? '' : entry.path.slice(0, separator);
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(entry);
    if (entry.type === 'directory' && !childrenByParent.has(entry.path)) {
      childrenByParent.set(entry.path, []);
    }
  });
  childrenByParent.forEach(children => children.sort((left, right) => {
    if (left.type !== right.type) return left.type === 'directory' ? -1 : 1;
    return left.name.localeCompare(right.name, 'zh-CN');
  }));
  return childrenByParent;
}
