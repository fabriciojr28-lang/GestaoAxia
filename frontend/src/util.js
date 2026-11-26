export const hojeISO = () => new Date().toLocaleDateString("sv-SE"); // AAAA-MM-DD no fuso local

export const mesAtualISO = () => hojeISO().slice(0, 7) + "-01";

export function dataBR(iso) {
  if (!iso) return "";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function mesBR(iso) {
  if (!iso) return "";
  const [a, m] = iso.split("-");
  const nomes = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  return `${nomes[Number(m) - 1]}/${a}`;
}

export const pct = (v) => (v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`);

export const num = (v) => (v ?? 0).toLocaleString("pt-BR");

/** Ordena por uma chave texto ignorando acentos. */
export const porNome = (a, b) => (a.nome || "").localeCompare(b.nome || "", "pt-BR");
