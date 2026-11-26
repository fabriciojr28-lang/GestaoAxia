import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import {
  Busca, Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, confirmar, limparVazios, useDados,
} from "../components/ui";
import { useApp } from "../contexto";
import { dataBR } from "../util";

const COR_SITUACAO = { MOBILIZADO: "verde", FOLGA: "amarela", FERIAS: "amarela", AFASTADO: "laranja", DESMOBILIZADO: "vermelha" };

const VAZIO = {
  nome: "", cpf: "", matricula: "", funcao: "TÉCNICO DE SEGURANÇA DO TRABALHO", tipo_engenharia: "",
  coordenador_id: "", ativo_atual_id: "", situacao: "MOBILIZADO", data_admissao: "", data_demissao: "",
  uf_origem: "", cidade_origem: "", telefone_corporativo: "", telefone_pessoal: "", email_corporativo: "",
  email_pessoal: "", veiculo: "", hospedagem: "",
};

const CAMPOS_NULOS = ["coordenador_id", "ativo_atual_id", "data_admissao", "data_demissao"];

function paraForm(c) {
  const f = { ...VAZIO };
  Object.keys(VAZIO).forEach((k) => (f[k] = c[k] ?? ""));
  f.coordenador_id = c.coordenador_id ? String(c.coordenador_id) : "";
  f.ativo_atual_id = c.ativo_atual_id ? String(c.ativo_atual_id) : "";
  return { ...f, id: c.id };
}

function Historico({ colaboradorId }) {
  const { opcoes } = useApp();
  const { dados } = useDados(`/colaboradores/${colaboradorId}/movimentacoes`);
  if (!dados) return <Carregando />;
  if (!dados.length) return <p className="suave">Nenhuma movimentação registrada.</p>;
  return (
    <table className="tabela tabela-compacta">
      <thead><tr><th>Movimentação</th><th>Ativo</th><th>Início</th><th>Fim</th><th>Obs.</th></tr></thead>
      <tbody>
        {dados.map((m) => (
          <tr key={m.id}>
            <td>{opcoes.tipos_movimentacao[m.tipo]}</td><td>{m.ativo?.nome || "—"}</td>
            <td className="nowrap">{dataBR(m.data_inicio)}</td><td className="nowrap">{dataBR(m.data_fim) || "—"}</td>
            <td className="obs">{m.observacoes}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FormColaborador({ inicial, aoSalvar, aoFechar, somenteLeitura }) {
  const { opcoes, listas } = useApp();
  const [form, setForm] = useState(inicial);
  const [erro, setErro] = useState("");
  const [aba, setAba] = useState("dados");
  const muda = (campo) => (v) => setForm((f) => ({ ...f, [campo]: v }));
  const texto = (campo, props = {}) => (
    <input value={form[campo] || ""} onChange={(e) => muda(campo)(e.target.value)} disabled={somenteLeitura} {...props} />
  );

  async function salvar(e) {
    e.preventDefault();
    try {
      const { id, ...resto } = form;
      const corpo = limparVazios(resto, CAMPOS_NULOS);
      if (id) await api(`/colaboradores/${id}`, { method: "PUT", body: corpo });
      else await api("/colaboradores", { method: "POST", body: corpo });
      avisar("Colaborador salvo.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    }
  }

  return (
    <>
      {form.id && (
        <div className="abas">
          <button className={aba === "dados" ? "ativa" : ""} onClick={() => setAba("dados")}>Dados</button>
          <button className={aba === "hist" ? "ativa" : ""} onClick={() => setAba("hist")}>Histórico de movimentações</button>
        </div>
      )}
      {aba === "hist" ? <Historico colaboradorId={form.id} /> : (
        <form onSubmit={salvar} className="grade-form">
          <Campo rotulo="Nome completo" largo>{texto("nome", { required: true, minLength: 3 })}</Campo>
          <Campo rotulo="CPF">{texto("cpf", { placeholder: "000.000.000-00" })}</Campo>
          <Campo rotulo="Matrícula">{texto("matricula")}</Campo>
          <Campo rotulo="Função">{texto("funcao")}</Campo>
          <Campo rotulo="Tipo de engenharia">
            <Selecao valor={form.tipo_engenharia} aoMudar={muda("tipo_engenharia")} opcoes={opcoes.tipos_engenharia}
              vazio="Não informado" desabilitado={somenteLeitura} />
          </Campo>
          <Campo rotulo="Coordenador técnico">
            <Selecao valor={form.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores}
              vazio="Sem coordenador" desabilitado={somenteLeitura} />
          </Campo>
          <Campo rotulo="Ativo / obra atual" dica="Muda sozinho quando há mobilização ou transferência">
            {somenteLeitura ? texto("_ativo", { value: listas.ativos.find((a) => String(a.id) === form.ativo_atual_id)?.nome || "" })
              : <Busca valor={form.ativo_atual_id} aoMudar={muda("ativo_atual_id")} itens={listas.ativos} />}
          </Campo>
          <Campo rotulo="Situação">
            <Selecao valor={form.situacao} aoMudar={muda("situacao")} opcoes={opcoes.situacoes_colaborador} vazio={null}
              desabilitado={somenteLeitura} />
          </Campo>
          <Campo rotulo="Admissão">{texto("data_admissao", { type: "date" })}</Campo>
          <Campo rotulo="Demissão">{texto("data_demissao", { type: "date" })}</Campo>
          <Campo rotulo="Tipo de veículo">
            <Selecao valor={form.veiculo} aoMudar={muda("veiculo")} opcoes={opcoes.veiculos} vazio="Não definido"
              desabilitado={somenteLeitura} />
          </Campo>
          <Campo rotulo="Hospedagem">
            <Selecao valor={form.hospedagem} aoMudar={muda("hospedagem")} opcoes={opcoes.hospedagens} vazio="Não definida"
              desabilitado={somenteLeitura} />
          </Campo>
          <Campo rotulo="Estado de origem">{texto("uf_origem")}</Campo>
          <Campo rotulo="Cidade de origem / residência">{texto("cidade_origem")}</Campo>
          <Campo rotulo="Telefone corporativo">{texto("telefone_corporativo")}</Campo>
          <Campo rotulo="Telefone pessoal">{texto("telefone_pessoal")}</Campo>
          <Campo rotulo="E-mail corporativo">{texto("email_corporativo", { type: "email" })}</Campo>
          <Campo rotulo="E-mail pessoal">{texto("email_pessoal", { type: "email" })}</Campo>
          <Erro>{erro}</Erro>
          <div className="acoes campo-largo">
            <button type="button" className="botao" onClick={aoFechar}>{somenteLeitura ? "Fechar" : "Cancelar"}</button>
            {!somenteLeitura && <button className="botao botao-primario">Salvar</button>}
          </div>
        </form>
      )}
    </>
  );
}

export default function Colaboradores() {
  const { opcoes, listas, pode, recarregarListas } = useApp();
  const [params] = useSearchParams();
  const [filtros, setFiltros] = useState({
    q: "", situacao: "", coordenador_id: "", tipo_engenharia: "", pendentes: params.get("pendentes") === "1",
  });
  const [editando, setEditando] = useState(null);
  const { dados, erro, carregando, recarregar } = useDados("/colaboradores", filtros);
  const muda = (campo) => (v) => setFiltros((f) => ({ ...f, [campo]: v }));

  async function excluir(c) {
    if (!confirmar(`Excluir ${c.nome}? Só é possível se não houver movimentações. Para quem saiu, prefira "Desmobilizado".`)) return;
    try {
      await api(`/colaboradores/${c.id}`, { method: "DELETE" });
      avisar("Colaborador excluído.");
      recarregar();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>{pode.coordenador ? "Minha equipe" : "Colaboradores"}</h1>
          <p className="subtitulo">Cadastro único do efetivo SST — substitui a planilha EFETIVO.</p>
        </div>
        {pode.editar && (
          <button className="botao botao-primario" onClick={() => setEditando({ ...VAZIO })}>+ Novo colaborador</button>
        )}
      </header>

      <div className="filtros">
        <Campo rotulo="Buscar">
          <input type="search" placeholder="Nome, CPF ou matrícula…" value={filtros.q} onChange={(e) => muda("q")(e.target.value)} />
        </Campo>
        <Campo rotulo="Situação">
          <Selecao valor={filtros.situacao} aoMudar={muda("situacao")} opcoes={opcoes.situacoes_colaborador} vazio="Todas" />
        </Campo>
        {!pode.coordenador && (
          <>
            <Campo rotulo="Coordenador">
              <Selecao valor={filtros.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores} vazio="Todos" />
            </Campo>
            <Campo rotulo="Engenharia">
              <Selecao valor={filtros.tipo_engenharia} aoMudar={muda("tipo_engenharia")} opcoes={opcoes.tipos_engenharia} vazio="Todas" />
            </Campo>
          </>
        )}
        <label className="check">
          <input type="checkbox" checked={filtros.pendentes} onChange={(e) => muda("pendentes")(e.target.checked)} />
          Só cadastros incompletos
        </label>
      </div>

      <Erro>{erro}</Erro>
      {carregando && !dados ? <Carregando /> : !dados?.length ? <Vazio>Nenhum colaborador encontrado.</Vazio> : (
        <div className="tabela-caixa">
          <p className="chip-total">{dados.length} colaborador(es)</p>
          <table className="tabela">
            <thead>
              <tr>
                <th>Nome</th><th>Situação</th><th>Ativo / obra</th><th>Coordenador</th><th>Função</th>
                <th>Matrícula</th><th>Veículo</th><th>Hosp.</th><th>Pendências</th><th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {dados.map((c) => (
                <tr key={c.id}>
                  <td className="forte">{c.nome}</td>
                  <td><Etiqueta tipo={COR_SITUACAO[c.situacao]}>{opcoes.situacoes_colaborador[c.situacao]}</Etiqueta></td>
                  <td>{c.ativo_atual?.nome || "—"}</td>
                  <td>{c.coordenador?.nome || "—"}</td>
                  <td className="suave">{c.funcao}</td>
                  <td>{c.matricula}</td>
                  <td>{c.veiculo}</td>
                  <td>{c.hospedagem}</td>
                  <td>{c.pendencias_cadastro.length ? <Etiqueta tipo="laranja" titulo={`Falta: ${c.pendencias_cadastro.join(", ")}`}>falta {c.pendencias_cadastro.join(", ")}</Etiqueta> : ""}</td>
                  <td className="nowrap acoes-linha">
                    <button className="botao botao-pequeno" onClick={() => setEditando(paraForm(c))}>
                      {pode.editar ? "Editar" : "Ver"}
                    </button>
                    {pode.admin && <button className="botao botao-pequeno botao-perigo" onClick={() => excluir(c)}>Excluir</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal titulo={editando?.id ? editando.nome : "Novo colaborador"} aberto={Boolean(editando)}
        aoFechar={() => setEditando(null)} largura={860}>
        {editando && (
          <FormColaborador inicial={editando} somenteLeitura={!pode.editar} aoFechar={() => setEditando(null)}
            aoSalvar={() => { setEditando(null); recarregar(); recarregarListas(); }} />
        )}
      </Modal>
    </section>
  );
}
