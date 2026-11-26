# GestaoAxia

Sistema web de gestão do efetivo SST da Axia Nordeste. Substitui três planilhas:

| Planilha antiga | No sistema |
|---|---|
| `EFETIVO SST BV.xlsx` | **Colaboradores** — cadastro único do efetivo |
| `Faturamento Movimentacao Mensal.xlsx` → aba MOVIMENTAÇÃO | **Movimentações** — lançamento diário |
| `Faturamento Movimentacao Mensal.xlsx` → FECHAMENTO + dashboards | **Fechamento mensal** + **Painel** |
| `Controle Evidencias PRO.xlsx` | **Evidências PRO** |

Stack: **FastAPI + SQLite** (backend) e **React + Vite** (frontend). Em produção um único container
serve a API e as telas.

## Perfis de acesso

| Perfil | O que faz |
|---|---|
| Administrador | Tudo, inclusive usuários, fechar/reabrir mês, mesclar e excluir cadastros |
| Editor | Alimenta todas as áreas (sem gestão de usuários) |
| Coordenador | Vê **só a própria equipe** e lança/edita as movimentações dela |
| Somente leitura | Consulta tudo, não altera nada |

Regras importantes:
- Quem é transferido para uma obra passa para a equipe do coordenador daquela obra.
- Depois de **fechar um mês**, só administradores alteram lançamentos daquele mês.
- Nomes de ativos, coordenadores e colaboradores não podem se repetir (acentos e espaços são ignorados).

## Rodar no computador (Windows)

Dê dois cliques em **`iniciar.bat`**. Ele instala o que faltar, compila as telas, importa as planilhas
na primeira vez e abre http://localhost:8000. Feche a janela preta para desligar.

Pré-requisitos: Python 3.12+ e Node.js LTS. A configuração local fica em `backend/.env`
(copiado de `backend/.env.example`, fora do git).

### Desenvolvimento (com recarga automática)

```bash
# terminal 1 — API em http://127.0.0.1:8000 (docs em /api/docs)
cd backend
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload

# terminal 2 — telas em http://localhost:5173
cd frontend
npm install
npm run dev
```

Testes: `cd backend && python -m pytest -q`

## Importar / reimportar as planilhas

Coloque os `.xlsx` na raiz do projeto (eles nunca vão para o git — têm CPF e telefones) e rode:

```bash
cd backend
python -m app.importar --pasta ..              # só se o banco estiver vazio
python -m app.importar --pasta .. --substituir # apaga os dados (mantém usuários) e reimporta
```

O importador padroniza nomes (`RAFAEL BITU` → `RAFAEL COSTA LEANDRO BITU`, `BOM NOME` → `SE BOM NOME`)
e lista no final tudo que precisa de conferência (datas invertidas, nomes abreviados, linhas duplicadas).

## Produção: VPS com Portainer (Docker Swarm + Traefik)

Toda a configuração fica no bloco `environment` da stack — nada no código.

| Endereço | O que responde |
|---|---|
| https://app.gestaoaxia.com.br | Telas do sistema |
| https://api.gestaoaxia.com.br | API — o Traefik acrescenta `/api` (ex.: `/colaboradores` → `/api/colaboradores`) |

As telas descobrem o endereço da API lendo `/config.js`, que o backend gera a partir da variável
`API_URL` da stack. Por isso o mesmo build serve para qualquer domínio.

1. **DNS**: registros tipo A de `app.gestaoaxia.com.br` e `api.gestaoaxia.com.br` para o IP da VPS
   (o Let's Encrypt do Traefik só emite o certificado depois que o DNS responde).
2. **Rede**: a stack usa a rede overlay externa `GestaoAxia`, a mesma do Traefik
   (`--providers.swarm.network=GestaoAxia`).
3. **Imagem**: a cada push na `main` o GitHub Actions roda os testes e publica
   `ghcr.io/fabriciojr28-lang/gestaoaxia:latest`; cada tag `vX.Y.Z` publica também `:vX.Y.Z`.
   Se o pacote for privado, cadastre `ghcr.io` no Portainer (*Registries*) com um token do GitHub
   com permissão `read:packages`.
4. **Stack**: Portainer → *Stacks* → *Add stack* → *Web editor* e cole o conteúdo de
   `stack.portainer.yml` (arquivo local com os valores reais, fora do git; o `docker-compose.yml`
   do repositório é o mesmo modelo com valores de exemplo).
5. **Atualizar**: em *Services* → `gestaoaxia_gestaoaxia` → *Update the service* marcando
   *Re-pull image*. O serviço para antes de subir o novo (`order: stop-first`) porque o SQLite
   não pode ter dois processos gravando.

No Swarm o nome do container muda a cada deploy. Para os comandos abaixo, pegue o nome atual com
`docker ps --filter name=gestaoaxia --format '{{.Names}}'` e use no lugar de `gestaoaxia`.
6. **Dados iniciais** — escolha um:
   - enviar o banco já importado (com o sistema local desligado):
     `docker cp dados/gestaoaxia.db gestaoaxia:/dados/`, depois
     `docker exec -u 0 gestaoaxia chown 1000:1000 /dados/gestaoaxia.db` e reiniciar o container; ou
   - importar lá: `docker cp "PLANILHA.xlsx" gestaoaxia:/dados/` (as três) e
     `docker exec gestaoaxia python -m app.importar --pasta /dados`
     (para reimportar por cima, acrescente `--substituir`; os usuários são mantidos).
7. **Backup**: o banco inteiro é o arquivo `/dados/gestaoaxia.db` do volume `gestaoaxia_dados`.

### Variáveis da stack

| Variável | Para que serve |
|---|---|
| `SECRET_KEY` | Assina os logins. 32+ caracteres aleatórios. Trocar derruba todas as sessões. |
| `TOKEN_EXPIRA_MINUTOS` | Quanto tempo o login dura |
| `DATABASE_PATH` | Caminho do SQLite (dentro do volume `/dados`) |
| `ADMIN_EMAIL` / `ADMIN_SENHA` / `ADMIN_NOME` | Administrador criado no primeiro start, se o e-mail ainda não existir. Mudar depois **não** altera a senha de um admin já criado — use "Trocar senha" na tela. |
| `API_URL` | Endereço público da API que as telas chamam (`https://api.gestaoaxia.com.br`). Vazio = mesmo endereço das telas |
| `CORS_ORIGINS` | Endereço das telas autorizado a chamar a API (`https://app.gestaoaxia.com.br`) |
| `FRONTEND_DIST` | Pasta das telas dentro da imagem (`/app/frontend_dist`) |
| `TZ` | Fuso horário do container |
