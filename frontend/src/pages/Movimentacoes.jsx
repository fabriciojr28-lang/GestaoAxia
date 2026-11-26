import { useMemo, useState } from "react";
import { api } from "../api";
import {
  Busca, Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, confirmar, limparVazios, useDados,
} from "../components/ui";
import { useApp } from "../contexto";
import { dataBR, hojeISO, mesAtualISO, mesBR } from "../util";

const COR_TIPO = {
  MOBILIZADO: "verde", MOBILIZADO_OBRA: "verde", RETORNO_FOLGA: "verde", TRANSFERIDO: "azul",
  FOLGA: "amarela", FERIAS: "amarela", AFASTADO: "laranja", DESMOBILIZADO: "vermelha", PENDENTE: "neutra",
};

const VAZIO = {
  colaborador_id: "", tipo: "", ativo_id: "", coordenador_id: "", data_inicio: hojeISO(), data_fim: "",
  observacoes: "",
};

function FormMovimentacao({ inicial, colaboradores, aoSalvar, aoFechar }) {
  const { opcoes, listas, pode } = useApp();
  const [form, setForm] = useState(inicial);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const muda = (campo) => (v) => setForm((f) => ({ ...f, [campo]: v }));

  const comPeriodo = opcoes.tipos_com_periodo.includes(form.tipo);
  const comDestino = opcoes.tipos_com_destino.includes(form.tipo);
  const colab = colaboradores.find((c) => String(c.id) === String(form.colaborador_id));
  const ativo = listas.ativos.find((a) => String(a.id) === String(form.ativo_id));

  async function salvar(e) {
    e.preventDefault();
    setSalvando(true);
    setErro("");
    try {
      const { colaborador: _ignorado, ...resto } = form;
      const corpo = limparVazios(resto, ["colaborador_id", "ativo_id", "coordenador_id", "data_fim"]);
      if (form.id) await api(`/movimentacoes/${form.id}`, { method: "PUT", body: corpo });
      else await api("/movimentacoes", { method: "POST", body: corpo });
      avisar(form.id ? "Movimentação atualizada." : "Movimentação lançada.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={salvar} className="grade-form">
      <Campo rotulo="Colaborador" largo>
        <Busca valor={form.colaborador_id} aoMudar={muda("colaborador_id")} itens={colaboradores} obrigatorio
          placeholder="Digite o nome do colaborador…" />
      </Campo>
      {colab && (
        <div className="info-linha campo-largo">
          Hoje: <strong>{opcoes.situacoes_colaborador[colab.situacao]}</strong>
          {colab.ativo_atual && <> em <strong>{colab.ativo_atual.nome}</strong></>}
          {colab.coordenador && <> · coord. {colab.coordenador.nome}</>}
        </div>
      )}
      <Campo rotulo="Situação / movimentação">
        <Selecao valor={form.tipo} aoMudar={muda("tipo")} opcoes={opcoes.tipos_movimentacao} obrigatorio />
      </Campo>
      <Campo rotulo={comDestino ? "Ativo / obra de destino" : "Ativo / obra"}
        dica={ativo ? [ativo.uf, ativo.municipio].filter(Boolean).join(" · ") : comDestino ? "Obrigatório" : "Opcional"}>
        <Busca valor={form.ativo_id} aoMudar={muda("ativo_id")} itens={listas.ativos} obrigatorio={comDestino}
          placeholder="Digite o ativo…" />
      </Campo>
      <Campo rotulo="Data início">
        <input type="date" value={form.data_inicio} required onChange={(e) => muda("data_inicio")(e.target.value)} />
      </Campo>
      <Campo rotulo="Data fim" dica={comPeriodo ? "Obrigatória para folga, férias e afastamento" : "Opcional"}>
        <input type="date" value={form.data_fim || ""} min={form.data_inicio} required={comPeriodo}
          onChange={(e) => muda("data_fim")(e.target.value)} />
      </Campo>
      {!pode.coordenador && (
        <Campo rotulo="Coordenador responsável" dica="Se vazio, usa o coordenador do colaborador">
          <Selecao valor={form.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores}
            vazio="Automático" />
        </Campo>
      )}
      <Campo rotulo="Observações" largo>
        <textarea rows={3} value={form.observacoes} onChange={(e) => muda("observacoes")(e.target.value)} />
      </Campo>
      <Erro>{erro}</Erro>
      <div className="acoes campo-largo">
        <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-primario" disabled={salvando}>{salvando ? "Salvando…" : "Salvar"}</button>
      </div>
    </form>
  );
}

export default function Movimentacoes() {
  const { opcoes, listas, pode } = useApp();
  const [mes, setMes] = useState(mesAtualISO());
  const [tipo, setTipo] = useState("");
  const [coord, setCoord] = useState("");
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState(null);

  const filtros = { mes, tipo, coordenador_id: coord, q: busca };
  const { dados, erro, carregando, recarregar } = useDados("/movimentacoes", filtros);
  const colabs = useDados("/colaboradores");

  const resumo = useMemo(() => {
    const cont = {};
    (dados || []).forEach((m) => (cont[m.tipo] = (cont[m.tipo] || 0) + 1));
    return cont;
  }, [dados]);

  async function excluir(mov) {
    if (!confirmar(`Excluir a movimentação de ${mov.colaborador.nome} (${opcoes.tipos_movimentacao[mov.tipo]})?`)) return;
    try {
      await api(`/movimentacoes/${mov.id}`, { method: "DELETE" });
      avisar("Movimentação excluída.");
      recarregar();
      colabs.recarregar();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  const abrirNova = () => setEditando({ ...VAZIO, data_inicio: hojeISO() });
  const abrirEdicao = (m) =>
    setEditando({
      id: m.id, colaborador: m.colaborador, colaborador_id: String(m.colaborador_id), tipo: m.tipo, ativo_id: m.ativo_id ? String(m.ativo_id) : "",
      coordenador_id: m.coordenador_id ? String(m.coordenador_id) : "", data_inicio: m.data_inicio,
      data_fim: m.data_fim || "", observacoes: m.observacoes,
    });

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>{pode.coordenador ? "Movimentações da minha equipe" : "Movimentações"}</h1>
          <p className="subtitulo">
            Mobilizações, transferências, folgas, férias e afastamentos.
            {pode.coordenador && " Você vê e lança apenas para os colaboradores da sua equipe."}
          </p>
        </div>
        {pode.lancar && (
          <button className="botao botao-primario" onClick={abrirNova}>+ Nova movimentação</button>
        )}
      </header>

      <div className="filtros">
        <Campo rotulo="Mês">
          <div className="linha">
            <input type="month" value={mes ? mes.slice(0, 7) : ""}
              onChange={(e) => setMes(e.target.value ? `${e.target.value}-01` : "")} />
            <button className="botao botao-pequeno" onClick={() => setMes("")} disabled={!mes}>Todos</button>
          </div>
        </Campo>
        <Campo rotulo="Tipo">
          <Selecao valor={tipo} aoMudar={setTipo} opcoes={opcoes.tipos_movimentacao} vazio="Todos" />
        </Campo>
        {!pode.coordenador && (
          <Campo rotulo="Coordenador">
            <Selecao valor={coord} aoMudar={setCoord} opcoes={listas.coordenadores} vazio="Todos" />
          </Campo>
        )}
        <Campo rotulo="Colaborador">
          <input type="search" placeholder="Buscar por nome…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </Campo>
      </div>

      {dados && dados.length > 0 && (
        <div className="chips">
          <span className="chip-total">{dados.length} lançamento(s){mes && ` em ${mesBR(mes)}`}</span>
          {Object.entries(resumo).map(([k, v]) => (
            <Etiqueta key={k} tipo={COR_TIPO[k]}>{opcoes.tipos_movimentacao[k]}: {v}</Etiqueta>
          ))}
        </div>
      )}

      <Erro>{erro}</Erro>
      {carregando && !dados ? (
        <Carregando />
      ) : !dados?.length ? (
        <Vazio>Nenhuma movimentação encontrada com esses filtros.</Vazio>
      ) : (
        <div className="tabela-caixa">
          <table className="tabela">
            <thead>
              <tr>
                <th>Colaborador</th>
                <th>Movimentação</th>
                <th>Ativo / obra</th>
                <th>Início</th>
                <th>Fim</th>
                <th>Coordenador</th>
                <th>Observações</th>
                <th>Lançado por</th>
                {pode.lancar && <th aria-label="Ações" />}
              </tr>
            </thead>
            <tbody>
              {dados.map((m) => (
                <tr key={m.id}>
                  <td className="forte">{m.colaborador.nome}</td>
                  <td><Etiqueta tipo={COR_TIPO[m.tipo]}>{opcoes.tipos_movimentacao[m.tipo]}</Etiqueta></td>
                  <td>{m.ativo?.nome || "—"}</td>
                  <td className="nowrap">{dataBR(m.data_inicio)}</td>
                  <td className="nowrap">{dataBR(m.data_fim) || "—"}</td>
                  <td>{m.coordenador?.nome || "—"}</td>
                  <td className="obs">{m.observacoes}</td>
                  <td className="suave">{m.criado_por_nome || "importação"}</td>
                  {pode.lancar && (
                    <td className="nowrap acoes-linha">
                      <button className="botao botao-pequeno" onClick={() => abrirEdicao(m)}>Editar</button>
                      <button className="botao botao-pequeno botao-perigo" onClick={() => excluir(m)}>Excluir</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal titulo={editando?.id ? "Editar movimentação" : "Nova movimentação"} aberto={Boolean(editando)}
        aoFechar={() => setEditando(null)} largura={720}>
        {editando && (
          <FormMovimentacao
            inicial={editando}
            colaboradores={
              // a pessoa pode ter saído da equipe por causa deste lançamento: mantém o nome disponível na edição
              editando.colaborador && !(colabs.dados || []).some((c) => c.id === editando.colaborador.id)
                ? [...(colabs.dados || []), editando.colaborador]
                : colabs.dados || []
            }
            aoFechar={() => setEditando(null)}
            aoSalvar={() => {
              setEditando(null);
              recarregar();
              colabs.recarregar();
            }}
          />
        )}
      </Modal>
    </section>
  );
}
