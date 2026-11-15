#!/usr/bin/env python3
"""Gera o pacote Anúncio Pronto: IA → checagens (com retry) → PDF/xlsx/CSV → e-mail DRY_RUN.

Uso:
  python3 -m gerador.gerar --local-json pedido.json --saida gerador/saida
  python3 -m gerador.gerar --pedido-id UUID --enviar --saida gerador/saida

O link de referência, se existir, é só copiado para a saída. Nunca é baixado.
E-mail e nome do comprador não vão para o provedor de IA.
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador.ia import carregar_chave_local, provedor, ErroIA
from gerador.checagem import checar, tem_erro, aplicar_acentos, listar_confirmacoes
from gerador.pdf import renderizar
from gerador.planilha import escrever_xlsx, escrever_csv
from gerador import enviar as envio

MAX_TENTATIVAS = 3  # 1 geração + 2 retries se a checagem falhar


def _cfg() -> dict:
    p = ROOT / "config.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"authorization": f"Bearer {token}", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def _post(url: str, token: str, corpo: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"authorization": f"Bearer {token}", "content-type": "application/json",
                                          "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return {"erro": e.read().decode("utf-8", "replace"), "status": e.code}


def carregar_pedido_remoto(pedido_id: str) -> dict:
    import urllib.error
    base = os.environ.get("INTAKE_URL") or (_cfg().get("urls") or {}).get("intake")
    token = os.environ.get("INTAKE_EXPORT_TOKEN") or os.environ.get("EXPORT_TOKEN")
    if not base or not token:
        raise SystemExit("INTAKE_URL e INTAKE_EXPORT_TOKEN são obrigatórios para --pedido-id")
    dados = _get(f"{base.rstrip('/')}/interno/pedido?id={pedido_id}", token)
    if "pedido" not in dados:
        raise SystemExit(f"falha ao ler pedido: {dados}")
    return dados


def gerar_um(prov, item: dict) -> tuple[dict, list]:
    """Gera um anúncio e recusa/regenera se a checagem tiver erro."""
    erros = None
    ultimo = None
    checagens = []
    for i in range(MAX_TENTATIVAS):
        anuncio = prov.gerar(item, erros_anteriores=erros)
        aplicar_acentos(anuncio, item)
        checagens = checar(anuncio, item)
        anuncio["_checagens"] = checagens
        anuncio["_tentativas"] = i + 1
        anuncio["confirmacoes"] = listar_confirmacoes(anuncio)
        if not tem_erro(checagens):
            return anuncio, checagens
        erros = [c for c in checagens if c["nivel"] == "erro"]
        ultimo = anuncio
    # esgota retries: devolve a última com as falhas visíveis em pendencias
    pend = list(ultimo.get("pendencias") or [])
    for e in erros:
        msg = f"Checagem automática: {e['mensagem']}"
        if msg not in pend:
            pend.append(msg)
    ultimo["pendencias"] = pend
    ultimo["_falhou_checagem"] = True
    ultimo["confirmacoes"] = listar_confirmacoes(ultimo)
    return ultimo, checagens


def slug(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:40] or "anuncio"


def gerar_pedido(pedido: dict, itens: list[dict], saida: Path, enviar: bool = False) -> dict:
    carregar_chave_local()
    prov = provedor()
    gerados = []
    for it in itens:
        # garantia: o gerador nunca faz fetch do link
        item = {k: it.get(k) for k in ("nome_produto", "categoria", "especificacoes", "diferenciais", "plataforma", "marca")}
        item["plataforma"] = (item.get("plataforma") or "ambos").lower()
        anuncio, checagens = gerar_um(prov, item)
        gerados.append({
            "item": {**item, "link_referencia": it.get("link_referencia") or None, "indice": it.get("indice")},
            "anuncio": anuncio,
            "checagens": checagens,
            "provedor": getattr(prov, "nome", ""),
            "modelo": getattr(prov, "modelo", ""),
        })

    saida.mkdir(parents=True, exist_ok=True)
    prefixo = f"anuncio-pronto-{slug(pedido.get('id') or 'local')}"
    pdf = saida / f"{prefixo}.pdf"
    xlsx = saida / f"{prefixo}.xlsx"
    csvp = saida / f"{prefixo}.csv"
    renderizar(pedido, gerados, pdf)
    escrever_xlsx(gerados, xlsx)
    escrever_csv(gerados, csvp)
    meta = saida / f"{prefixo}.json"
    # JSON de auditoria: sem e-mail? na verdade o pedido tem e-mail; útil para o envio, mas o arquivo de amostra
    # pode mascarar. Mantemos o e-mail só se for gerar+enviar; amostras usam e-mail fictício.
    dump = {
        "pedido": {k: pedido.get(k) for k in ("id", "email", "nome", "pacote", "quantidade", "status")},
        "provedor": getattr(prov, "nome", ""),
        "itens": gerados,
        "arquivos": [str(pdf), str(xlsx), str(csvp)],
    }
    meta.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    n_err = sum(1 for g in gerados if any(c["nivel"] == "erro" for c in g["checagens"]))
    resumo = f"{len(gerados)} anúncio(s) no PDF e na planilha."
    if n_err:
        resumo += f" {n_err} com alerta de checagem que não saiu na regeneração — veja “O que conferir”."
    resultado = {"pdf": str(pdf), "xlsx": str(xlsx), "csv": str(csvp), "json": str(meta),
                 "provedor": getattr(prov, "nome", ""), "erros_persistentes": n_err, "resumo": resumo}

    if enviar:
        cfg = _cfg()
        payload = envio.montar_payload(pedido, [pdf, xlsx, csvp], resumo, cfg)
        resultado["email"] = envio.send(payload, prefixo)
    return resultado


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-json", help="arquivo com {pedido, itens} (fluxo local/e2e)")
    ap.add_argument("--pedido-id")
    ap.add_argument("--enviar", action="store_true")
    ap.add_argument("--saida", default=str(ROOT / "gerador" / "saida"))
    ap.add_argument("--status-remoto", action="store_true", help="atualiza /interno/status no Worker")
    a = ap.parse_args()
    if a.local_json:
        dados = json.loads(Path(a.local_json).read_text(encoding="utf-8"))
        pedido, itens = dados["pedido"], dados["itens"]
    elif a.pedido_id:
        import urllib.error
        dados = carregar_pedido_remoto(a.pedido_id)
        pedido, itens = dados["pedido"], dados["itens"]
        # marca em geração (idempotente)
        token = os.environ.get("INTAKE_EXPORT_TOKEN") or os.environ.get("EXPORT_TOKEN")
        base = os.environ.get("INTAKE_URL") or ""
        if a.status_remoto and base and token:
            _post(f"{base.rstrip('/')}/interno/status", token, {"pedido_id": pedido["id"], "status": "em_geracao"})
    else:
        ap.error("informe --local-json ou --pedido-id")

    try:
        if pedido.get("status") == "reembolsado":
            raise SystemExit("pedido reembolsado; geração cancelada")
        res = gerar_pedido(pedido, itens, Path(a.saida), enviar=a.enviar)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if a.pedido_id and a.status_remoto:
            token = os.environ.get("INTAKE_EXPORT_TOKEN") or os.environ.get("EXPORT_TOKEN")
            base = os.environ.get("INTAKE_URL") or ""
            detalhe = json.dumps({"resumo": res["resumo"], "provedor": res["provedor"], "erros": res["erros_persistentes"]})
            print(_post(f"{base.rstrip('/')}/interno/status", token, {"pedido_id": pedido["id"], "status": "enviado", "detalhe": detalhe}))
        return 0
    except Exception as e:
        if a.pedido_id and a.status_remoto:
            token = os.environ.get("INTAKE_EXPORT_TOKEN") or os.environ.get("EXPORT_TOKEN")
            base = os.environ.get("INTAKE_URL") or ""
            if base and token:
                _post(f"{base.rstrip('/')}/interno/status", token,
                      {"pedido_id": a.pedido_id, "status": "falhou", "detalhe": json.dumps({"erro": str(e)[:500]})})
        raise


if __name__ == "__main__":
    sys.exit(main())
