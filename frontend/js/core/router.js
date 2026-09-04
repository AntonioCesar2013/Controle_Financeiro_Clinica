export function createPanelRegistry(modules, renderers) {
    return Object.assign({}, ...modules.map((module) => module.panels(renderers)));
}

export function resolvePanel(registry, name) {
    return registry[name] || null;
}
