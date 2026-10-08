// Mantém filtros e ações fora da área rolável de cada listagem.
export function organizeTablePanels(root) {
    for (const scope of root.querySelectorAll('.selection-scope')) {
        const filters = scope.querySelector('.table-filters');
        const toolbar = scope.querySelector('.selection-toolbar');
        if (filters && toolbar) filters.after(toolbar);
        scope.querySelectorAll('.table-interaction-hint').forEach(node => node.remove());
        for (const meta of scope.querySelectorAll('.filterable__meta')) {
            const paging = [...meta.querySelectorAll('[data-page]')];
            if (paging.length) {
                if (toolbar) toolbar.after(meta);
                meta.classList.add('table-pagination');
            } else {
                const clear = meta.querySelector('[data-action="clear-table-filters"]');
                if (clear && toolbar) {
                    const internmentActions = toolbar.querySelector('.internment-actions');
                    (internmentActions || toolbar).append(clear);
                }
                meta.classList.add('table-filter-feedback');
            }
        }
    }
    const panels = [...root.querySelectorAll('.panel:not(.panel--menu)')];
    if (root.matches?.('.panel:not(.panel--menu)')) panels.unshift(root);
    for (const panel of panels) {
        const body = panel.querySelector('.panel__body');
        const scope = body.querySelector(':scope > .selection-scope');
        if (!scope || body.querySelector('form') || body.querySelectorAll('.table-wrap').length !== 1) continue;
        panel.classList.add('panel--table-layout');
        const table = scope.querySelector('.table-wrap');
        let parent = table.parentElement;
        while (parent && parent !== body) {
            parent.classList.add('table-layout-stack');
            parent = parent.parentElement;
        }
    }
}
