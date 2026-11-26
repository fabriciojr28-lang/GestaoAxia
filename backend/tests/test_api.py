from datetime import date, timedelta

from conftest import entrar


def _base(client, admin):
    """Dois coordenadores, uma obra para cada, um colaborador em cada equipe."""
    c1 = client.post("/api/coordenadores", json={"nome": "Rafael Costa Leandro Bitu"}, headers=admin).json()
    c2 = client.post("/api/coordenadores", json={"nome": "Helder Damasceno"}, headers=admin).json()
    a1 = client.post("/api/ativos", json={"nome": "SE Milagres II", "uf": "CE", "coordenador_id": c1["id"]},
                     headers=admin).json()
    a2 = client.post("/api/ativos", json={"nome": "SE Bongi", "uf": "PE", "coordenador_id": c2["id"]},
                     headers=admin).json()
    p1 = client.post("/api/colaboradores", json={"nome": "Ana Lopes", "coordenador_id": c1["id"],
                                                 "ativo_atual_id": a1["id"]}, headers=admin).json()
    p2 = client.post("/api/colaboradores", json={"nome": "Aline Paulo", "coordenador_id": c2["id"],
                                                 "ativo_atual_id": a2["id"]}, headers=admin).json()
    return c1, c2, a1, a2, p1, p2


def _criar_login_coordenador(client, admin, coord_id, email="rafael@teste.com"):
    r = client.post("/api/usuarios", json={"email": email, "nome": "Rafael", "perfil": "coordenador",
                                           "coordenador_id": coord_id, "senha": "senha-coord-123"}, headers=admin)
    assert r.status_code == 201, r.text
    return entrar(client, email, "senha-coord-123")


def test_login_errado_e_rota_protegida(client):
    assert client.post("/api/auth/login", data={"username": "admin@teste.com", "password": "x"}).status_code == 401
    assert client.get("/api/colaboradores").status_code == 401


def test_admin_criado_pela_stack(client, admin):
    eu = client.get("/api/auth/eu", headers=admin).json()
    assert eu["perfil"] == "admin" and eu["email"] == "admin@teste.com"


def test_nome_duplicado_ignora_acento_e_espacos(client, admin):
    assert client.post("/api/coordenadores", json={"nome": "Américo dos Santos"}, headers=admin).status_code == 201
    r = client.post("/api/coordenadores", json={"nome": "AMERICO  DOS SANTOS"}, headers=admin)
    assert r.status_code == 409


def test_movimentacao_valida_datas_e_destino(client, admin):
    _, _, _, _, p1, _ = _base(client, admin)
    r = client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "FOLGA",
                                                "data_inicio": "2026-08-28", "data_fim": "2026-08-14"}, headers=admin)
    assert r.status_code == 422 and "anterior" in r.json()["detail"]
    r = client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "TRANSFERIDO",
                                                "data_inicio": "2026-08-01"}, headers=admin)
    assert r.status_code == 422 and "destino" in r.json()["detail"]


def test_coordenador_so_ve_e_lanca_para_sua_equipe(client, admin):
    c1, _, _, _, p1, p2 = _base(client, admin)
    rafael = _criar_login_coordenador(client, admin, c1["id"])

    nomes = [c["nome"] for c in client.get("/api/colaboradores", headers=rafael).json()]
    assert nomes == ["ANA LOPES"]

    ontem = (date.today() - timedelta(days=1)).isoformat()
    daqui = (date.today() + timedelta(days=5)).isoformat()
    ok = client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "FOLGA",
                                                 "data_inicio": ontem, "data_fim": daqui}, headers=rafael)
    assert ok.status_code == 201, ok.text
    assert ok.json()["coordenador"]["id"] == c1["id"]
    assert client.get(f"/api/colaboradores/{p1['id']}", headers=admin).json()["situacao"] == "FOLGA"

    negado = client.post("/api/movimentacoes", json={"colaborador_id": p2["id"], "tipo": "FOLGA",
                                                     "data_inicio": ontem, "data_fim": daqui}, headers=rafael)
    assert negado.status_code == 403

    # o coordenador não acessa outras áreas
    assert client.get("/api/painel", headers=rafael).status_code == 403
    assert client.get("/api/pro", headers=rafael).status_code == 403
    assert client.get("/api/fechamento?mes=2026-11-01", headers=rafael).status_code == 403
    assert client.post("/api/ativos", json={"nome": "X"}, headers=rafael).status_code == 403
    assert client.get(f"/api/colaboradores/{p2['id']}", headers=rafael).status_code == 404


def test_transferencia_muda_equipe_do_colaborador(client, admin):
    c1, c2, _, a2, p1, _ = _base(client, admin)
    rafael = _criar_login_coordenador(client, admin, c1["id"])
    hoje = date.today().isoformat()
    r = client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "TRANSFERIDO",
                                                "ativo_id": a2["id"], "data_inicio": hoje}, headers=rafael)
    assert r.status_code == 201, r.text
    colab = client.get(f"/api/colaboradores/{p1['id']}", headers=admin).json()
    assert colab["ativo_atual"]["id"] == a2["id"] and colab["coordenador"]["id"] == c2["id"]
    # quem lançou continua vendo o próprio lançamento
    assert len(client.get("/api/movimentacoes", headers=rafael).json()) == 1


def test_fechamento_calcula_dias_e_mes_fechado_bloqueia(client, admin):
    c1, _, _, _, p1, _ = _base(client, admin)
    client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "FERIAS",
                                            "data_inicio": "2026-10-25", "data_fim": "2026-11-03"}, headers=admin)
    r = client.post("/api/fechamento/gerar?mes=2026-11-01", headers=admin)
    assert r.status_code == 200 and r.json()["criadas"] == 2
    linhas = client.get("/api/fechamento?mes=2026-11-01", headers=admin).json()["linhas"]
    ana = next(x for x in linhas if x["colaborador"]["nome"] == "ANA LOPES")
    assert ana["dias_ferias"] == 3  # 1, 2 e 3 de novembro

    assert client.post("/api/fechamento/fechar?mes=2026-11-01", headers=admin).status_code == 204
    rafael = _criar_login_coordenador(client, admin, c1["id"])
    r = client.post("/api/movimentacoes", json={"colaborador_id": p1["id"], "tipo": "FOLGA",
                                                "data_inicio": "2026-11-10", "data_fim": "2026-11-12"}, headers=rafael)
    assert r.status_code == 423

    xlsx = client.get("/api/fechamento/exportar?mes=2026-11-01", headers=admin)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


def test_pro_status_documental(client, admin):
    _, _, a1, _, _, _ = _base(client, admin)
    ct = client.post("/api/contratadas", json={"nome": "HWM Engenharia"}, headers=admin).json()
    docs = {k: "OK" for k in ("apr", "pex", "cr", "lista_forum", "lista_rpac", "forum_aprovacao")}
    r = client.post("/api/pro", json={"contratada_id": ct["id"], "ativo_id": a1["id"], "data": "2026-11-20",
                                      "atividade": "Lançamento de cabos", **docs, "cr": "PENDENTE"}, headers=admin)
    assert r.status_code == 201, r.text
    assert r.json()["status_documental"] == "Incompleto" and r.json()["documentos_em_aberto"] == ["CR"]
    assert r.json()["coordenador"] is not None  # herdado do ativo
    painel = client.get("/api/painel?mes=2026-11-01", headers=admin).json()
    assert painel["pro"]["docs_em_aberto"]["CR"] == 1


def test_leitura_nao_altera(client, admin):
    client.post("/api/usuarios", json={"email": "ver@teste.com", "nome": "Visitante", "perfil": "leitura",
                                       "senha": "senha-leitura-1"}, headers=admin)
    leitor = entrar(client, "ver@teste.com", "senha-leitura-1")
    assert client.get("/api/painel", headers=leitor).status_code == 200
    assert client.post("/api/contratadas", json={"nome": "X Ltda"}, headers=leitor).status_code == 403


def test_config_js_publica_endereco_da_api(client):
    r = client.get("/config.js")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/javascript")
    assert r.text.strip() == 'window.GESTAOAXIA_API = "";'
