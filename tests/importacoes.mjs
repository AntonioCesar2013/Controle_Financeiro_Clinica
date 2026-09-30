import assert from "node:assert/strict";
import { parseCsv } from "../frontend/js/components/importacoes.js";

const linhas = parseCsv("\uFEFFinternacao_id;numero_parcela;tipo;data_vencimento;valor;desconto\r\n1;2;MENSALIDADE;2026-10-10;1500,00;0,00\r\n");
assert.equal(linhas.length, 1);
assert.equal(linhas[0].valor, "1500,00");
assert.equal(linhas[0].numero_parcela, "2");
assert.throws(() => parseCsv("internacao_id;tipo\n1;MENSALIDADE"), /Colunas obrigatórias ausentes/);
console.log("Leitura e validação estrutural do CSV verificadas.");
