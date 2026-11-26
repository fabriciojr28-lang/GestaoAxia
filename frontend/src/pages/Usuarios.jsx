import { useState } from "react";
import { api } from "../api";
import { Campo, Carregando, Erro, Etiqueta, Modal, Selecao, Vazio, avisar, limparVazios, useDados } from "../components/ui";
import { useApp } from "../contexto";

const COR_PERFIL = { admin: "roxa", editor: "azul", coordenador: "verde", leitura: "neutra" };

function FormUsuario({ inicial, aoSalvar, aoFechar }) {
  const { opcoes, listas } = useApp();
  const [form, setForm] = useState(inicial);
  const [erro, setErro] = useState("");
  const muda = (c) => (v) => setForm((f) => ({ ...f, [c]: v }));

  function aoEscolherCoordenador(id) {
    const coord = listas.coordenadores.find((c) => String(c.id) === id);
    setForm((f) => ({ ...f, coordenador_id: id, nome: f.nome || (coord ? coord.nome : "") }));
  }

  async function salvar(e) {
    e.preventDefault();
    try {
      const { id, ...resto } = form;
      const corpo = limparVazios(resto, ["coordenador_id", "senha"]);
      if (id) await api(`/usuarios/${id}`, { method: "PUT", body: corpo });
      else await api("/usuarios", { method: "POST", body: corpo });
      avisar(id ? "Usuário atualizado." : "Usuário criado. Envie o e-mail e a senha inicial para a pessoa.");
      aoSalvar();
    } catch (err) {
      setErro(err.message);
    }
  }

  return (
    <form onSubmit={salvar} className="form-coluna">
      <Campo rotulo="Perfil de acesso">
        <Selecao valor={form.perfil} aoMudar={muda("perfil")} opcoes={opcoes.perfis} vazio={null} />
      </Campo>
      {form.perfil === "coordenador" && (
        <Campo rotulo="Coordenador técnico" dica="Este login verá e lançará movimentações só da equipe deste coordenador">
          <Selecao valor={form.coordenador_id} aoMudar={aoEscolherCoordenador} opcoes={listas.coordenadores} obrigatorio />
        </Campo>
      )}
      <Campo rotulo="Nome"><input value={form.nome} required minLength={2} onChange={(e) => muda("nome")(e.target.value)} /></Campo>
      <Campo rotulo="E-mail (login)"><input type="email" value={form.email} required onChange={(e) => muda("email")(e.target.value)} /></Campo>
      <Campo rotulo={form.id ? "Nova senha" : "Senha inicial"} dica={form.id ? "Deixe em branco para manter a atual" : "Mínimo de 8 caracteres — a pessoa pode trocar depois"}>
        <input type="text" value={form.senha} minLength={8} required={!form.id} autoComplete="new-password"
          onChange={(e) => muda("senha")(e.target.value)} />
      </Campo>
      <label className="check"><input type="checkbox" checked={form.ativo} onChange={(e) => muda("ativo")(e.target.checked)} /> Acesso liberado</label>
      <Erro>{erro}</Erro>
      <div className="acoes">
        <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
        <button className="botao botao-primario">Salvar</button>
      </div>
    </form>
  );
}

export default function Usuarios() {
  const { opcoes, usuario } = useApp();
  const { dados, erro, carregando, recarregar } = useDados("/usuarios");
  const [editando, setEditando] = useState(null);

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>Usuários e acessos</h1>
          <p className="subtitulo">Cada pessoa entra com o próprio e-mail. Coordenadores acessam só as movimentações da equipe.</p>
        </div>
        <button className="botao botao-primario" onClick={() => setEditando({ email: "", nome: "", perfil: "coordenador", coordenador_id: "", senha: "", ativo: true })}>
          + Novo usuário
        </button>
      </header>
      <Erro>{erro}</Erro>
      {carregando && !dados ? <Carregando /> : !dados?.length ? <Vazio>Nenhum usuário.</Vazio> : (
        <div className="tabela-caixa">
          <table className="tabela">
            <thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Equipe</th><th>Último acesso</th><th>Situação</th><th aria-label="Ações" /></tr></thead>
            <tbody>
              {dados.map((u) => (
                <tr key={u.id}>
                  <td className="forte">{u.nome}{u.id === usuario.id && <span className="suave"> (você)</span>}</td>
                  <td>{u.email}</td>
                  <td><Etiqueta tipo={COR_PERFIL[u.perfil]}>{opcoes.perfis[u.perfil]?.split(" (")[0]}</Etiqueta></td>
                  <td>{u.coordenador?.nome || ""}</td>
                  <td className="suave">{u.ultimo_acesso ? new Date(u.ultimo_acesso).toLocaleString("pt-BR") : "nunca entrou"}</td>
                  <td>{u.ativo ? <Etiqueta tipo="verde">liberado</Etiqueta> : <Etiqueta tipo="vermelha">bloqueado</Etiqueta>}</td>
                  <td className="acoes-linha">
                    <button className="botao botao-pequeno" onClick={() => setEditando({ ...u, coordenador_id: u.coordenador_id ? String(u.coordenador_id) : "", senha: "" })}>Editar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal titulo={editando?.id ? `Editar ${editando.nome}` : "Novo usuário"} aberto={Boolean(editando)} aoFechar={() => setEditando(null)} largura={520}>
        {editando && <FormUsuario inicial={editando} aoFechar={() => setEditando(null)} aoSalvar={() => { setEditando(null); recarregar(); }} />}
      </Modal>
    </section>
  );
}
