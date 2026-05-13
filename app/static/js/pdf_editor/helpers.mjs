/**
 * Pure helpers for the PDF Konva designer (invoice + quote).
 * Loaded via dynamic import() from the Jinja-rendered admin templates.
 */

/** @param {import('konva').Node[]} nodes */
export function unionClientRect(nodes) {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const n of nodes) {
        if (!n || typeof n.getClientRect !== 'function') continue;
        if (n.visible && !n.visible()) continue;
        const r = n.getClientRect({ skipTransform: false });
        minX = Math.min(minX, r.x);
        minY = Math.min(minY, r.y);
        maxX = Math.max(maxX, r.x + r.width);
        maxY = Math.max(maxY, r.y + r.height);
    }
    if (minX === Infinity) {
        return { x: 0, y: 0, width: 0, height: 0, right: 0, bottom: 0 };
    }
    return {
        x: minX,
        y: minY,
        width: maxX - minX,
        height: maxY - minY,
        right: maxX,
        bottom: maxY,
    };
}

/**
 * Collect vertical/horizontal snap lines from other nodes (stage coords).
 * @param {import('konva').Layer} layer
 * @param {import('konva').Node[]} exclude
 */
export function collectSnapLines(layer, exclude) {
    const lines = [];
    const ex = new Set(exclude);
    if (!layer || !layer.getChildren) return lines;
    layer.getChildren().forEach((child) => {
        if (!child || ex.has(child)) return;
        const nm = child.attrs && child.attrs.name;
        if (nm === 'background' || nm === 'page-border' || child.className === 'Transformer') return;
        if (child.visible && !child.visible()) return;
        const r = child.getClientRect({ skipTransform: false });
        const midX = r.x + r.width / 2;
        const midY = r.y + r.height / 2;
        lines.push(
            { kind: 'v', pos: r.x, min: r.y, max: r.y + r.height },
            { kind: 'v', pos: r.x + r.width, min: r.y, max: r.y + r.height },
            { kind: 'v', pos: midX, min: r.y, max: r.y + r.height },
            { kind: 'h', pos: r.y, min: r.x, max: r.x + r.width },
            { kind: 'h', pos: r.y + r.height, min: r.x, max: r.x + r.width },
            { kind: 'h', pos: midY, min: r.x, max: r.x + r.width }
        );
    });
    return lines;
}

/**
 * Snap drag delta for a set of moving nodes to alignment guides.
 * @param {import('konva').Node[]} movingNodes
 */
export function snapDragByGuides(layer, movingNodes, tolerancePx = 6) {
    const lines = collectSnapLines(layer, [...movingNodes]);
    if (!movingNodes.length || !lines.length) return { dx: 0, dy: 0, guides: [] };

    const box = unionClientRect(movingNodes);
    const vEdges = [box.x, box.x + box.width / 2, box.right];
    const hEdges = [box.y, box.y + box.height / 2, box.bottom];

    let bestDx = 0;
    let bestAbsDx = tolerancePx + 1;
    const vGuides = [];
    for (const L of lines) {
        if (L.kind !== 'v') continue;
        for (const edge of vEdges) {
            const d = L.pos - edge;
            if (Math.abs(d) <= tolerancePx && Math.abs(d) < bestAbsDx) {
                bestAbsDx = Math.abs(d);
                bestDx = d;
                vGuides.length = 0;
                vGuides.push({ kind: 'v', x: L.pos, y1: L.min, y2: L.max });
            }
        }
    }

    let bestDy = 0;
    let bestAbsDy = tolerancePx + 1;
    const hGuides = [];
    for (const L of lines) {
        if (L.kind !== 'h') continue;
        for (const edge of hEdges) {
            const d = L.pos - edge;
            if (Math.abs(d) <= tolerancePx && Math.abs(d) < bestAbsDy) {
                bestAbsDy = Math.abs(d);
                bestDy = d;
                hGuides.length = 0;
                hGuides.push({ kind: 'h', y: L.pos, x1: L.min, x2: L.max });
            }
        }
    }

    return { dx: bestDx, dy: bestDy, guides: [...vGuides, ...hGuides] };
}

/** @param {import('konva').Node[]} nodes */
export function distributeHorizontal(nodes) {
    if (!nodes || nodes.length < 3) return;
    const items = nodes
        .map((n) => ({ n, rect: n.getClientRect({ skipTransform: false }) }))
        .sort((a, b) => a.rect.x - b.rect.x);
    const left = items[0].rect.x;
    const right = items[items.length - 1].rect.x + items[items.length - 1].rect.width;
    const totalW = items.reduce((s, i) => s + i.rect.width, 0);
    const n = items.length;
    const gap = (right - left - totalW) / (n - 1);
    let x = left;
    for (let i = 0; i < n; i++) {
        const { n: node, rect } = items[i];
        const dx = x - rect.x;
        node.x(node.x() + dx);
        x += rect.width + gap;
    }
}

/** @param {import('konva').Node[]} nodes */
export function distributeVertical(nodes) {
    if (!nodes || nodes.length < 3) return;
    const items = nodes
        .map((n) => ({ n, rect: n.getClientRect({ skipTransform: false }) }))
        .sort((a, b) => a.rect.y - b.rect.y);
    const top = items[0].rect.y;
    const bottom = items[items.length - 1].rect.y + items[items.length - 1].rect.height;
    const totalH = items.reduce((s, i) => s + i.rect.height, 0);
    const n = items.length;
    const gap = (bottom - top - totalH) / (n - 1);
    let y = top;
    for (let i = 0; i < n; i++) {
        const { n: node, rect } = items[i];
        const dy = y - rect.y;
        node.y(node.y() + dy);
        y += rect.height + gap;
    }
}
