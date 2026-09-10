import assert from 'node:assert/strict';
import { balanceFields } from '../frontend/js/components/conference.js';
import { businessModules } from '../frontend/js/modules/index.js';
import { createPanelRegistry } from '../frontend/js/core/router.js';

const html = balanceFields([
    { chave:'CARTEIRA:1',tipo:'CARTEIRA',nome:'<script>alert(1)</script>',valor:-500 },
    { chave:'ESTOQUE:1',tipo:'ESTOQUE',nome:'Produto',valor:7,unidade:'UN' },
]);
assert(!html.includes('<script>'));
assert(html.includes('&lt;script&gt;'));
assert.match(html,/step="1" min="0" data-conference-value="ESTOQUE:1"/);
assert.match(html,/step="0.01"  data-conference-value="CARTEIRA:1"/);
assert(!html.includes('value="-5"'), 'Valores externos não devem ser preenchidos automaticamente');
assert(createPanelRegistry(businessModules,new Proxy({}, {get:()=>()=>{}})).conferencia);
console.log('Conferência: campos monetários, estoque, saldo negativo, escape HTML e painel validados.');
