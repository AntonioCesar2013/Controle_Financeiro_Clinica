export function setFormBusy(form, busy) {
    form.querySelectorAll("input, button, select, textarea").forEach((element) => {
        element.disabled = busy;
    });
}
