"""Entrada em reais na API; valores internos sempre em centavos inteiros."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def reais_para_centavos(valor):
    if isinstance(valor, bool):
        raise ValueError("Valor monetário inválido.")
    texto = str(valor if valor not in (None, "") else "0").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto)
        if not numero.is_finite():
            raise ValueError("Valor monetário inválido.")
        centavos = int((numero * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, OverflowError) as erro:
        raise ValueError("Valor monetário inválido.") from erro
    if abs(centavos) > 9_000_000_000_000_000:
        raise ValueError("Valor monetário fora do limite.")
    return centavos


def validar_centavos(valor):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError("Informe o valor em centavos inteiros.")
    if abs(valor) > 9_000_000_000_000_000:
        raise ValueError("Valor monetário fora do limite.")
    return valor
