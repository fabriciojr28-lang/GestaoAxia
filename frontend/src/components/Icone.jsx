// Ícones em SVG (traço), sem dependências externas.
const CAMINHOS = {
  painel: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  movimentacoes: "M7 7h13l-4-4M17 17H4l4 4",
  fechamento: "M4 4h16v16H4zM4 9h16M9 4v16",
  pro: "M9 12l2 2 4-4M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z",
  colaboradores: "M16 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6M22 19v-1a4 4 0 0 0-3-3.9M16 4.1a3 3 0 0 1 0 5.8",
  cadastros: "M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6M9 10h.01M15 10h.01",
  usuarios: "M15 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0M5 21v-2a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v2",
  chave: "M15 7a4 4 0 1 1-3.9 4.9L3 20v-3h3v-3h3l1.1-1.1A4 4 0 0 1 15 7z",
  sair: "M15 4h4v16h-4M10 17l5-5-5-5M15 12H3",
  menu: "M4 6h16M4 12h16M4 18h16",
  fechar: "M6 6l12 12M18 6L6 18",
};

export default function Icone({ nome, tamanho = 18 }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="icone">
      <path d={CAMINHOS[nome]} />
    </svg>
  );
}
