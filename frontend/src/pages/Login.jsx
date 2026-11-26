import { useState } from "react";
import { useApp } from "../contexto";

export default function Login() {
  const { entrar } = useApp();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setErro("");
    try {
      await entrar(email.trim(), senha);
    } catch (err) {
      setErro(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login-fundo">
      <form className="login-cartao" onSubmit={enviar}>
        <div className="marca marca-login">
          <span className="marca-logo">AX</span>
          <div>
            <strong>GestaoAxia</strong>
            <small>Gestão do efetivo SST · Axia Nordeste</small>
          </div>
        </div>
        <label className="campo">
          <span className="campo-rotulo">E-mail</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus
            autoComplete="username" />
        </label>
        <label className="campo">
          <span className="campo-rotulo">Senha</span>
          <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required
            autoComplete="current-password" />
        </label>
        {erro && <div className="erro-bloco">{erro}</div>}
        <button className="botao botao-primario botao-bloco" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
        <p className="login-rodape">Esqueceu a senha? Peça ao administrador para redefinir.</p>
      </form>
    </div>
  );
}
