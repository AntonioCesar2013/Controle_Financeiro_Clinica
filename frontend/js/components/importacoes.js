import { escapeHtml, formatMoney } from "../utils/formatters.js";

const COLUNAS = ["internacao_id", "numero_parcela", "tipo", "data_vencimento", "valor", "desconto"];

function separarLinha(linha, separador) {
    const campos=[]; let atual="", aspas=false;
    for(let i=0;i<linha.length;i+=1){
        const c=linha[i];
        if(c==='"'&&aspas&&linha[i+1]==='"'){atual+='"';i+=1;continue;}
        if(c==='"'){aspas=!aspas;continue;}
        if(c===separador&&!aspas){campos.push(atual.trim());atual="";continue;}
        atual+=c;
    }
    if(aspas)throw new Error("O CSV possui aspas não fechadas.");
    campos.push(atual.trim()); return campos;
}

export function parseCsv(texto) {
    const limpo=String(texto||"").replace(/^\uFEFF/,"").replace(/\r\n?/g,"\n").trim();
    if(!limpo)throw new Error("O arquivo CSV está vazio.");
    const linhas=limpo.split("\n").filter(l=>l.trim());
    const separador=(linhas[0].match(/;/g)||[]).length >= (linhas[0].match(/,/g)||[]).length ? ";" : ",";
    const cabecalho=separarLinha(linhas.shift(),separador).map(x=>x.trim().toLowerCase());
    const ausentes=COLUNAS.filter(c=>!cabecalho.includes(c));
    if(ausentes.length)throw new Error(`Colunas obrigatórias ausentes: ${ausentes.join(", ")}.`);
    if(linhas.length>1000)throw new Error("O arquivo aceita no máximo 1000 linhas por importação.");
    return linhas.map((linha,indice)=>{
        const valores=separarLinha(linha,separador);
        if(valores.length!==cabecalho.length)throw new Error(`Linha ${indice+2}: quantidade de colunas diferente do cabeçalho.`);
        return Object.fromEntries(cabecalho.map((coluna,i)=>[coluna,valores[i]]));
    });
}

export function createImports({api,showAlert}) {
    let linhas=[]; let previa=null;
    let internacoes=[];
    const endpoint="/api/administracao/importacoes/contas-receber";
    async function render(){
        linhas=[];previa=null;
        internacoes=(await api("/api/internacoes")).dados||[];
        const referencia=internacoes.length?`<details><summary>Consultar códigos das internações</summary><div class="table-wrap"><table><thead><tr><th>Código</th><th>Residente</th><th>Responsável</th><th>Situação</th></tr></thead><tbody>${internacoes.map(x=>`<tr><td>${x.id}</td><td>${escapeHtml(x.residente_nome)}</td><td>${escapeHtml(x.responsavel_nome)}</td><td>${escapeHtml(x.status)}</td></tr>`).join("")}</tbody></table></div></details>`:'<p class="form-note">Nenhuma internação cadastrada. Cadastre uma internação antes de importar contas.</p>';
        return `<section class="selection-scope"><div class="workspace-intro"><div><h3>Importar contas a receber</h3><p>Envie um CSV UTF-8 separado por ponto e vírgula. A prévia não altera os dados.</p></div><button class="button button--secondary" type="button" data-action="download-receivables-template">Baixar modelo CSV</button></div>${referencia}<form class="login-form" data-receivables-import><div class="field"><label>Arquivo CSV</label><input type="file" accept=".csv,text/csv" data-import-file required${internacoes.length?"":" disabled"}></div><p class="form-note">Colunas: internacao_id, numero_parcela, tipo, data_vencimento, valor e desconto. Tipos: ACOLHIMENTO, MENSALIDADE e OUTRO.</p><p class="login-error" data-import-error role="alert"></p><div data-import-preview><div class="empty-state"><p>Selecione um arquivo para validar e visualizar os lançamentos.</p></div></div><button class="button" type="submit" data-import-confirm disabled>Confirmar importação</button></form></section>`;
    }
    function tabela(resultado){
        const resumo=`<div class="inventory-summary"><article><span>Linhas</span><strong>${resultado.total}</strong></article><article><span>Novas</span><strong>${resultado.novas}</strong></article><article><span>Duplicadas</span><strong>${resultado.duplicadas}</strong></article><article><span>Erros</span><strong>${resultado.erros.length}</strong></article></div>`;
        const erros=resultado.erros.length?`<div class="form-note"><strong>Erros encontrados:</strong><ul>${resultado.erros.slice(0,20).map(x=>`<li>Linha ${x.linha}: ${escapeHtml(x.erro)}</li>`).join("")}</ul></div>`:"";
        const registros=resultado.linhas.length?`<div class="table-wrap"><table><thead><tr><th>Linha</th><th>Internação</th><th>Residente</th><th>Parcela</th><th>Tipo</th><th>Vencimento</th><th>Valor</th><th>Situação</th></tr></thead><tbody>${resultado.linhas.map(x=>`<tr><td>${x.linha}</td><td>${x.internacao_id}</td><td>${escapeHtml(x.residente_nome)}</td><td>${x.numero_parcela}</td><td>${escapeHtml(x.tipo)}</td><td>${escapeHtml(x.data_vencimento)}</td><td>${formatMoney(x.valor)}</td><td>${x.duplicada?"Duplicada":"Nova"}</td></tr>`).join("")}</tbody></table></div>`:"";
        return `${resumo}${erros}${registros}${resultado.total>100?'<p class="form-note">A prévia exibe somente as primeiras 100 linhas válidas.</p>':""}`;
    }
    async function change(input){
        if(!input.matches("[data-import-file]"))return false;
        const form=input.closest("form"), erro=form.querySelector("[data-import-error]"), botao=form.querySelector("[data-import-confirm]");
        erro.textContent="";botao.disabled=true;previa=null;
        try{
            const arquivo=input.files?.[0];
            if(!arquivo)throw new Error("Selecione um arquivo CSV.");
            if(arquivo.size>2_000_000)throw new Error("O arquivo deve ter no máximo 2 MB.");
            linhas=parseCsv(await arquivo.text());
            const resposta=await api(endpoint,{method:"POST",body:{acao:"PREVIA",linhas}});
            previa=resposta;form.querySelector("[data-import-preview]").innerHTML=tabela(resposta);
            botao.disabled=Boolean(resposta.erros.length)||resposta.novas===0;
        }catch(e){linhas=[];erro.textContent=e.message;form.querySelector("[data-import-preview]").innerHTML="";}
        return true;
    }
    async function submit(form){
        const erro=form.querySelector("[data-import-error]"), botao=form.querySelector("[data-import-confirm]");
        if(!previa||previa.erros.length||!previa.novas)return;
        botao.disabled=true;erro.textContent="";
        try{
            const resultado=await api(endpoint,{method:"POST",body:{acao:"IMPORTAR",linhas}});
            showAlert("Importação concluída",`${resultado.importadas} conta(s) importada(s); ${resultado.duplicadas} duplicada(s) ignorada(s).`);
            form.reset();linhas=[];previa=null;form.querySelector("[data-import-preview]").innerHTML='<div class="empty-state"><p>Importação concluída. Selecione outro arquivo para continuar.</p></div>';
        }catch(e){erro.textContent=e.message;botao.disabled=false;}
    }
    function download(){
        const exemplo=internacoes[0]?.id||1;
        const conteudo=`internacao_id;numero_parcela;tipo;data_vencimento;valor;desconto\r\n${exemplo};1;MENSALIDADE;2026-10-10;1500,00;0,00\r\n`;
        const link=document.createElement("a");link.href=URL.createObjectURL(new Blob(["\uFEFF"+conteudo],{type:"text/csv;charset=utf-8"}));link.download="modelo_contas_a_receber.csv";link.click();URL.revokeObjectURL(link.href);
    }
    function click(target){if(target.dataset.action==="download-receivables-template"){download();return true;}return false;}
    return {render,change,submit,click};
}
