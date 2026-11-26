import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { Avisos, Carregando } from "./components/ui";
import { ProvedorApp, useApp } from "./contexto";
import Cadastros from "./pages/Cadastros";
import Colaboradores from "./pages/Colaboradores";
import Fechamento from "./pages/Fechamento";
import Login from "./pages/Login";
import Movimentacoes from "./pages/Movimentacoes";
import Painel from "./pages/Painel";
import Pro from "./pages/Pro";
import Usuarios from "./pages/Usuarios";
import "./estilo.css";

function Rotas() {
  const { usuario, carregando, opcoes, pode } = useApp();
  if (carregando) return <Carregando />;
  if (!usuario || !opcoes) return <Login />;
  const interno = (el) => (pode.interno ? el : <Navigate to="/movimentacoes" replace />);
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={interno(<Painel />)} />
        <Route path="movimentacoes" element={<Movimentacoes />} />
        <Route path="colaboradores" element={<Colaboradores />} />
        <Route path="fechamento" element={interno(<Fechamento />)} />
        <Route path="pro" element={interno(<Pro />)} />
        <Route path="cadastros" element={interno(<Cadastros />)} />
        <Route path="usuarios" element={pode.admin ? <Usuarios /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to={pode.interno ? "/" : "/movimentacoes"} replace />} />
      </Route>
    </Routes>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ProvedorApp>
      <BrowserRouter>
        <Rotas />
        <Avisos />
      </BrowserRouter>
    </ProvedorApp>
  </StrictMode>,
);
