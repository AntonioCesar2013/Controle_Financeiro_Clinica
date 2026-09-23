import assert from "node:assert/strict";
import { calcularSaldoPrevisto, createAdministrationItems } from "../frontend/js/components/itens-administracao.js";
import { renderActionTable, renderTable } from "../frontend/js/components/renderers.js";

let panel, alert, refreshed=0;
const row={id:1,nome:'Mesa <script>',codigo_patrimonio:'PAT-1',categoria:'Móveis',setor_nome:'Admin',setor_id:1,
    localizacao:'Sala',quantidade:0,unidade_medida:'UN',estado_conservacao:'BOM',ativo:1,versao:3,
    descricao:null,data_aquisicao:null,valor_aquisicao:null};
const api=async path=>{
    if(path.startsWith('/api/administracao/itens/historico')) return {dados:{linhas:[{tipo:'EDICAO',data_movimentacao:'2026-09-21',registrado_em:'2026-09-21 10:00:00',quantidade_anterior:0,variacao:0,quantidade_resultante:0,setor_anterior_nome:'<origem>',setor_novo_nome:'Admin',motivo:'<motivo>',dados_anteriores:'{\"nome\":\"<antigo>\"}',dados_novos:'{\"nome\":\"Novo\"}'}]}};
    if(path.startsWith('/api/administracao/itens/detalhe')) return {dados:row};
    if(path.startsWith('/api/administracao/itens?')) return {dados:{linhas:[row],indicadores:{registros:1,ativos:1,ruim:0,inservivel:0,quantidades:{UN:0}},pagina:1,tamanho:50,total_geral:1,total_filtrado:1}};
    if(path==='/api/financeiro/cadastros') return {dados:{setores:[{id:1,nome:'Admin',ativo:1}]}};
    return {sucesso:true};
};
const module=createAdministrationItems({api,renderActionTable,renderTable,showPanel:(title,body)=>{panel={title,body};},showAlert:(t,m)=>{alert={t,m};},closePanel:()=>{},refresh:async()=>{refreshed++;}});
const html=await module.render();
assert.match(html,/Itens administrativos|Item selecionado/);
assert.match(html,/Mesa &lt;script&gt;/);
assert.match(html,/data-action="select-report-row"/);
assert.doesNotMatch(html,/data-column-key="acoes"/);
assert.match(html,/Quantidade por unidade/);
assert.doesNotMatch(html,/R\$/);
assert.match(html,/data-selection-action="move" disabled/);
module.click({dataset:{action:'admin-item-form',kind:'edit',id:'1'}});await new Promise(r=>setTimeout(r,0));
assert.match(panel.body,/name="versao_esperada" value="3"/);assert.doesNotMatch(panel.body,/name="quantidade"/);
module.click({dataset:{action:'admin-item-form',kind:'move',id:'1'}});await new Promise(r=>setTimeout(r,0));
assert.match(panel.body,/AJUSTE/);assert.match(panel.body,/Saldo atual/);assert.match(panel.body,/Saldo previsto/);
assert.match(panel.body,/baixa total deixará o saldo zerado e inativará automaticamente/);
assert.equal(calcularSaldoPrevisto('ENTRADA',3,2),5);
assert.equal(calcularSaldoPrevisto('SAIDA',5,1),4);
assert.equal(calcularSaldoPrevisto('AJUSTE',4,2),2);
assert.equal(calcularSaldoPrevisto('BAIXA',2,2),0);
row.setor_id=9;row.setor_nome='Arquivo inativo';row.setor_ativo=0;
module.state.setores=[{id:2,nome:'Manutenção',ativo:1}];
module.click({dataset:{action:'admin-item-form',kind:'transfer',id:'1'}});await new Promise(r=>setTimeout(r,0));
assert.match(panel.body,/Origem: <strong>Arquivo inativo/);
assert.match(panel.body,/<option value="">Escolha o setor de destino<\/option>/);
assert.doesNotMatch(panel.body,/value="2" selected/);
assert.match(panel.body,/Destino: escolha um setor/);
module.state.setores=[];alert=null;
module.click({dataset:{action:'admin-item-form',kind:'transfer',id:'1'}});await new Promise(r=>setTimeout(r,0));
assert.equal(alert.t,'Transferência indisponível');assert.match(alert.m,/Não há setor ativo/);
module.click({dataset:{action:'admin-item-history',id:'1'}});await new Promise(r=>setTimeout(r,0));
assert.match(panel.body,/&lt;motivo&gt;/);assert.doesNotMatch(panel.body,/<motivo>/);
assert.equal(module.change({matches:s=>s==='[data-admin-filter]',dataset:{adminFilter:'ativo'},value:'0'}),true);
assert.equal(module.state.ativo,'0');
console.log('Itens administrativos: painel, seleção, filtros, formulários e escape validados.');
