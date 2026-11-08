/**
 * Suggest a project from the active tab URL (no content scripts).
 * Matches project name / code tokens against hostname + path.
 */

function tokensFromProject(project) {
  const parts = [];
  if (project?.name) parts.push(String(project.name));
  if (project?.code) parts.push(String(project.code));
  return parts
    .flatMap((s) => s.toLowerCase().split(/[^a-z0-9]+/g))
    .filter((t) => t.length >= 3);
}

/**
 * @param {string|null|undefined} url
 * @param {Array<{id:number,name?:string,code?:string|null}>} projects
 * @returns {{id:number,name?:string,code?:string|null}|null}
 */
export function suggestProjectFromUrl(url, projects) {
  if (!url || !Array.isArray(projects) || projects.length === 0) return null;
  let haystack = '';
  try {
    const u = new URL(url);
    haystack = `${u.hostname}${u.pathname}`.toLowerCase();
  } catch {
    haystack = String(url).toLowerCase();
  }

  let best = null;
  let bestScore = 0;
  for (const project of projects) {
    const tokens = tokensFromProject(project);
    if (!tokens.length) continue;
    let score = 0;
    for (const token of tokens) {
      if (haystack.includes(token)) score += token.length;
    }
    if (score > bestScore) {
      bestScore = score;
      best = project;
    }
  }
  return best;
}
