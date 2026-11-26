import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { useApp } from "../contexto";
import Icone from "./Icone";
import { Campo, Modal, avisar } from "./ui";

function TrocarSenha({ aberto, aoFechar }) {
  const [form, setForm] = useState({ senha_atual: "", senha_nova: "", confirmar: "" });
  const [erro, setErro] = useState("");
  async function enviar(e) {
    e.preventDefault();
    if (form.senha_nova !== form.confirmar) return setErro("A confirmação não confere com a nova senha.");
    try {
      await api("/auth/senha", { method: "POST", body: { senha_atual: form.senha_atual, senha_nova: form.senha_nova } });
      avisar("Senha alterada. Use a nova senha no próximo acesso.");
      setForm({ senha_atual: "", senha_nova: "", confirmar: "" });
      setErro("");
      aoFechar();
    } catch (err) {
      setErro(err.message);
    }
  }
  return (
    <Modal titulo="Trocar minha senha" aberto={aberto} aoFechar={aoFechar} largura={420}>
      <form onSubmit={enviar} className="form-coluna">
        <Campo rotulo="Senha atual">
          <input type="password" value={form.senha_atual} required autoComplete="current-password"
            onChange={(e) => setForm({ ...form, senha_atual: e.target.value })} />
        </Campo>
        <Campo rotulo="Nova senha" dica="Mínimo de 8 caracteres">
          <input type="password" value={form.senha_nova} required minLength={8} autoComplete="new-password"
            onChange={(e) => setForm({ ...form, senha_nova: e.target.value })} />
        </Campo>
        <Campo rotulo="Confirmar nova senha">
          <input type="password" value={form.confirmar} required minLength={8} autoComplete="new-password"
            onChange={(e) => setForm({ ...form, confirmar: e.target.value })} />
        </Campo>
        {erro && <div className="erro-bloco">{erro}</div>}
        <div className="acoes">
          <button type="button" className="botao" onClick={aoFechar}>Cancelar</button>
          <button className="botao botao-primario">Salvar nova senha</button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * Tabelas sem rolagem lateral: cada célula recebe o nome da coluna (data-rotulo) para que,
 * quando não couber na largura, a linha vire um cartão com "rótulo: valor" quebrando para baixo.
 */
const LARGURA_MINIMA_COLUNA = 95; // px por coluna para a tabela ficar confortável

function useTabelasResponsivas(ref) {
  useEffect(() => {
    const raiz = ref.current;
    if (!raiz) return undefined;
    let agendado = 0;
    const ajustar = () => {
      agendado = 0;
      raiz.querySelectorAll("table.tabela").forEach((tabela) => {
        const titulos = [...tabela.querySelectorAll("thead th")].map((th) => th.textContent.trim());
        tabela.querySelectorAll("tbody tr").forEach((tr) => {
          [...tr.children].forEach((td, i) => {
            if (td.dataset.rotulo !== (titulos[i] || "")) td.dataset.rotulo = titulos[i] || "";
          });
        });
        const caixa = tabela.parentElement;
        tabela.classList.remove("tabela-cartoes");
        const disponivel = caixa.clientWidth;
        const estoura = tabela.scrollWidth > disponivel + 1;
        const apertada = disponivel < titulos.length * LARGURA_MINIMA_COLUNA || disponivel < 600;
        tabela.classList.toggle("tabela-cartoes", estoura || apertada);
      });
    };
    const agendar = () => {
      if (!agendado) agendado = requestAnimationFrame(ajustar);
    };
    ajustar();
    const mutacoes = new MutationObserver(agendar);
    mutacoes.observe(raiz, { childList: true, subtree: true });
    const tamanho = new ResizeObserver(agendar);
    tamanho.observe(raiz);
    return () => {
      mutacoes.disconnect();
      tamanho.disconnect();
      cancelAnimationFrame(agendado);
    };
  }, [ref]);
}

const iniciais = (nome = "") => nome.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();

export default function Layout() {
  const { usuario, opcoes, sair, pode } = useApp();
  const [senhaAberta, setSenhaAberta] = useState(false);
  const [menuAberto, setMenuAberto] = useState(false);
  const conteudo = useRef(null);
  const local = useLocation();
  useTabelasResponsivas(conteudo);
  useEffect(() => setMenuAberto(false), [local.pathname]);

  const secoes = pode.coordenador
    ? [{ titulo: "Minha área", itens: [
        { para: "/movimentacoes", rotulo: "Movimentações", icone: "movimentacoes" },
        { para: "/colaboradores", rotulo: "Minha equipe", icone: "colaboradores" },
      ] }]
    : [
        { titulo: "Visão geral", itens: [{ para: "/", rotulo: "Painel", icone: "painel", fim: true }] },
        { titulo: "Operação", itens: [
          { para: "/movimentacoes", rotulo: "Movimentações", icone: "movimentacoes" },
          { para: "/fechamento", rotulo: "Fechamento mensal", icone: "fechamento" },
          { para: "/pro", rotulo: "Evidências PRO", icone: "pro" },
        ] },
        { titulo: "Cadastros", itens: [
          { para: "/colaboradores", rotulo: "Colaboradores", icone: "colaboradores" },
          { para: "/cadastros", rotulo: "Ativos e listas", icone: "cadastros" },
          ...(pode.admin ? [{ para: "/usuarios", rotulo: "Usuários e acessos", icone: "usuarios" }] : []),
        ] },
      ];

  const perfil = usuario.coordenador ? usuario.coordenador.nome : opcoes?.perfis?.[usuario.perfil]?.split(" (")[0];

  return (
    <div className={`app${menuAberto ? " menu-aberto" : ""}`}>
      <header className="barra-topo">
        <button className="botao-icone-claro" onClick={() => setMenuAberto(true)} aria-label="Abrir menu">
          <Icone nome="menu" tamanho={22} />
        </button>
        <span className="barra-topo-marca"><span className="marca-logo">AX</span> GestaoAxia</span>
        <span className="avatar avatar-pequeno" title={usuario.nome}>{iniciais(usuario.nome)}</span>
      </header>
      <div className="lateral-fundo" onClick={() => setMenuAberto(false)} />

      <aside className="lateral">
        <div className="marca">
          <span className="marca-logo">AX</span>
          <div className="marca-texto">
            <strong>GestaoAxia</strong>
            <small>SST · Axia Nordeste</small>
          </div>
          <button className="botao-icone-claro lateral-fechar" onClick={() => setMenuAberto(false)} aria-label="Fechar menu">
            <Icone nome="fechar" />
          </button>
        </div>
        <nav className="nav">
          {secoes.map((s) => (
            <div key={s.titulo} className="nav-secao">
              <span className="nav-titulo">{s.titulo}</span>
              {s.itens.map((i) => (
                <NavLink key={i.para} to={i.para} end={i.fim} className="nav-item">
                  <Icone nome={i.icone} />
                  <span>{i.rotulo}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="cartao-usuario">
          <span className="avatar">{iniciais(usuario.nome)}</span>
          <div className="cartao-usuario-texto">
            <strong>{usuario.nome}</strong>
            <small>{perfil}</small>
          </div>
          <div className="cartao-usuario-acoes">
            <button className="botao-icone-claro" onClick={() => setSenhaAberta(true)} title="Trocar senha" aria-label="Trocar senha">
              <Icone nome="chave" tamanho={16} />
            </button>
            <button className="botao-icone-claro" onClick={sair} title="Sair" aria-label="Sair">
              <Icone nome="sair" tamanho={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="conteudo" ref={conteudo}>
        <Outlet />
      </main>
      <TrocarSenha aberto={senhaAberta} aoFechar={() => setSenhaAberta(false)} />
    </div>
  );
}
