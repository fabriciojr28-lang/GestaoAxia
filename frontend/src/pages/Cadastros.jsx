import { useMemo, useState } from "react";
import { api } from "../api";
import { Busca, Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, confirmar, limparVazios, useDados } from "../components/ui";
import { useApp } from "../contexto";

function FormAtivo({ inicial, aoSalvar, aoFechar }) {
  const { opcoes, listas } = useApp();
  const [form, setForm] = useState(inicial);
  const [erro, setErro] = useState("");
  const muda = (c) => (v) => setForm((f) => ({ ...f, [c]: v }));
  async function salvar(e) {
    e.preventDefault();
    try {
      const { id, ...resto } = form;
      const corpo = limparVazios(resto, ["coordenador_id"]);
      if (id) await api(`/ativos/${id}`, { method: "PUT", body: corpo });
      else await api("/ativos", { method: "POST", body: corpo });
      avisar("Ativo salvo.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    }
  }
  return (
    <form onSubmit={salvar} className="grade-form">
      <Campo rotulo="Nome do ativo / obra" largo><input value={form.nome} required onChange={(e) => muda("nome")(e.target.value)} /></Campo>
      <Campo rotulo="Nº do ativo"><input value={form.numero} onChange={(e) => muda("numero")(e.target.value)} /></Campo>
      <Campo rotulo="Tipo de engenharia"><Selecao valor={form.tipo_engenharia} aoMudar={muda("tipo_engenharia")} opcoes={opcoes.tipos_engenharia} vazio="Não informado" /></Campo>
      <Campo rotulo="UF"><Selecao valor={form.uf} aoMudar={muda("uf")} opcoes={opcoes.ufs} vazio="—" /></Campo>
      <Campo rotulo="Município"><input value={form.municipio} onChange={(e) => muda("municipio")(e.target.value)} /></Campo>
      <Campo rotulo="Coordenador técnico" dica="Quem for transferido para esta obra passa para a equipe deste coordenador">
        <Selecao valor={form.coordenador_id} aoMudar={muda("coordenador_id")} opcoes={listas.coordenadores} vazio="Sem coordenador" />
      </Campo>
      <label className="check"><input type="checkbox" checked={form.em_uso} onChange={(e) => muda("em_uso")(e.target.checked)} /> Em uso</label>
      <Erro>{erro}</Erro>
      <div className="acoes campo-largo">
        <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-primario">Salvar</button>
      </div>
    </form>
  );
}

function Mesclar({ origem, aoFechar, aoConcluir }) {
  const { listas } = useApp();
  const [destino, setDestino] = useState("");
  const [erro, setErro] = useState("");
  async function mesclar() {
    const alvo = listas.ativos.find((a) => String(a.id) === destino);
    if (!confirmar(`Tudo que aponta para "${origem.nome}" passará para "${alvo.nome}" e "${origem.nome}" será removido. Confirmar?`)) return;
    try {
      await api(`/ativos/${origem.id}/mesclar/${destino}`, { method: "POST" });
      avisar("Ativos mesclados.");
      aoConcluir();
    } catch (e) {
      setErro(e.message);
    }
  }
  return (
    <div className="form-coluna">
      <p>Use quando o mesmo ativo foi cadastrado com nomes diferentes. Colaboradores, movimentações, fechamentos e registros de PRO de <strong>{origem.nome}</strong> passarão para o ativo escolhido.</p>
      <Campo rotulo="Manter qual ativo?">
        <Busca valor={destino} aoMudar={setDestino} itens={listas.ativos.filter((a) => a.id !== origem.id)} />
      </Campo>
      <Erro>{erro}</Erro>
      <div className="acoes">
        <button className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-perigo" disabled={!destino} onClick={mesclar}>Mesclar</button>
      </div>
    </div>
  );
}

function Ativos() {
  const { opcoes, listas, pode, recarregarListas } = useApp();
  const [busca, setBusca] = useState("");
  const [editando, setEditando] = useState(null);
  const [mesclando, setMesclando] = useState(null);
  const colabs = useDados("/colaboradores");
  const contagem = useMemo(() => {
    const c = {};
    (colabs.dados || []).forEach((x) => x.ativo_atual_id && x.situacao !== "DESMOBILIZADO" && (c[x.ativo_atual_id] = (c[x.ativo_atual_id] || 0) + 1));
    return c;
  }, [colabs.dados]);
  const termo = busca.trim().toUpperCase();
  const itens = listas.ativos.filter((a) => !termo || a.nome.includes(termo) || a.municipio.includes(termo));
  const atualizar = () => { setEditando(null); setMesclando(null); recarregarListas(); colabs.recarregar(); };

  async function excluir(a) {
    if (!confirmar(`Excluir o ativo ${a.nome}?`)) return;
    try {
      await api(`/ativos/${a.id}`, { method: "DELETE" });
      avisar("Ativo excluído.");
      recarregarListas();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  return (
    <>
      <div className="filtros">
        <Campo rotulo="Buscar"><input type="search" value={busca} placeholder="Ativo ou município…" onChange={(e) => setBusca(e.target.value)} /></Campo>
        <div className="espaco" />
        {pode.editar && (
          <button className="botao botao-primario" onClick={() => setEditando({ nome: "", numero: "", tipo_engenharia: "", uf: "", municipio: "", coordenador_id: "", em_uso: true })}>
            + Novo ativo
          </button>
        )}
      </div>
      <div className="tabela-caixa">
        <p className="chip-total">{itens.length} ativo(s)</p>
        <table className="tabela">
          <thead><tr><th>Nº</th><th>Ativo / obra</th><th>Engenharia</th><th>UF</th><th>Município</th><th>Coordenador</th><th>Em campo</th><th aria-label="Ações" /></tr></thead>
          <tbody>
            {itens.map((a) => (
              <tr key={a.id} className={a.em_uso ? "" : "linha-inativa"}>
                <td className="suave">{a.numero}</td>
                <td className="forte">{a.nome}</td>
                <td>{opcoes.tipos_engenharia[a.tipo_engenharia] || ""}</td>
                <td>{a.uf}</td><td>{a.municipio}</td>
                <td>{a.coordenador?.nome || <span className="falta">—</span>}</td>
                <td>{contagem[a.id] || ""}</td>
                <td className="nowrap acoes-linha">
                  {pode.editar && (
                    <button className="botao botao-pequeno" onClick={() => setEditando({ ...a, coordenador_id: a.coordenador_id ? String(a.coordenador_id) : "" })}>Editar</button>
                  )}
                  {pode.admin && <button className="botao botao-pequeno" onClick={() => setMesclando(a)}>Mesclar</button>}
                  {pode.admin && <button className="botao botao-pequeno botao-perigo" onClick={() => excluir(a)}>×</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Modal titulo={editando?.id ? "Editar ativo" : "Novo ativo"} aberto={Boolean(editando)} aoFechar={() => setEditando(null)}>
        {editando && <FormAtivo inicial={editando} aoFechar={() => setEditando(null)} aoSalvar={atualizar} />}
      </Modal>
      <Modal titulo={`Mesclar ${mesclando?.nome || ""}`} aberto={Boolean(mesclando)} aoFechar={() => setMesclando(null)} largura={520}>
        {mesclando && <Mesclar origem={mesclando} aoFechar={() => setMesclando(null)} aoConcluir={atualizar} />}
      </Modal>
    </>
  );
}

/** Lista simples (coordenadores ou contratadas): nome + extras. */
function ListaSimples({ caminho, titulo, extras = [], novo, aoMudar }) {
  const { pode } = useApp();
  const { dados, erro, carregando, recarregar } = useDados(caminho);
  const [editando, setEditando] = useState(null);
  const [erroForm, setErroForm] = useState("");

  async function salvar(e) {
    e.preventDefault();
    try {
      const { id, ...corpo } = editando;
      if (id) await api(`${caminho}/${id}`, { method: "PUT", body: corpo });
      else await api(caminho, { method: "POST", body: corpo });
      avisar("Salvo.");
      setEditando(null);
      recarregar();
      aoMudar?.();
    } catch (err) {
      setErroForm(err.message);
    }
  }
  async function excluir(item) {
    if (!confirmar(`Excluir ${item.nome}?`)) return;
    try {
      await api(`${caminho}/${item.id}`, { method: "DELETE" });
      recarregar();
      aoMudar?.();
    } catch (e) {
      avisar(e.message, "erro");
    }
  }

  if (carregando && !dados) return <Carregando />;
  return (
    <>
      <Erro>{erro}</Erro>
      <div className="filtros">
        <div className="espaco" />
        {pode.editar && <button className="botao botao-primario" onClick={() => { setErroForm(""); setEditando({ ...novo }); }}>+ Adicionar</button>}
      </div>
      {!dados?.length ? <Vazio>Nada cadastrado.</Vazio> : (
        <div className="tabela-caixa">
          <table className="tabela">
            <thead><tr><th>Nome</th>{extras.map((x) => <th key={x.campo}>{x.rotulo}</th>)}<th aria-label="Ações" /></tr></thead>
            <tbody>
              {dados.map((item) => (
                <tr key={item.id}>
                  <td className="forte">{item.nome}</td>
                  {extras.map((x) => <td key={x.campo}>{x.exibir ? x.exibir(item[x.campo]) : item[x.campo]}</td>)}
                  <td className="nowrap acoes-linha">
                    {pode.editar && <button className="botao botao-pequeno" onClick={() => { setErroForm(""); setEditando({ ...item }); }}>Editar</button>}
                    {pode.admin && <button className="botao botao-pequeno botao-perigo" onClick={() => excluir(item)}>×</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal titulo={editando?.id ? `Editar ${titulo}` : `Novo(a) ${titulo}`} aberto={Boolean(editando)} aoFechar={() => setEditando(null)} largura={480}>
        {editando && (
          <form onSubmit={salvar} className="form-coluna">
            <Campo rotulo="Nome"><input value={editando.nome} required onChange={(e) => setEditando({ ...editando, nome: e.target.value })} /></Campo>
            {extras.map((x) => (
              <Campo key={x.campo} rotulo={x.rotulo} dica={x.dica}>
                {x.tipo === "bool" ? (
                  <input type="checkbox" checked={Boolean(editando[x.campo])} onChange={(e) => setEditando({ ...editando, [x.campo]: e.target.checked })} />
                ) : (
                  <input value={editando[x.campo] || ""} onChange={(e) => setEditando({ ...editando, [x.campo]: e.target.value })} />
                )}
              </Campo>
            ))}
            <Erro>{erroForm}</Erro>
            <div className="acoes">
              <button type="button" className="botao" onClick={() => setEditando(null)}>Cancelar</button>
              <button className="botao botao-primario">Salvar</button>
            </div>
          </form>
        )}
      </Modal>
    </>
  );
}

export default function Cadastros() {
  const { recarregarListas } = useApp();
  const [aba, setAba] = useState("ativos");
  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>Ativos e cadastros</h1>
          <p className="subtitulo">Listas usadas em todo o sistema. Nomes repetidos (com ou sem acento) são bloqueados.</p>
        </div>
      </header>
      <div className="abas">
        <button className={aba === "ativos" ? "ativa" : ""} onClick={() => setAba("ativos")}>Ativos / obras</button>
        <button className={aba === "coord" ? "ativa" : ""} onClick={() => setAba("coord")}>Coordenadores técnicos</button>
        <button className={aba === "contr" ? "ativa" : ""} onClick={() => setAba("contr")}>Contratadas</button>
      </div>
      {aba === "ativos" && <Ativos />}
      {aba === "coord" && (
        <ListaSimples caminho="/coordenadores" titulo="coordenador" novo={{ nome: "", apelido: "", em_atividade: true }} aoMudar={recarregarListas}
          extras={[
            { campo: "apelido", rotulo: "Nome curto", dica: "Como aparece nas planilhas antigas" },
            { campo: "em_atividade", rotulo: "Em atividade", tipo: "bool", exibir: (v) => (v ? <Etiqueta tipo="verde">sim</Etiqueta> : <Etiqueta>não</Etiqueta>) },
          ]} />
      )}
      {aba === "contr" && <ListaSimples caminho="/contratadas" titulo="contratada" novo={{ nome: "" }} />}
    </section>
  );
}
