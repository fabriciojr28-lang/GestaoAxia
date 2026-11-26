import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

/** Carrega dados da API e expõe recarregar(); refaz quando deps mudam. */
export function useDados(caminho, params, deps = []) {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(true);
  const chave = JSON.stringify(params || {});
  const recarregar = useCallback(async () => {
    setCarregando(true);
    try {
      setDados(await api(caminho, { params: JSON.parse(chave) }));
      setErro("");
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caminho, chave, ...deps]);
  useEffect(() => {
    recarregar();
  }, [recarregar]);
  return { dados, erro, carregando, recarregar, setDados };
}

/** Aviso flutuante simples. */
let mostrarAvisoGlobal = () => {};
export const avisar = (texto, tipo = "ok") => mostrarAvisoGlobal({ texto, tipo, id: Date.now() });

export function Avisos() {
  const [aviso, setAviso] = useState(null);
  useEffect(() => {
    mostrarAvisoGlobal = setAviso;
  }, []);
  useEffect(() => {
    if (!aviso) return undefined;
    const t = setTimeout(() => setAviso(null), aviso.tipo === "erro" ? 6000 : 3000);
    return () => clearTimeout(t);
  }, [aviso]);
  if (!aviso) return null;
  return (
    <div className={`aviso aviso-${aviso.tipo}`} role="status" onClick={() => setAviso(null)}>
      {aviso.texto}
    </div>
  );
}

export function Modal({ titulo, aberto, aoFechar, children, largura = 640, rodape }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!aberto) return undefined;
    const esc = (e) => e.key === "Escape" && aoFechar();
    document.addEventListener("keydown", esc);
    ref.current?.querySelector("input,select,textarea")?.focus();
    return () => document.removeEventListener("keydown", esc);
  }, [aberto, aoFechar]);
  if (!aberto) return null;
  return (
    <div className="modal-fundo" onMouseDown={(e) => e.target === e.currentTarget && aoFechar()}>
      <div className="modal" style={{ maxWidth: largura }} ref={ref} role="dialog" aria-modal="true">
        <header className="modal-topo">
          <h2>{titulo}</h2>
          <button type="button" className="botao-icone" onClick={aoFechar} aria-label="Fechar">
            ×
          </button>
        </header>
        <div className="modal-corpo">{children}</div>
        {rodape && <footer className="modal-rodape">{rodape}</footer>}
      </div>
    </div>
  );
}

export function Campo({ rotulo, dica, erro, children, largo }) {
  return (
    <label className={`campo${largo ? " campo-largo" : ""}`}>
      <span className="campo-rotulo">{rotulo}</span>
      {children}
      {dica && <span className="campo-dica">{dica}</span>}
      {erro && <span className="campo-erro">{erro}</span>}
    </label>
  );
}

/** <select> a partir de um dicionário {codigo: rotulo} ou lista de objetos {id, nome}. */
export function Selecao({ valor, aoMudar, opcoes, vazio = "Selecione…", desabilitado, obrigatorio }) {
  const itens = Array.isArray(opcoes)
    ? opcoes.map((o) => (typeof o === "string" ? [o, o] : [String(o.id), o.nome]))
    : Object.entries(opcoes || {});
  return (
    <select
      value={valor ?? ""}
      onChange={(e) => aoMudar(e.target.value)}
      disabled={desabilitado}
      required={obrigatorio}
    >
      {vazio !== null && <option value="">{vazio}</option>}
      {itens.map(([k, v]) => (
        <option key={k} value={k}>
          {v}
        </option>
      ))}
    </select>
  );
}

/** Campo de busca com lista (datalist) para escolher um item por nome entre muitos. */
export function Busca({ valor, aoMudar, itens, placeholder = "Digite para buscar…", obrigatorio }) {
  const atual = itens.find((i) => String(i.id) === String(valor));
  const [texto, setTexto] = useState(atual?.nome || "");
  const idLista = useRef(`lista-${Math.random().toString(36).slice(2)}`).current;
  useEffect(() => {
    setTexto(atual?.nome || "");
  }, [atual?.nome]);
  return (
    <>
      <input
        list={idLista}
        value={texto}
        placeholder={placeholder}
        required={obrigatorio}
        onChange={(e) => {
          setTexto(e.target.value);
          const achado = itens.find((i) => i.nome === e.target.value.toUpperCase() || i.nome === e.target.value);
          aoMudar(achado ? String(achado.id) : "");
        }}
        onBlur={() => !valor && setTexto("")}
      />
      <datalist id={idLista}>
        {itens.map((i) => (
          <option key={i.id} value={i.nome} />
        ))}
      </datalist>
    </>
  );
}

export function Etiqueta({ tipo = "neutra", children, titulo }) {
  return (
    <span className={`etiqueta etiqueta-${tipo}`} title={titulo}>
      {children}
    </span>
  );
}

export function Vazio({ children }) {
  return <div className="vazio">{children}</div>;
}

export function Erro({ children }) {
  return children ? <div className="erro-bloco">{children}</div> : null;
}

export function Carregando() {
  return <div className="carregando">Carregando…</div>;
}

/** Confirmação nativa com texto claro. */
export const confirmar = (texto) => window.confirm(texto);

/** Converte "" em null para campos de id/data antes de enviar para a API. */
export function limparVazios(obj, campos) {
  const copia = { ...obj };
  campos.forEach((c) => {
    if (copia[c] === "" || copia[c] === undefined) copia[c] = null;
    else if (c.endsWith("_id") && copia[c] !== null) copia[c] = Number(copia[c]);
  });
  return copia;
}
