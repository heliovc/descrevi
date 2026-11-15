#!/usr/bin/env python3
"""e2e local da Descrevi: compra → formulário → geração → checagens → PDF/xlsx
→ e-mail DRY_RUN → reembolso revoga → purge de 30 dias → título grátis (teto).

Não fala com produção, não envia e-mail real, não baixa o link de referência.
"""
from __future__ import annotations
import json, os, sqlite3, subprocess, sys, time, urllib.error, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
WORKER = ROOT / "intake" / "worker"
ESTADO = ROOT / "e2e" / ".estado-worker"
SAIDA = ROOT / "e2e" / "saida"
SHOTS = ROOT / "screenshots"
WURL = "http://127.0.0.1:8788"
SITE = "http://127.0.0.1:4173"
TOKEN = "test-token-descrevi"
EXPORT = "test-export-descrevi"

PRODUTOS = [
    {
        "indice": 1,
        "nome_produto": "Garrafa térmica inox",
        "categoria": "Utilidades domésticas",
        "especificacoes": "Capacidade 1 litro. Material: aço inox. Parede dupla. Tampa com rosca. Não vai à boca do fogão. Cor a cadastrar como variação.",
        "diferenciais": "Parede dupla e tampa com rosca",
        "plataforma": "ambos",
        "link_referencia": "http://127.0.0.1:9/nao-buscar-este-anuncio",
    },
    {
        "indice": 2,
        "nome_produto": "Organizador de gaveta em acrílico",
        "categoria": "Organização e armazenamento",
        "especificacoes": "Medidas: 40 × 30 × 5 cm. Material: acrílico transparente de 3 mm. 6 divisórias fixas. Limpeza com pano úmido e sabão neutro; não usar álcool.",
        "diferenciais": "Divisórias fixas, acrílico de 3 mm",
        "plataforma": "ambos",
        "link_referencia": "",
    },
    {
        "indice": 3,
        "nome_produto": "Fone de ouvido bluetooth",
        "categoria": "Áudio",
        "especificacoes": "Bluetooth 5.3. Estojo carregador. Microfone. Compatível com iPhone, Samsung e Xiaomi (três marcas). Sem informação de autonomia.",
        "diferenciais": "Estojo carregador e microfone",
        "plataforma": "ambos",
        "link_referencia": "",
    },
]


class Cores:
    ok = fail = skip = 0


def passo(msg):
    print(f"\n=== {msg}", flush=True)


def checar(cond, msg):
    if cond:
        Cores.ok += 1
        print(f"  ok  {msg}", flush=True)
        return True
    Cores.fail += 1
    print(f"  FALHOU  {msg}", flush=True)
    return False


def get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            corpo = json.loads(e.read() or b"{}")
        except Exception:
            corpo = {}
        return e.code, corpo


def post(url, corpo, headers=None, timeout=20):
    h = {"content-type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST", headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            corpo = json.loads(e.read() or b"{}")
        except Exception:
            corpo = {}
        return e.code, corpo


def db_path() -> Path:
    # wrangler local: persist-to/v3/d1/miniflare-D1DatabaseObject/<id>.sqlite  (dados podem estar no WAL)
    cands = [p for p in ESTADO.glob("**/d1/**/*.sqlite") if p.name != "metadata.sqlite"]
    for p in cands:
        try:
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            tem = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pedidos'").fetchone()
            con.close()
            if tem:
                return p
        except Exception:
            continue
    raise FileNotFoundError(f"D1 com tabela pedidos não encontrado em {ESTADO} (candidatos: {cands})")


def sql(q, args=()):
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(q, args)
        if q.strip().lower().startswith("select"):
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def espera_worker():
    for _ in range(40):
        try:
            st, j = get(WURL + "/")
            if st == 200 and j.get("servico") == "descrevi-intake":
                return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("Worker não subiu em http://127.0.0.1:8788")


def inicia_worker():
    ESTADO.mkdir(parents=True, exist_ok=True)
    # limpa estado anterior para o teste ser determinístico
    import shutil
    if ESTADO.exists():
        shutil.rmtree(ESTADO)
    ESTADO.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["npx", "wrangler", "d1", "execute", "descrevi", "--local", "--persist-to", str(ESTADO), "--file=schema.sql"],
        cwd=str(WORKER), check=False, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise RuntimeError("falha ao aplicar schema.sql")
    log = (ROOT / "e2e" / "worker.log").open("w")
    proc = subprocess.Popen(
        ["npx", "wrangler", "dev", "--local", "--port", "8788", "--persist-to", str(ESTADO), "--ip", "127.0.0.1"],
        cwd=str(WORKER), stdout=log, stderr=subprocess.STDOUT,
    )
    return proc, log


def main():
    os.chdir(ROOT)
    os.environ.setdefault("KIWIFY_TOKEN", TOKEN)
    os.environ.setdefault("EXPORT_TOKEN", EXPORT)
    os.environ.setdefault("INTAKE_EXPORT_TOKEN", EXPORT)
    os.environ.setdefault("INTAKE_URL", WURL)
    os.environ.setdefault("DRY_RUN", "true")
    # chave só se já estiver no ambiente ou se GEMINI_ENV_FILE for passado por fora
    SAIDA.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)

    passo("checagens unitárias (sem rede)")
    from gerador.checagem import checar_titulo_ml, checar_titulo_shopee, tem_erro, contar_marcas_citadas
    item = {"nome_produto": "Garrafa", "especificacoes": "1 litro inox", "plataforma": "ambos"}
    p1 = checar_titulo_ml("OFERTA Garrafa Frete Gratis estoque", item)
    checar(tem_erro(p1), "título ML com estoque/frete/oferta é recusado")
    p2 = checar_titulo_ml("Garrafa Térmica Inox 1 Litro Parede Dupla Tampa Rosca", item)
    checar(not tem_erro(p2) and len("Garrafa Térmica Inox 1 Litro Parede Dupla Tampa Rosca") <= 60,
           "título ML válido de 53 caracteres passa")
    longo = "A" * 61
    checar(tem_erro(checar_titulo_ml(longo, item)), "título ML com 61 caracteres é recusado")
    spam = "Fone Bluetooth fone fone fone Samsung Xiaomi Motorola Apple"
    checar(tem_erro(checar_titulo_shopee(spam, item)), "título Shopee com 4 marcas ou repetição é recusado")
    # 4 marcas depois de "para"
    quatro = "Capa Anime para Iphone, Samsung, Xiaomi, Motorola"
    checar(len(contar_marcas_citadas(quatro, item)) > 3, "detector de mais de 3 marcas")

    proc, logf = None, None
    httpd = None
    try:
        passo("sobe o Worker local")
        proc, logf = inicia_worker()
        espera_worker()
        checar(True, "GET / → descrevi-intake")

        passo("compra Kiwify (pacote de 3)")
        sim = subprocess.run(
            [sys.executable, str(ROOT / "intake/mock/kiwify_sim.py"), "order_approved",
             "--email", "vendedor.teste@example.com", "--nome", "Ana Teste", "--pacote", "3",
             "--url", WURL + "/kiwify", "--token", TOKEN],
            capture_output=True, text=True, check=False,
        )
        checar(sim.returncode == 0, f"webhook order_approved 200 ({sim.stdout.strip()[:200]})")
        dados = json.loads(sim.stdout)
        order_id = dados["order_id"]
        # idempotência
        sim2 = subprocess.run(
            [sys.executable, str(ROOT / "intake/mock/kiwify_sim.py"), "order_approved",
             "--email", "vendedor.teste@example.com", "--nome", "Ana Teste", "--pacote", "3",
             "--order", order_id, "--url", WURL + "/kiwify", "--token", TOKEN],
            capture_output=True, text=True, check=False,
        )
        j2 = json.loads(sim2.stdout)
        checar(j2["resposta"].get("duplicado") is True, "segundo webhook do mesmo evento é idempotente")

        rows = sql("SELECT * FROM pedidos WHERE order_id=?", (order_id,))
        checar(len(rows) == 1 and rows[0]["status"] == "pago" and rows[0]["quantidade"] == 3, "pedido pago, 3 itens")
        token_p = rows[0]["token"]
        pedido_id = rows[0]["id"]
        outb = sql("SELECT tipo,assunto,dry_run FROM outbox WHERE pedido_id=?", (pedido_id,))
        checar(any(o["tipo"] == "formulario" and o["dry_run"] == 1 for o in outb), "e-mail do formulário gravado em DRY_RUN")

        passo("formulário (API)")
        st, ped = get(f"{WURL}/pedido?t={token_p}")
        checar(st == 200 and ped["quantidade"] == 3, "GET /pedido devolve o pacote")
        st, resp = post(f"{WURL}/pedido/enviar", {"token": token_p, "consentimento": True, "itens": PRODUTOS})
        checar(st == 200 and resp.get("preenchidos") == 3, f"POST /pedido/enviar preenche 3/3 ({resp})")
        # o link foi guardado e nada tentou buscá-lo (porta 9 recusaria; só checamos o valor)
        itens = sql("SELECT link_referencia FROM itens WHERE pedido_id=? AND indice=1", (pedido_id,))
        checar(itens and "nao-buscar-este-anuncio" in (itens[0]["link_referencia"] or ""),
               "link de referência gravado, sem fetch")

        passo("geração (PDF + xlsx + CSV + e-mail DRY_RUN)")
        # Preferimos Gemini se a chave local estiver disponível, senão mock.
        env = os.environ.copy()
        env.setdefault("PYTHONPATH", str(ROOT))
        if not env.get("GEMINI_API_KEY") and not env.get("GEMINI_ENV_FILE"):
            candidato = Path("/workspace/fornecia/privado/gemini.env")
            if candidato.exists():
                env["GEMINI_ENV_FILE"] = str(candidato)
        # se ainda assim a chave falhar, o gerador cai? não: provedor() escolhe gemini se a chave carregar.
        # Forçamos carregar antes para decidir.
        from gerador.ia import carregar_chave_local
        if env.get("GEMINI_ENV_FILE") and not os.environ.get("GEMINI_API_KEY"):
            os.environ["GEMINI_ENV_FILE"] = env["GEMINI_ENV_FILE"]
            carregar_chave_local()
            if os.environ.get("GEMINI_API_KEY"):
                env["GEMINI_API_KEY"] = os.environ["GEMINI_API_KEY"]
        if not env.get("GEMINI_API_KEY"):
            env["DESCREVI_PROVIDER"] = "mock"
        ger = subprocess.run(
            [sys.executable, "-m", "gerador.gerar", "--pedido-id", pedido_id, "--enviar",
             "--status-remoto", "--saida", str(SAIDA)],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=240,
        )
        print(ger.stdout[-2000:] if ger.stdout else "")
        if ger.returncode != 0:
            print(ger.stderr[-2000:] if ger.stderr else "")
        checar(ger.returncode == 0, "gerador encerrou com sucesso")
        pdfs = list(SAIDA.glob("*.pdf"))
        xlsx = list(SAIDA.glob("*.xlsx"))
        csvs = list(SAIDA.glob("*.csv"))
        checar(bool(pdfs) and pdfs[0].stat().st_size > 2000, f"PDF gerado ({pdfs})")
        checar(bool(xlsx), "xlsx gerado")
        checar(bool(csvs), "CSV gerado")
        # o JSON da geração contém o link e nenhum fetch foi necessário
        meta = json.loads(next(SAIDA.glob("*.json")).read_text())
        link = meta["itens"][0]["item"].get("link_referencia") or ""
        checar("nao-buscar" in link, "link aparece na saída, só como referência")
        provedor = meta.get("provedor") or ""
        print(f"  provedor usado: {provedor}", flush=True)
        outbox_files = list((ROOT / "data" / "outbox").glob("*.json"))
        checar(bool(outbox_files), "payload de e-mail DRY_RUN em data/outbox/")
        if outbox_files:
            payload = json.loads(outbox_files[-1].read_text())
            checar(payload.get("to") and "attachment" in payload and payload["subject"], "payload tem destinatário, assunto e anexos")
            # não deve ter tentado enviar de verdade
            # send() com DRY_RUN não chama a API

        st, stj = post(f"{WURL}/interno/status", {"pedido_id": pedido_id, "status": "enviado", "detalhe": "e2e"},
                       headers={"authorization": f"Bearer {EXPORT}"})
        # pode já ter sido marcado pelo --status-remoto
        checar(st == 200, f"interno/status aceito ({stj})")

        passo("reembolso revoga o link")
        simr = subprocess.run(
            [sys.executable, str(ROOT / "intake/mock/kiwify_sim.py"), "order_refunded",
             "--email", "vendedor.teste@example.com", "--order", order_id, "--pacote", "3",
             "--url", WURL + "/kiwify", "--token", TOKEN],
            capture_output=True, text=True, check=False,
        )
        checar(simr.returncode == 0, "webhook order_refunded 200")
        st, ped2 = get(f"{WURL}/pedido?t={token_p}")
        checar(st == 410, f"GET /pedido após reembolso devolve 410 ({ped2})")
        st, ped3 = get(f"{WURL}/interno/pedido?id={pedido_id}", headers={"authorization": f"Bearer {EXPORT}"})
        checar(st == 410, "GET /interno/pedido reembolsado também 410")

        passo("purge de 30 dias")
        # insere um pedido velho direto no D1
        import uuid
        from datetime import datetime, timedelta, timezone
        velho = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
        pid = str(uuid.uuid4())
        sql("INSERT INTO pedidos (id,email,nome,order_id,token,pacote,quantidade,status,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (pid, "apagar@example.com", "Velho", str(uuid.uuid4()), "x" * 48, "3", 3, "enviado", velho, velho))
        sql("INSERT INTO itens (id,pedido_id,indice,nome_produto,preenchido,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), pid, 1, "Produto a apagar", 1, velho, velho))
        st, rot = post(f"{WURL}/admin/rotina", {}, headers={"authorization": f"Bearer {EXPORT}"})
        checar(st == 200 and rot.get("pedidos_apagados", 0) >= 1, f"rotina apagou pedido com mais de 30 dias ({rot})")
        ainda = sql("SELECT id FROM pedidos WHERE id=?", (pid,))
        checar(ainda == [], "pedido velho não está mais no D1")
        ainda_i = sql("SELECT id FROM itens WHERE pedido_id=?", (pid,))
        checar(ainda_i == [], "itens do pedido velho também apagados")

        passo("título grátis: 3 por IP, o 4º recusa")
        corpo_t = {"nome_produto": "Garrafa térmica", "especificacoes": "inox 1 litro parede dupla", "turnstile": "skip"}
        oks = 0
        ultimo = None
        for i in range(4):
            st, j = post(f"{WURL}/titulo-gratis", corpo_t)
            ultimo = (st, j)
            if st == 200 and j.get("titulo"):
                oks += 1
        checar(oks == 3, f"3 gerações grátis aceitas (títulos ok)")
        checar(ultimo[0] == 429, f"a 4ª geração do mesmo IP devolve 429 ({ultimo[1]})")
        if oks:
            t = None
            # pega um título da 1ª — refazemos a asserção pelo último 200 não disponível; conferimos limite
        # gera com IP “outro” não dá para forçar fácil; o teto por IP basta

        passo("páginas do site + capturas")
        class SiteHandler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(ROOT / "site"), **kw)
        httpd = ThreadingHTTPServer(("127.0.0.1", 4173), SiteHandler)
        Thread(target=httpd.serve_forever, daemon=True).start()
        time.sleep(0.2)
        with urllib.request.urlopen(SITE + "/index.html", timeout=10) as r:
            html = r.read().decode()
        checar("Anúncio Pronto" in html and "Descrevi" in html, "landing carrega com a marca e o pacote")
        checar("não garantimos vendas" in html.lower() or "Não garantimos vendas" in html, "landing sem promessa de vendas")
        checar("Radar de Licitações" not in html and "Valora" not in html, "landing sem Valora / Radar")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, executable_path="/usr/bin/google-chrome")
                page = browser.new_page(viewport={"width": 390, "height": 844})
                page.goto(SITE + "/index.html", wait_until="load")
                page.screenshot(path=str(SHOTS / "landing-mobile.png"), full_page=True)
                page.set_viewport_size({"width": 1280, "height": 800})
                page.goto(SITE + "/index.html", wait_until="load")
                page.screenshot(path=str(SHOTS / "landing-desktop.png"), full_page=True)
                page.goto(SITE + "/titulo.html", wait_until="load")
                page.screenshot(path=str(SHOTS / "titulo-gratis.png"), full_page=True)
                page.goto(SITE + "/privacidade.html", wait_until="load")
                page.screenshot(path=str(SHOTS / "privacidade.png"), full_page=True)
                # formulário com token já revogado deve mostrar erro — usamos um token fresco? o pedido foi reembolsado.
                # abre a página mesmo assim
                page.goto(SITE + f"/formulario.html?t={token_p}", wait_until="load")
                page.wait_for_timeout(800)
                page.screenshot(path=str(SHOTS / "formulario-revogado.png"), full_page=True)
                browser.close()
            checar((SHOTS / "landing-mobile.png").exists() and (SHOTS / "landing-desktop.png").exists(),
                   f"capturas em {SHOTS}")
        except Exception as e:
            Cores.fail += 1
            print(f"  FALHOU  playwright: {e}", flush=True)

    finally:
        if httpd:
            try:
                httpd.shutdown()
            except Exception:
                pass
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except Exception:
                proc.kill()
        if logf:
            logf.close()

    print(f"\nResultado: {Cores.ok} ok, {Cores.fail} falha(s)")
    return 1 if Cores.fail else 0


if __name__ == "__main__":
    sys.exit(main())
