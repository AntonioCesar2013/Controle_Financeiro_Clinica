function digits(value, limit) {
    return String(value || "").replace(/\D/g, "").slice(0, limit);
}

export function maskCpf(value) {
    const number = digits(value, 11);
    return number
        .replace(/^(\d{3})(\d)/, "$1.$2")
        .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export function maskCnpj(value) {
    const number = digits(value, 14);
    return number
        .replace(/^(\d{2})(\d)/, "$1.$2")
        .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/\.(\d{3})(\d)/, ".$1/$2")
        .replace(/(\/\d{4})(\d)/, "$1-$2");
}

export function maskDocument(value) {
    return digits(value, 14).length > 11 ? maskCnpj(value) : maskCpf(value);
}

export function maskPhone(value) {
    const number = digits(value, 11);
    if (number.length <= 2) return number ? `(${number}` : "";
    if (number.length <= 6) return number.replace(/^(\d{2})(\d+)/, "($1) $2");
    if (number.length <= 10) return number.replace(/^(\d{2})(\d{4})(\d+)/, "($1) $2-$3");
    return number.replace(/^(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
}

export function applyInputMask(input) {
    const formatters = { cpf: maskCpf, document: maskDocument, phone: maskPhone };
    const formatter = formatters[input?.dataset?.mask];
    if (!formatter) return;
    input.value = formatter(input.value);
}

export function applyInputMasks(root) {
    root.querySelectorAll("input[data-mask]").forEach(applyInputMask);
}
