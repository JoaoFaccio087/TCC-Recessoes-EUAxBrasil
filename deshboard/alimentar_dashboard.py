"""Alimenta o dashboard (ABRIR-PAINEL.html) com a edição ativa da Gold (Parquet).

O dashboard traz os dados embutidos em ``window.__DADOS__``, num formato próprio
(um arquivo JSON por tabela). Este script lê os Parquet da edição ativa com o DuckDB,
converte para esse formato e regrava o bloco ``window.__DADOS__`` do HTML. Também grava
os mesmos JSON em ``deshboard/data/`` (o dashboard os lê por HTTP quando o bloco não existe).

Origem dos dados (D39): o branch ``dados`` do repositório, lido do worktree local desse branch
(``TCC_REPO_DADOS`` no .env; padrão ``%USERPROFILE%\\tcc-local\\repo-dados``), pasta ``dados/``.
É a mesma cópia que vai para o GitHub pelo ``scripts\\publicar_dados.ps1``: rode-o antes deste
script (o ``scripts\\publicar_tudo.ps1`` já faz isso na ordem certa).

Uso (na raiz do projeto):
    & $env:USERPROFILE\\tcc-local\\.venv\\Scripts\\python.exe deshboard\\alimentar_dashboard.py
    ... deshboard\\alimentar_dashboard.py --edicao 20261118-1349   # edição específica
    ... deshboard\\alimentar_dashboard.py --origem C:\\outra\\pasta\\dados   # outra pasta de dados

Diferenças entre o modelo da Gold e o do dashboard, e como foram resolvidas:
- O dashboard tem pares fixos (uma série por país e indicador, ``id_serie_par``). Na Gold,
  a série brasileira pode mudar de um episódio para outro (``ponte_serie_br_eua``: PME antiga,
  PME nova, PNAD Contínua; PIM-PF antiga e atual). Por isso, cada par da ponte vira um
  indicador com uma série por país, id ``<pais>_<id_par>``, que usa em cada episódio a série
  indicada pela ponte. A troca aparece em ``mudancas_metodologia``.
- A produção industrial dos EUA é a referência de três pares (produção, exportações totais e
  exportações para os EUA); aparece uma vez em cada indicador.
- O dashboard conta o tempo em meses. O PIB é trimestral: ``t_rel`` em trimestres vira meses
  (× 3), e as medidas do PIB em trimestres também são passadas para meses (× 3).
- Sentido "ambos" (juros e inflação) vira "neutro" ("variação" no texto do dashboard).
- Meses sem valor na Gold (``valor_painel`` nulo) ficam fora de ``fato_valor_alinhado``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import duckdb

PASTA = Path(__file__).resolve().parent
RAIZ = PASTA.parent
sys.path.insert(0, str(RAIZ / "src"))

from tcc_pipeline import config as cfgmod  # noqa: E402
from tcc_pipeline.validacao import edicao_ativa  # noqa: E402

HTML = PASTA / "ABRIR-PAINEL.html"

# Indicadores do dashboard (um por par da ponte) e grupos de filtro.
INDICADORES = {
    "producao_industrial": {"grupo": "atividade", "us": "Produção industrial", "br": "Produção industrial"},
    "pib": {"grupo": "atividade", "us": "PIB", "br": "PIB"},
    "desemprego": {"grupo": "trabalho", "us": "Taxa de desemprego", "br": "Taxa de desemprego"},
    "juros": {"grupo": "juros", "us": "Juros básicos", "br": "Juros básicos"},
    "inflacao": {"grupo": "precos", "us": "Inflação em 12 meses", "br": "Inflação em 12 meses"},
    "acoes": {"grupo": "mercado", "us": "Ações (reais)", "br": "Ações (reais)"},
    "exportacoes_total": {"grupo": "externo", "us": "Produção industrial (par das exportações totais)",
                          "br": "Exportações totais (reais)"},
    "exportacoes_eua": {"grupo": "externo", "us": "Produção industrial (par das exportações para os EUA)",
                        "br": "Exportações para os EUA (reais)"},
}
GRUPOS = [
    {"id": "atividade", "nome": "Atividade econômica"},
    {"id": "trabalho", "nome": "Mercado de trabalho"},
    {"id": "juros", "nome": "Juros"},
    {"id": "precos", "nome": "Preços"},
    {"id": "externo", "nome": "Setor externo"},
    {"id": "mercado", "nome": "Mercado acionário"},
]
PAISES = [
    {"id": "US", "nome": "EUA", "nome_completo": "Estados Unidos"},
    {"id": "BR", "nome": "Brasil", "nome_completo": "Brasil"},
]
EPISODIOS_TEXTO = {
    "1981-1982": ("1981–82", "Política monetária fortemente contracionista do Fed para conter a inflação; "
                             "no Brasil, coincide com a crise da dívida externa."),
    "2007-2009": ("2007–09", "Crise do crédito imobiliário e do sistema financeiro norte-americano, "
                             "transmitida ao Brasil pelo crédito externo, câmbio e comércio."),
    "2020": ("2020", "Choque sanitário com paralisação simultânea das atividades; "
                     "a recessão mais curta da cronologia do NBER."),
}
CRONOLOGIA_NBER = [  # picos e vales mensais do NBER no período do dashboard
    {"pico": "1980-01", "vale": "1980-07"}, {"pico": "1981-07", "vale": "1982-11"},
    {"pico": "1990-07", "vale": "1991-03"}, {"pico": "2001-03", "vale": "2001-11"},
    {"pico": "2007-12", "vale": "2009-06"}, {"pico": "2020-02", "vale": "2020-04"},
]
SITUACAO = {"OK": "recuperado", "RECUPERACAO_NAO_OBSERVADA": "nao_recuperado",
            "NAO_APLICAVEL": "nao_se_aplica"}
SENTIDO = {"queda": "queda", "alta": "alta", "ambos": "neutro"}
FREQ = {"M": "mensal", "T": "trimestral", "A": "anual"}


def ym(d) -> str | None:
    return None if d is None else f"{d.year:04d}-{d.month:02d}"


def num(x, casas: int = 4):
    return None if x is None else round(float(x), casas)


def linhas(con, sql: str) -> list[dict]:
    r = con.execute(sql)
    cols = [c[0] for c in r.description]
    return [dict(zip(cols, v)) for v in r.fetchall()]


def montar(pasta_edicao: Path, raiz_pub: Path) -> dict:
    con = duckdb.connect()
    for arq in pasta_edicao.glob("*.parquet"):
        con.execute(f"CREATE VIEW {arq.stem} AS SELECT * FROM read_parquet('{arq.as_posix()}')")

    ed = linhas(con, "SELECT * FROM dim_edicao")[0]
    id_ed = ed["id_edicao"]
    series = {s["id_serie"]: s for s in linhas(con, "SELECT * FROM dim_serie")}
    metodos = {m["id_metodo"]: m for m in linhas(con, "SELECT * FROM dim_metodo")}
    episodios = linhas(con, "SELECT * FROM dim_episodio ORDER BY pico_mensal")
    ponte = linhas(con, "SELECT * FROM ponte_serie_br_eua")
    resumo = {(r["id_serie"], r["id_episodio"]): r for r in linhas(con, "SELECT * FROM fato_resumo_episodio")}
    comp = {(c["id_par"], c["id_episodio"]): c for c in linhas(con, "SELECT * FROM fato_comparacao")}
    valores = linhas(con, """
        SELECT a.*, v.valor_original FROM fato_serie_alinhada_mensal a
        LEFT JOIN fato_valor_mensal v USING (id_serie, data_ref)
        UNION ALL BY NAME
        SELECT a.*, v.valor_original FROM fato_serie_alinhada_trimestral a
        LEFT JOIN fato_valor_trimestral v USING (id_serie, data_ref)""")
    por_serie_ep: dict[tuple, list] = {}
    for v in valores:
        por_serie_ep.setdefault((v["id_serie"], v["id_episodio"]), []).append(v)

    limiares = _limiares()
    ids_ep = [e["id_episodio"] for e in episodios]
    pico = {e["id_episodio"]: e["pico_mensal"] for e in episodios}

    dim_serie, fato_valor, fato_resumo, fato_comp = [], [], [], []
    for id_par, info in INDICADORES.items():
        trechos = {p["id_episodio"]: p for p in ponte if p["id_par"] == id_par}
        if not trechos:
            continue
        for pais, lado in (("US", "id_serie_eua"), ("BR", "id_serie_br")):
            vid = f"{pais.lower()}_{id_par}"
            par_vid = f"{'br' if pais == 'US' else 'us'}_{id_par}"
            usadas = {ep: trechos[ep][lado] for ep in ids_ep if ep in trechos and trechos[ep][lado]}
            originais = list(dict.fromkeys(usadas.values()))
            base = series[originais[0]]
            sem_dados = [ep for ep in ids_ep if ep not in usadas]
            freq = base["frequencia"]
            fator = 3 if freq == "T" else 1
            tipo = "indice" if base["tipo_medida"] == "nivel" else "pp"

            mudancas, anterior = [], None
            for ep in ids_ep:
                s = usadas.get(ep)
                if s and anterior and s != anterior:
                    mudancas.append({"data": ym(pico[ep]), "descricao":
                                     f"A partir de {EPISODIOS_TEXTO[ep][0]}: {series[s]['nome']} "
                                     f"({series[s]['fonte']} {series[s]['codigo_origem']}), no lugar de "
                                     f"{series[anterior]['nome']}."})
                anterior = s or anterior
            for s in originais:
                if series[s].get("aviso_metodologia"):
                    mudancas.append({"data": ym(series[s]["inicio_disponivel"]),
                                     "descricao": series[s]["aviso_metodologia"]})
            difs = {trechos[ep]["diferencas_metodologicas"] for ep in usadas if trechos[ep]["diferencas_metodologicas"]}

            def juntar(campo):
                return " / ".join(dict.fromkeys(str(series[s][campo]) for s in originais if series[s][campo]))

            id_metodo = next((r["id_metodo"] for s in originais for ep in ids_ep
                              if (r := resumo.get((s, ep))) and r["id_metodo"]), None)
            dim_serie.append({
                "id": vid,
                "codigo": juntar("codigo_origem"),
                "nome": info["us" if pais == "US" else "br"],
                "pais": pais,
                "grupo": info["grupo"],
                "descricao": " ".join([juntar("descricao") + "."] + sorted(difs)),
                "fonte": {"portal": juntar("fonte"), "produtor": juntar("produtor"), "url": juntar("url")},
                "unidade_original": juntar("unidade"),
                "unidade_painel": "Índice (pico = 100)" if tipo == "indice" else "Variação em p.p. desde o pico",
                "frequencia": FREQ[freq],
                "ajuste_sazonal": any(series[s]["ajuste_sazonal"] for s in originais)
                                  or bool(id_metodo and "stl" in id_metodo),
                "metodo": {"tipo": tipo, "versao": metodos[id_metodo]["versao"] if id_metodo else "1",
                           "descricao": metodos[id_metodo]["descricao"].rstrip(".") if id_metodo else ""},
                "sentido_crise": SENTIDO[base["sentido_adverso"]],
                "limiar_reacao": limiares.get(base["grupo"]),
                "periodo_inicio": min(ym(series[s]["inicio_disponivel"]) for s in originais),
                "periodo_fim": max(ym(series[s]["fim_disponivel"]) for s in originais),
                "mudancas_metodologia": mudancas,
                "id_serie_par": par_vid,
                "episodios_sem_dados": sem_dados,
                "series_gold": usadas,  # rastreabilidade: série da Gold usada em cada episódio
            })

            for ep, s in usadas.items():
                for v in por_serie_ep.get((s, ep), []):
                    t = v["t_rel"] * fator
                    if v["valor_painel"] is None or not -24 <= t <= 48:
                        continue
                    fato_valor.append({
                        "id_serie": vid, "id_episodio": ep, "mes_relativo": t,
                        "data_referencia": ym(v["data_ref"]),
                        "valor_original": num(v["valor_original"]),
                        "valor_painel": num(v["valor_painel"]),
                        "data_coleta": v["coletado_em"].date().isoformat() if v["coletado_em"] else None,
                        "id_edicao": id_ed})
                r = resumo.get((s, ep))
                if not r:
                    continue
                cobertura_ok = (r["cobertura"] or 0) > 0
                mult = lambda x: None if x is None else int(x) * fator  # noqa: E731
                fato_resumo.append({
                    "id_serie": vid, "id_episodio": ep,
                    "variacao_pico_vale": num(r["amplitude"], 2),
                    "meses_ate_vale": mult(r["t_extremo"]),
                    "meses_ate_recuperacao": mult(r["t_recuperacao"]),
                    "situacao_recuperacao": SITUACAO.get(r["status_recuperacao"], "sem_dados")
                                            if cobertura_ok else "sem_dados",
                    "mes_reacao": mult(r["t_reacao"]),
                    "id_edicao": id_ed})

        fator_par = 3 if any(series[p["id_serie_eua"]]["frequencia"] == "T" for p in trechos.values()) else 1
        for ep in ids_ep:
            c = comp.get((id_par, ep))
            if not c:
                continue
            fato_comp.append({
                "id_episodio": ep, "id_serie_eua": f"us_{id_par}", "id_serie_br": f"br_{id_par}",
                "defasagem_meses": None if c["defasagem"] is None else int(c["defasagem"]) * fator_par,
                "diferenca_variacao": num(c["dif_amplitude"], 2), "id_edicao": id_ed})

    janelas = cfgmod_regras()["janelas"]["M"]
    return {
        "edicao.json": {
            "id_edicao": id_ed,
            "gerado_em": ed["publicado_em"].strftime("%Y-%m-%dT%H:%M"),
            "ilustrativo": False,
            "janela_meses": janelas["exibicao"],
            "janela_medidas_meses": janelas["busca_recuperacao_max"],
            "aviso": (f"Edição {id_ed} da camada Gold (dados reais). Reação e pior valor buscados em até "
                      f"{janelas['busca_reacao_pior'][1]} meses após o pico; recuperação em até "
                      f"{janelas['busca_recuperacao_max']} meses. PIB trimestral convertido para meses (× 3)."),
        },
        "dim_episodio.json": [{
            "id": e["id_episodio"], "nome": e["nome"], "rotulo": EPISODIOS_TEXTO[e["id_episodio"]][0],
            "pico": ym(e["pico_mensal"]), "vale": ym(e["vale_mensal"]),
            "contexto": EPISODIOS_TEXTO[e["id_episodio"]][1]} for e in episodios],
        "dim_grupo.json": [g for g in GRUPOS if any(s["grupo"] == g["id"] for s in dim_serie)],
        "dim_pais.json": PAISES,
        "cronologia_nber.json": CRONOLOGIA_NBER,
        "dim_serie.json": dim_serie,
        "fato_valor_alinhado.json": fato_valor,
        "fato_resumo_episodio.json": fato_resumo,
        "fato_comparacao.json": fato_comp,
        "execucoes.json": _execucoes(raiz_pub),
    }


def cfgmod_regras() -> dict:
    import yaml
    return yaml.safe_load((RAIZ / "config" / "regras.yaml").read_text(encoding="utf-8"))


def _limiares() -> dict:
    """Limiar de reação na unidade do dashboard: % de queda para índice, p.p. para taxa."""
    out = {}
    for g, r in cfgmod_regras()["grupos"].items():
        lim = r["limiar"]
        out[g] = round(abs(100 - lim), 2) if lim > 50 else lim
    return out


def _execucoes(raiz_pub: Path) -> list[dict]:
    arq = raiz_pub / "controle_execucao.parquet"
    if not arq.exists():
        return []
    con = duckdb.connect()
    regs = linhas(con, f"SELECT * FROM read_parquet('{arq.as_posix()}') ORDER BY inicio")
    out = []
    for r in regs:
        dur = (r["fim"] - r["inicio"]).total_seconds() / 60 if r["fim"] and r["inicio"] else None
        status = r["status"] or ""
        obs = r["observacao"] or r["erro"] or ""
        if status == "SEM_ALTERACOES":
            obs = obs or "sem alterações nas fontes"
        out.append({
            "id_execucao": r["id_execucao"],
            # controle_execucao guarda UTC; o dashboard mostra no fuso deste computador.
            "inicio": r["inicio"].replace(tzinfo=dt.timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M"),
            "duracao_min": None if dur is None else round(dur, 1),
            "tipo": "reprocessamento" if r["comando"] == "reprocessar" else "atualizacao",
            "status": "sucesso" if status in ("SUCESSO", "SEM_ALTERACOES") else "falha",
            "series_processadas": r["series_processadas"],
            "registros": r["registros"],
            "id_edicao": r["id_edicao"] or "—",
            "observacao": obs})
    return out


def gravar(dados: dict) -> None:
    pasta_json = PASTA / "data"
    pasta_json.mkdir(exist_ok=True)
    for nome, conteudo in dados.items():
        (pasta_json / nome).write_text(json.dumps(conteudo, ensure_ascii=False, indent=1), encoding="utf-8")

    html = HTML.read_text(encoding="utf-8")
    bloco = "window.__DADOS__=" + json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    novo, n = re.subn(r"window\.__DADOS__=\{.*?\}(?=;?</script>)", lambda _: bloco, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("Bloco window.__DADOS__ não encontrado em ABRIR-PAINEL.html")
    # Texto fixo do dashboard que ainda citava o Airflow (retirado na D6).
    novo = novo.replace("feitos pelo responsável no Airflow",
                        "feitos pelo responsável na pipeline Python (Agendador de Tarefas do Windows)")
    HTML.write_text(novo, encoding="utf-8")


def origem_padrao() -> Path:
    """Pasta dados/ do worktree do branch ``dados`` (D39)."""
    import os
    repo = os.environ.get("TCC_REPO_DADOS") or Path(os.environ["USERPROFILE"]) / "tcc-local" / "repo-dados"
    return Path(repo) / "dados"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--edicao", help="id da edição (padrão: a ativa em atual.json)")
    ap.add_argument("--origem", help="pasta de dados (padrão: dados/ do worktree do branch dados)")
    args = ap.parse_args()
    cfgmod.carregar_env()
    origem = Path(args.origem) if args.origem else origem_padrao()
    raiz_pub = origem / "publicacao"
    if not (raiz_pub / "atual.json").exists():
        raise SystemExit(f"Nenhuma edição em {raiz_pub}. Rode antes o scripts\\publicar_dados.ps1 "
                         "(ele atualiza o branch dados).")
    print(f"Origem: {origem}")
    pasta = raiz_pub / "edicoes" / args.edicao if args.edicao else edicao_ativa(raiz_pub)
    dados = montar(pasta, raiz_pub)
    gravar(dados)
    print(f"Dashboard alimentado com a edição {dados['edicao.json']['id_edicao']}: "
          f"{len(dados['dim_serie.json'])} séries, {len(dados['fato_valor_alinhado.json'])} valores, "
          f"{len(dados['fato_resumo_episodio.json'])} resumos, {len(dados['fato_comparacao.json'])} comparações.")


if __name__ == "__main__":
    main()
