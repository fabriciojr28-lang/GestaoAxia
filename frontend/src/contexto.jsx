import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, quandoSessaoExpirar, token } from "./api";

const Contexto = createContext(null);

/** Sessão do usuário + listas usadas nos formulários (carregadas uma vez). */
export function ProvedorApp({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(Boolean(token.get()));
  const [opcoes, setOpcoes] = useState(null);
  const [listas, setListas] = useState({ coordenadores: [], ativos: [] });

  const sair = useCallback(() => {
    token.limpar();
    setUsuario(null);
    setOpcoes(null);
  }, []);

  const recarregarListas = useCallback(async () => {
    const [coordenadores, ativos] = await Promise.all([api("/coordenadores"), api("/ativos")]);
    setListas({ coordenadores, ativos });
  }, []);

  const iniciar = useCallback(async () => {
    const [eu, ops] = await Promise.all([api("/auth/eu"), api("/opcoes")]);
    setUsuario(eu);
    setOpcoes(ops);
    await recarregarListas();
  }, [recarregarListas]);

  useEffect(() => {
    quandoSessaoExpirar(sair);
    if (token.get()) {
      iniciar().catch(sair).finally(() => setCarregando(false));
    }
  }, [iniciar, sair]);

  async function entrar(email, senha) {
    const r = await api("/auth/login", { method: "POST", form: { username: email, password: senha } });
    token.set(r.access_token);
    await iniciar();
  }

  const perfil = usuario?.perfil;
  const permissoes = {
    interno: ["admin", "editor", "leitura"].includes(perfil),
    editar: ["admin", "editor"].includes(perfil),
    lancar: ["admin", "editor", "coordenador"].includes(perfil),
    admin: perfil === "admin",
    coordenador: perfil === "coordenador",
  };

  return (
    <Contexto.Provider
      value={{ usuario, carregando, opcoes, listas, recarregarListas, entrar, sair, pode: permissoes }}
    >
      {children}
    </Contexto.Provider>
  );
}

export const useApp = () => useContext(Contexto);
