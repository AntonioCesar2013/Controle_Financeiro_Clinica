import assert from "node:assert/strict";
import { localDate } from "../frontend/js/utils/formatters.js";

process.env.TZ = "America/Sao_Paulo";
assert.equal(localDate(new Date("2026-09-04T00:30:00Z")), "2026-09-03");
assert.equal(localDate(new Date("2026-10-01T01:59:00Z")), "2026-09-30");
assert.equal(localDate(new Date("2027-01-01T03:01:00Z")), "2027-01-01");
console.log("3 cenários de data local aprovados.");
const { matchesFilters } = await import("../frontend/js/components/filters.js");
assert(matchesFilters({search: "José da Silva 12345678901", status: "Ativo", date: "2026-09-03"}, {search: "jose silva", status: "Ativo", start: "2026-09-01", end: "2026-09-30"}));
assert(matchesFilters({search: "12345678901"}, {search: "123.456.789-01"}));
assert(!matchesFilters({search: "José", status: "Inativo", date: "2026-08-31"}, {status: "Ativo"}));
assert(!matchesFilters({search: "José", date: "2026-08-31"}, {start: "2026-09-01"}));
console.log("4 cenários de filtros aprovados.");
