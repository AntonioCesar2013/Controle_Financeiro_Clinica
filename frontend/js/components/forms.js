export function setFormBusy(form, busy) {
    form.setAttribute("aria-busy", String(busy));
    form.querySelectorAll("input, button, select, textarea").forEach((element) => {
        element.disabled = busy;
    });
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
        if (busy) {
            button.dataset.idleLabel = button.textContent;
            button.textContent = "Processando…";
        } else if (button.dataset.idleLabel) {
            button.textContent = button.dataset.idleLabel;
            delete button.dataset.idleLabel;
        }
    });
}
