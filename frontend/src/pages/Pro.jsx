import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Busca, Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, confirmar, limparVazios, useDados } from "../components/ui";
import { useApp } from "../contexto";
import { dataBR, hojeISO, pct } from "../util";

const COR_DOC = { OK: "verde", PENDENTE: "laranja", A_VALIDAR: "amarela", NA: "neutra" };
const COR_STATUS = { Completo: "verde", Incompleto: "laranja", "Sem evidência": "vermelha", "Não aplicável": "neutra" };
const SIGLA_DOC = { apr: "APR", pex: "PEX", cr: "CR", lista_forum: "FOR", lista_rpac: "RPAC", forum_aprovacao: "APROV" };

function FormPro({ inicial, contratadas, aoSalvar, aoFechar }) {
  const { opcoes, listas } = useApp();
  const [form, setForm] = useState(inicial);
  const [erro, setErro] = useState("");
  const muda = (c) => (v) => setForm((f) => ({ ...f, [c]: v }));

  async function salvar(e) {
    e.preventDefault();
    try {
      const { id, ...resto } = form;
      const corpo = limparVazios(resto, ["contratada_id", "ativo_id", "coordenador_id", "prazo"]);
      if (id) await api(`/pro/${id}`, { method: "PUT", body: corpo });
      else await api("/pro", { method: "POST", body: corpo });
      avisar("Registro de PRO salvo.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    }
  }

  return (
    <form onSubmit={salvar} className="grade-form">
      <Campo rotulo="Contratada"><Busca valor={form.contratada_id} aoMudar={muda("contratada_id")} itens={contratadas} obrigatorio /></Campo>
      <Campo rotulo="Ativo"><Busca valor={form.ativo_id} aoMudar={muda("ativo_id")} itens={listas.ativos} obrigatorio /></Campo>
      <Campo rotulo="Coordenador técnico" dica="Se vazio, usa o coordenador do ativo">
        <Selecao valor={form.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores} vazio="Automático" />
      </Campo>
      <Campo rotulo="Data"><input type="date" value={form.data} required onChange={(e) => muda("data")(e.target.value)} /></Campo>
      <Campo rotulo="Atividade" largo><textarea rows={2} value={form.atividade} required minLength={3} onChange={(e) => muda("atividade")(e.target.value)} /></Campo>
      <fieldset className="docs campo-largo">
        <legend>Documentos</legend>
        {Object.entries(opcoes.documentos_pro).map(([campo, rotulo]) => (
          <div key={campo} className="doc-linha">
            <span>{rotulo}</span>
            <div className="segmentado" role="radiogroup" aria-label={rotulo}>
              {Object.entries(opcoes.situacoes_doc).map(([k, v]) => (
                <button type="button" key={k} className={form[campo] === k ? `sel sel-${COR_DOC[k]}` : ""}
                  onClick={() => muda(campo)(k)} aria-pressed={form[campo] === k}>{v}</button>
              ))}
            </div>
          </div>
        ))}
      </fieldset>
      <Campo rotulo="Responsável pela ação"><input value={form.responsavel_acao} onChange={(e) => muda("responsavel_acao")(e.target.value)} /></Campo>
      <Campo rotulo="Prazo"><input type="date" value={form.prazo || ""} onChange={(e) => muda("prazo")(e.target.value)} /></Campo>
      <Campo rotulo="Próxima ação" largo><input value={form.proxima_acao} onChange={(e) => muda("proxima_acao")(e.target.value)} /></Campo>
      <Campo rotulo="Link da evidência" largo dica="Pasta do SharePoint/Drive onde estão os documentos">
        <input type="url" placeholder="https://…" value={form.link_evidencia} onChange={(e) => muda("link_evidencia")(e.target.value)} />
      </Campo>
      <Campo rotulo="Observação" largo><textarea rows={2} value={form.observacao} onChange={(e) => muda("observacao")(e.target.value)} /></Campo>
      <Erro>{erro}</Erro>
      <div className="acoes campo-largo">
        <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-primario">Salvar</button>
      </div>
    </form>
  );
}

const NOVO = {
  contratada_id: "", ativo_id: "", coordenador_id: "", data: hojeISO(), atividade: "",
  apr: "PENDENTE", pex: "PENDENTE", cr: "PENDENTE", lista_forum: "PENDENTE", lista_rpac: "PENDENTE", forum_aprovacao: "PENDENTE",
  observacao: "", responsavel_acao: "", proxima_acao: "", link_evidencia: "", prazo: "",
};

export default function Pro() {
  const { opcoes, listas, pode } = useApp();
  const [params] = useSearchParams();
  const [filtros, setFiltros] = useState({ ativo_id: "", coordenador_id: "", contratada_id: "", status: "", q: "", somente_em_aberto: params.get("aberto") === "1" });
  const [editando, setEditando] = useState(null);
  const { dados, erro, carregando, recarregar } = useDados("/pro", filtros);
  const contratadas = useDados("/contratadas");
  const muda = (c) => (v) => setFiltros((f) => ({ ...f, [c]: v }));

  const paraForm = (r) => {
    const f = { ...NOVO };
    Object.keys(NOVO).forEach((k) => (f[k] = r[k] ?? ""));
    ["contratada_id", "ativo_id", "coordenador_id"].forEach((k) => (f[k] = r[k] ? String(r[k]) : ""));
    return { ...f, id: r.id };
  };

  async function excluir(r) {
    if (!confirmar(`Excluir o registro "${r.atividade.slice(0, 60)}"?`)) return;
    try {
      await api(`/pro/${r.id}`, { method: "DELETE" });
      avisar("Registro excluído.");
      recarregar();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>Evidências do PRO</h1>
          <p className="subtitulo">Planejamento de Risco Operacional — APR, PEX, CR, listas e fórum de aprovação por atividade.</p>
        </div>
        {pode.editar && <button className="botao botao-primario" onClick={() => setEditando({ ...NOVO })}>+ Novo registro</button>}
      </header>

      <div className="filtros">
        <Campo rotulo="Atividade"><input type="search" placeholder="Buscar…" value={filtros.q} onChange={(e) => muda("q")(e.target.value)} /></Campo>
        <Campo rotulo="Ativo"><Selecao valor={filtros.ativo_id} aoMudar={muda("ativo_id")} opcoes={listas.ativos} vazio="Todos" /></Campo>
        <Campo rotulo="Contratada"><Selecao valor={filtros.contratada_id} aoMudar={muda("contratada_id")} opcoes={contratadas.dados || []} vazio="Todas" /></Campo>
        <Campo rotulo="Coordenador"><Selecao valor={filtros.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores} vazio="Todos" /></Campo>
        <Campo rotulo="Status"><Selecao valor={filtros.status} aoMudar={muda("status")} opcoes={["Completo", "Incompleto", "Sem evidência", "Não aplicável"]} vazio="Todos" /></Campo>
        <label className="check">
          <input type="checkbox" checked={filtros.somente_em_aberto} onChange={(e) => muda("somente_em_aberto")(e.target.checked)} />
          Só com documento em aberto
        </label>
      </div>

      <Erro>{erro}</Erro>
      {carregando && !dados ? <Carregando /> : !dados?.length ? <Vazio>Nenhum registro encontrado.</Vazio> : (
        <div className="tabela-caixa">
          <p className="chip-total">{dados.length} registro(s)</p>
          <table className="tabela">
            <thead>
              <tr>
                <th>Data</th><th>Ativo</th><th>Contratada</th><th>Atividade</th><th>Documentos</th><th>Status</th>
                <th>Aderência</th><th>Responsável / prazo</th><th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {dados.map((r) => (
                <tr key={r.id} className={r.prazo_vencido ? "linha-alerta" : ""}>
                  <td className="nowrap">{dataBR(r.data)}</td>
                  <td>{r.ativo.nome}</td>
                  <td className="suave">{r.contratada.nome}</td>
                  <td className="obs">{r.atividade}</td>
                  <td>
                    <div className="docs-mini">
                      {Object.entries(SIGLA_DOC).map(([campo, sigla]) => (
                        <Etiqueta key={campo} tipo={COR_DOC[r[campo]]} titulo={`${opcoes.documentos_pro[campo]}: ${opcoes.situacoes_doc[r[campo]]}`}>{sigla}</Etiqueta>
                      ))}
                    </div>
                  </td>
                  <td><Etiqueta tipo={COR_STATUS[r.status_documental]}>{r.status_documental}</Etiqueta></td>
                  <td>{pct(r.aderencia)}</td>
                  <td className="suave">
                    {r.responsavel_acao}{r.prazo && <div className={r.prazo_vencido ? "texto-alerta" : ""}>até {dataBR(r.prazo)}</div>}
                  </td>
                  <td className="nowrap acoes-linha">
                    {r.link_evidencia && <a className="botao botao-pequeno" href={r.link_evidencia} target="_blank" rel="noreferrer">Abrir</a>}
                    <button className="botao botao-pequeno" onClick={() => setEditando(paraForm(r))}>{pode.editar ? "Editar" : "Ver"}</button>
                    {pode.editar && <button className="botao botao-pequeno botao-perigo" onClick={() => excluir(r)}>×</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal titulo={editando?.id ? "Editar registro de PRO" : "Novo registro de PRO"} aberto={Boolean(editando)}
        aoFechar={() => setEditando(null)} largura={820}>
        {editando && (
          <FormPro inicial={editando} contratadas={contratadas.dados || []} aoFechar={() => setEditando(null)}
            aoSalvar={() => { setEditando(null); recarregar(); }} />
        )}
      </Modal>
    </section>
  );
}
