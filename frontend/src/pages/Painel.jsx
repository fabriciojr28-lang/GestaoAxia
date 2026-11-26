import { useState } from "react";
import { Link } from "react-router-dom";
import { Carregando, Erro, Etiqueta, useDados } from "../components/ui";
import { dataBR, mesAtualISO, mesBR, num, pct } from "../util";

function Indicador({ rotulo, valor, detalhe, destaque, para }) {
  const conteudo = (
    <>
      <span className="indicador-rotulo">{rotulo}</span>
      <span className="indicador-valor">{valor}</span>
      {detalhe && <span className="indicador-detalhe">{detalhe}</span>}
    </>
  );
  const classe = `indicador${destaque ? ` indicador-${destaque}` : ""}`;
  return para ? <Link to={para} className={`${classe} indicador-link`}>{conteudo}</Link> : <div className={classe}>{conteudo}</div>;
}

/** Lista de barras horizontais: rótulo, barra proporcional e valor. */
function Barras({ dados, cor = "azul", vazio = "Sem dados" }) {
  const itens = Object.entries(dados || {}).filter(([, v]) => v > 0);
  if (!itens.length) return <p className="suave">{vazio}</p>;
  const max = Math.max(...itens.map(([, v]) => v));
  return (
    <ul className="barras">
      {itens.map(([rotulo, v]) => (
        <li key={rotulo}>
          <span className="barra-rotulo" title={rotulo}>{rotulo}</span>
          <span className="barra-trilho">
            <span className={`barra barra-${cor}`} style={{ width: `${(v / max) * 100}%` }} />
          </span>
          <span className="barra-valor">{num(v)}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Painel() {
  const [mes, setMes] = useState(mesAtualISO());
  const { dados: d, erro, carregando } = useDados("/painel", { mes });

  return (
    <section>
      <header className="pagina-topo">
        <div>
          <h1>Painel</h1>
          <p className="subtitulo">Efetivo, movimentações do mês e evidências do PRO num só lugar.</p>
        </div>
        <label className="campo campo-inline">
          <span className="campo-rotulo">Mês de referência</span>
          <input type="month" value={mes.slice(0, 7)} onChange={(e) => e.target.value && setMes(`${e.target.value}-01`)} />
        </label>
      </header>
      <Erro>{erro}</Erro>
      {carregando && !d ? <Carregando /> : d && (
        <>
          <h2 className="secao-titulo">Efetivo</h2>
          <div className="indicadores">
            <Indicador rotulo="Em campo" valor={num(d.efetivo.em_campo)} detalhe={`de ${num(d.efetivo.total)} cadastrados`} para="/colaboradores" />
            <Indicador rotulo="Trabalhando hoje" valor={num(d.efetivo.em_campo - d.efetivo.fora_hoje.total)} destaque="verde"
              detalhe="em campo, sem folga/férias/afastamento hoje" />
            <Indicador rotulo="Fora hoje" valor={num(d.efetivo.fora_hoje.total)} destaque="amarela"
              detalhe={`${d.efetivo.fora_hoje.folga} folga · ${d.efetivo.fora_hoje.ferias} férias · ${d.efetivo.fora_hoje.afastado} afastado`} />
            <Indicador rotulo="Cadastros incompletos" valor={num(d.efetivo.cadastros_incompletos)}
              detalhe="sem CPF, matrícula, função ou ativo" destaque={d.efetivo.cadastros_incompletos ? "laranja" : ""}
              para="/colaboradores?pendentes=1" />
          </div>

          <h2 className="secao-titulo">Movimentações · {mesBR(d.mes)} {d.mes_fechado && <Etiqueta tipo="neutra">mês fechado</Etiqueta>}</h2>
          <div className="indicadores">
            <Indicador rotulo="Movimentações no mês" valor={num(d.movimentacoes.no_mes)}
              detalhe={`${num(d.movimentacoes.pessoas_movimentadas)} pessoa(s)`} para="/movimentacoes" />
            <Indicador rotulo="Pessoas em folga / férias" valor={num(d.movimentacoes.pessoas_folga_ferias)} />
            <Indicador rotulo="Dias de folga" valor={num(d.movimentacoes.dias_folga)} />
            <Indicador rotulo="Dias de férias" valor={num(d.movimentacoes.dias_ferias)}
              detalhe={d.movimentacoes.dias_afastado ? `+ ${d.movimentacoes.dias_afastado} dia(s) de afastamento` : null} />
          </div>

          <div className="grade-2">
            <div className="cartao">
              <h3>Movimentações por tipo</h3>
              <Barras dados={d.movimentacoes.por_tipo} vazio="Nenhuma movimentação iniciada neste mês." />
            </div>
            <div className="cartao">
              <h3>Últimos lançamentos</h3>
              {d.movimentacoes.ultimas.length ? (
                <ul className="lista-simples">
                  {d.movimentacoes.ultimas.map((u) => (
                    <li key={u.id}>
                      <strong>{u.colaborador}</strong>
                      <span>{u.tipo}{u.ativo && ` · ${u.ativo}`}</span>
                      <span className="suave">{dataBR(u.data_inicio)}{u.data_fim && ` a ${dataBR(u.data_fim)}`}</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="suave">Nada lançado neste mês.</p>}
            </div>
          </div>

          <h2 className="secao-titulo">Evidências do PRO</h2>
          <div className="indicadores">
            <Indicador rotulo="Registros de PRO" valor={num(d.pro.registros)} detalhe={`${d.pro.ativos} ativos`} para="/pro" />
            <Indicador rotulo="Completos" valor={num(d.pro.completos)} destaque="verde" />
            <Indicador rotulo="Incompletos" valor={num(d.pro.incompletos)} destaque={d.pro.incompletos ? "laranja" : ""}
              para="/pro?aberto=1" />
            <Indicador rotulo="Completude" valor={pct(d.pro.completude)}
              detalhe={d.pro.prazos_vencidos ? `${d.pro.prazos_vencidos} com prazo vencido` : "registros 100% documentados"}
              destaque={d.pro.prazos_vencidos ? "vermelha" : ""} />
          </div>
          <div className="grade-2">
            <div className="cartao">
              <h3>Documentos em aberto</h3>
              <Barras dados={d.pro.docs_em_aberto} cor="laranja" vazio="Nenhum documento pendente." />
              {Object.values(d.pro.docs_a_validar).some(Boolean) && (
                <>
                  <h4>A validar</h4>
                  <Barras dados={d.pro.docs_a_validar} cor="amarela" />
                </>
              )}
            </div>
            <div className="cartao">
              <h3>Ativos com pendência documental</h3>
              {d.pro.por_ativo.filter((a) => a.docs_em_aberto).length ? (
                <table className="tabela tabela-compacta">
                  <thead><tr><th>Ativo</th><th>Registros</th><th>Docs. em aberto</th><th>Aderência</th></tr></thead>
                  <tbody>
                    {d.pro.por_ativo.filter((a) => a.docs_em_aberto).map((a) => (
                      <tr key={a.ativo}>
                        <td>{a.ativo}</td><td>{a.registros}</td><td>{a.docs_em_aberto}</td><td>{pct(a.aderencia)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <p className="suave">Todos os ativos estão com a documentação completa.</p>}
            </div>
          </div>

          <div className="grade-2">
            <div className="cartao">
              <h3>Efetivo em campo por coordenador</h3>
              <Barras dados={d.efetivo.por_coordenador} />
            </div>
            <div className="cartao">
              <h3>Veículos e hospedagem · fechamento {mesBR(d.mes)}</h3>
              {d.fechamento.linhas ? (
                <div className="grade-2 grade-interna">
                  <Barras dados={d.fechamento.veiculos} cor="azul" />
                  <Barras dados={d.fechamento.hospedagens} cor="roxa" />
                </div>
              ) : <p className="suave">Fechamento deste mês ainda não gerado. <Link to="/fechamento">Gerar agora</Link></p>}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
