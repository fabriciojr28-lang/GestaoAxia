// Cliente da API: guarda o token, trata sessão expirada e mensagens de erro.
const CHAVE_TOKEN = "gestaoaxia.token";

export const token = {
  get: () => localStorage.getItem(CHAVE_TOKEN),
  set: (t) => localStorage.setItem(CHAVE_TOKEN, t),
  limpar: () => localStorage.removeItem(CHAVE_TOKEN),
};

let aoExpirar = () => {};
export function quandoSessaoExpirar(fn) {
  aoExpirar = fn;
}

// Endereço da API vem da stack (variável API_URL) via /config.js.
// Ex.: "https://api.gestaoaxia.com.br" — vazio = mesmo endereço das telas (/api).
const BASE_API = (window.GESTAOAXIA_API || "").replace(/\/$/, "");

function montarUrl(caminho, params) {
  const url = new URL(BASE_API ? `${BASE_API}${caminho}` : `/api${caminho}`, window.location.origin);
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "" && v !== false) url.searchParams.set(k, v);
  });
  return url;
}

export async function api(caminho, { method = "GET", body, params, form } = {}) {
  const headers = {};
  const t = token.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  let corpo;
  if (form) {
    corpo = new URLSearchParams(form);
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    corpo = JSON.stringify(body);
  }
  const resp = await fetch(montarUrl(caminho, params), { method, headers, body: corpo });
  if (resp.status === 401 && caminho !== "/auth/login") {
    token.limpar();
    aoExpirar();
    throw new Error("Sua sessão expirou. Entre novamente.");
  }
  if (resp.status === 204) return null;
  const dados = await resp.json().catch(() => null);
  if (!resp.ok) {
    const detalhe = dados?.detail;
    throw new Error(typeof detalhe === "string" ? detalhe : "Não foi possível concluir a operação.");
  }
  return dados;
}

export async function baixar(caminho, params, nomeArquivo) {
  const resp = await fetch(montarUrl(caminho, params), {
    headers: { Authorization: `Bearer ${token.get()}` },
  });
  if (!resp.ok) throw new Error("Não foi possível gerar o arquivo.");
  const blob = await resp.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = nomeArquivo;
  link.click();
  URL.revokeObjectURL(link.href);
}
