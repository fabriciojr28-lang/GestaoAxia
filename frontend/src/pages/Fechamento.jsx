import { useMemo, useState } from "react";
import { api, baixar } from "../api";
import { Busca, Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, confirmar, limparVazios, useDados } from "../components/ui";
import { useApp } from "../contexto";
import { dataBR, mesAtualISO, mesBR } from "../util";

const COR = { MOBILIZADO_OBRA: "verde", FOLGA: "amarela", FERIAS: "amarela", AFASTADO: "laranja", TRANSFERIDO: "azul", DESMOBILIZADO: "vermelha", PENDENTE: "neutra" };

function FormLinha({ linha, aoSalvar, aoFechar }) {
  const { opcoes, listas } = useApp();
  const [form, setForm] = useState({
    ativo_id: linha.ativo_id ? String(linha.ativo_id) : "", coordenador_id: linha.coordenador_id ? String(linha.coordenador_id) : "",
    status: linha.status, inicio: linha.inicio || "", fim: linha.fim || "", veiculo: linha.veiculo, hospedagem: linha.hospedagem,
    dias_folga: linha.dias_folga, dias_ferias: linha.dias_ferias, dias_afastado: linha.dias_afastado, observacao: linha.observacao,
  });
  const [erro, setErro] = useState("");
  const muda = (c) => (v) => setForm((f) => ({ ...f, [c]: v }));

  async function salvar(e) {
    e.preventDefault();
    try {
      const corpo = limparVazios(form, ["ativo_id", "coordenador_id", "inicio", "fim"]);
      ["dias_folga", "dias_ferias", "dias_afastado"].forEach((k) => (corpo[k] = Number(corpo[k] || 0)));
      await api(`/fechamento/${linha.id}`, { method: "PUT", body: corpo });
      avisar("Linha do fechamento salva.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    }
  }

  return (
    <form onSubmit={salvar} className="grade-form">
      <Campo rotulo="Ativo / obra" largo><Busca valor={form.ativo_id} aoMudar={muda("ativo_id")} itens={listas.ativos} /></Campo>
      <Campo rotulo="Coordenador técnico">
        <Selecao valor={form.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores} vazio="Sem coordenador" />
      </Campo>
      <Campo rotulo="Status"><Selecao valor={form.status} aoMudar={muda("status")} opcoes={opcoes.status_fechamento} vazio={null} /></Campo>
      <Campo rotulo="Início"><input type="date" value={form.inicio} onChange={(e) => muda("inicio")(e.target.value)} /></Campo>
      <Campo rotulo="Fim"><input type="date" value={form.fim} min={form.inicio || undefined} onChange={(e) => muda("fim")(e.target.value)} /></Campo>
      <Campo rotulo="Tipo de veículo"><Selecao valor={form.veiculo} aoMudar={muda("veiculo")} opcoes={opcoes.veiculos} vazio="Não definido" /></Campo>
      <Campo rotulo="Hospedagem"><Selecao valor={form.hospedagem} aoMudar={muda("hospedagem")} opcoes={opcoes.hospedagens} vazio="Não definida" /></Campo>
      <Campo rotulo="Dias de folga"><input type="number" min={0} max={31} value={form.dias_folga} onChange={(e) => muda("dias_folga")(e.target.value)} /></Campo>
      <Campo rotulo="Dias de férias"><input type="number" min={0} max={31} value={form.dias_ferias} onChange={(e) => muda("dias_ferias")(e.target.value)} /></Campo>
      <Campo rotulo="Dias afastado"><input type="number" min={0} max={31} value={form.dias_afastado} onChange={(e) => muda("dias_afastado")(e.target.value)} /></Campo>
      <Campo rotulo="Observação" largo><textarea rows={3} value={form.observacao} onChange={(e) => muda("observacao")(e.target.value)} /></Campo>
      <Erro>{erro}</Erro>
      <div className="acoes campo-largo">
        <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-primario">Salvar</button>
      </div>
    </form>
  );
}

export default function Fechamento() {
  const { opcoes, pode } = useApp();
  const [mes, setMes] = useState(mesAtualISO());
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState(null);
  const { dados, erro, carregando, recarregar } = useDados("/fechamento", { mes });
  const bloqueado = dados?.fechado && !pode.admin;

  const linhas = useMemo(() => {
    const termo = busca.trim().toUpperCase();
    return (dados?.linhas || []).filter((l) => !termo || l.colaborador.nome.includes(termo) || (l.ativo?.nome || "").includes(termo));
  }, [dados, busca]);

  async function acao(fn, msg) {
    try {
      const r = await fn();
      avisar(typeof msg === "function" ? msg(r) : msg);
      recarregar();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  const gerar = () => acao(() => api("/fechamento/gerar", { method: "POST", params: { mes } }),
    (r) => `Fechamento atualizado: ${r.criadas} linha(s) nova(s), ${r.atualizadas} recalculada(s).`);
  const fechar = () => confirmar(`Fechar ${mesBR(mes)}? Depois disso, só administradores poderão alterar lançamentos deste mês.`)
    && acao(() => api("/fechamento/fechar", { method: "POST", params: { mes } }), "Mês fechado.");
  const reabrir = () => acao(() => api("/fechamento/reabrir", { method: "POST", params: { mes } }), "Mês reaberto.");
  const remover = (l) => confirmar(`Remover ${l.colaborador.nome} do fechamento de ${mesBR(mes)}?`)
    && acao(() => api(`/fechamento/${l.id}`, { method: "DELETE" }), "Linha removida.");
  const exportar = () => baixar("/fechamento/exportar", { mes }, `fechamento_${mes.slice(0, 7)}.xlsx`).catch((e) => avisar(e.message, "erro"));

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>Fechamento mensal {dados?.fechado && <Etiqueta tipo="neutra">fechado</Etiqueta>}</h1>
          <p className="subtitulo">
            Uma linha por profissional no mês, com veículo, hospedagem e dias de folga/férias calculados das movimentações.
          </p>
        </div>
        <div className="linha">
          <button className="botao" onClick={exportar} disabled={!dados?.linhas?.length}>⬇ Exportar Excel</button>
          {pode.editar && !bloqueado && <button className="botao botao-primario" onClick={gerar}>↻ Gerar / atualizar do mês</button>}
          {pode.admin && (dados?.fechado
            ? <button className="botao" onClick={reabrir}>Reabrir mês</button>
            : <button className="botao" onClick={fechar} disabled={!dados?.linhas?.length}>🔒 Fechar mês</button>)}
        </div>
      </header>

      <div className="filtros">
        <Campo rotulo="Mês">
          <input type="month" value={mes.slice(0, 7)} onChange={(e) => e.target.value && setMes(`${e.target.value}-01`)} />
        </Campo>
        <Campo rotulo="Buscar">
          <input type="search" placeholder="Profissional ou ativo…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </Campo>
      </div>

      <Erro>{erro}</Erro>
      {carregando && !dados ? <Carregando /> : !dados?.linhas?.length ? (
        <Vazio>
          Ainda não há fechamento para {mesBR(mes)}.
          {pode.editar && <> Clique em <strong>Gerar / atualizar do mês</strong> para montar a partir do efetivo e das movimentações.</>}
        </Vazio>
      ) : (
        <div className="tabela-caixa">
          <p className="chip-total">{linhas.length} profissional(is)</p>
          <table className="tabela">
            <thead>
              <tr>
                <th>Nº</th><th>Ativo</th><th>UF</th><th>Município</th><th>Coord.</th><th>Profissional</th><th>Status</th>
                <th>Início</th><th>Fim</th><th>Veículo</th><th>Hosp.</th><th title="Dias de folga / férias / afastado">Folga/Fér./Af.</th>
                <th>Observação</th>{pode.editar && !bloqueado && <th aria-label="Ações" />}
              </tr>
            </thead>
            <tbody>
              {linhas.map((l) => (
                <tr key={l.id}>
                  <td className="suave">{l.ativo_numero}</td>
                  <td>{l.ativo?.nome || "—"}</td><td>{l.uf}</td><td>{l.municipio}</td>
                  <td className="suave">{l.coordenador?.nome?.split(" ")[0] || "—"}</td>
                  <td className="forte">{l.colaborador.nome}</td>
                  <td><Etiqueta tipo={COR[l.status]}>{opcoes.status_fechamento[l.status]}</Etiqueta></td>
                  <td className="nowrap">{dataBR(l.inicio)}</td><td className="nowrap">{dataBR(l.fim)}</td>
                  <td title={opcoes.veiculos[l.veiculo]}>{l.veiculo || <span className="falta">—</span>}</td>
                  <td title={opcoes.hospedagens[l.hospedagem]}>{l.hospedagem || <span className="falta">—</span>}</td>
                  <td className="nowrap">{l.dias_folga} / {l.dias_ferias} / {l.dias_afastado}</td>
                  <td className="obs">{l.observacao}</td>
                  {pode.editar && !bloqueado && (
                    <td className="nowrap acoes-linha">
                      <button className="botao botao-pequeno" onClick={() => setEditando(l)}>Editar</button>
                      <button className="botao botao-pequeno botao-perigo" onClick={() => remover(l)}>×</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal titulo={editando ? `${editando.colaborador.nome} · ${mesBR(mes)}` : ""} aberto={Boolean(editando)}
        aoFechar={() => setEditando(null)} largura={760}>
        {editando && <FormLinha linha={editando} aoFechar={() => setEditando(null)} aoSalvar={() => { setEditando(null); recarregar(); }} />}
      </Modal>
    </section>
  );
}
