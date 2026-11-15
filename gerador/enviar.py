"""E-mail da entrega (Brevo). DRY_RUN=true por padrão: grava o payload em data/outbox/, não envia."""
from __future__ import annotations
import base64, json, os, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "data" / "outbox"
API = "https://api.brevo.com/v3/smtp/email"


def dry_run() -> bool:
    return os.environ.get("DRY_RUN", "true").lower() not in ("false", "0", "no")


def _html(pedido: dict, resumo: str, suporte: str, site: str, endereco: str) -> tuple[str, str, str]:
    n = pedido.get("quantidade") or 1
    assunto = f"Seu Anúncio Pronto ({n} anúncio{'s' if n != 1 else ''}) está no anexo"
    corpo = f"""<p style="margin:0 0 14px 0;font-size:20px;line-height:27px;font-weight:800;">Material pronto para colar</p>
<p style="margin:0 0 12px 0;">Segue o pacote Anúncio Pronto em PDF e planilha (xlsx e CSV). Use os textos nos campos do Mercado Livre e da Shopee. Revise antes de publicar: o texto usa só o que você enviou no formulário.</p>
<p style="margin:0 0 12px 0;font-size:13px;color:#5b675f;">{resumo}</p>
<p style="margin:0 0 12px 0;font-size:13px;color:#5b675f;">Não publicamos no seu lugar e não pedimos senha. Não há garantia de vendas nem de posição na busca.</p>"""
    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eef4f1;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" style="max-width:600px;background:#fff;border:1px solid #d5e0da;border-radius:10px;">
<tr><td style="background:#1a4a3c;padding:18px 24px;font-size:20px;font-weight:800;color:#fff;">Descrevi</td></tr>
<tr><td style="padding:26px 24px;font-size:15px;line-height:23px;color:#12241d;">{corpo}</td></tr>
<tr><td style="padding:16px 24px 24px;border-top:1px solid #d5e0da;font-size:12px;line-height:18px;color:#5b675f;">
Você recebe este e-mail porque comprou o pacote Anúncio Pronto, da Descrevi. Dúvidas: {suporte}<br>
<a href="{site}/privacidade.html" style="color:#5b675f;">Política de privacidade</a> · <a href="{site}/termos.html" style="color:#5b675f;">Termos de uso</a><br>
{endereco}
</td></tr></table></td></tr></table></body></html>"""
    texto = f"Seu Anúncio Pronto está no anexo (PDF, planilha e CSV).\n\n{resumo}\n\nRevise antes de publicar. Dúvidas: {suporte}"
    return assunto, html, texto


def _anexo(path: Path) -> dict:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = {".pdf": "application/pdf", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".csv": "text/csv"}.get(path.suffix.lower(), "application/octet-stream")
    return {"name": path.name, "content": data, "contentType": mime}


def montar_payload(pedido: dict, arquivos: list[Path], resumo: str, cfg: dict) -> dict:
    rem = cfg.get("remetente") or {}
    suporte = os.environ.get("SUPORTE_EMAIL") or rem.get("suporte") or "heliovcastro@gmail.com"
    site = (cfg.get("urls") or {}).get("site") or "https://heliovc.github.io/descrevi"
    endereco = rem.get("endereco") or ""
    assunto, html, texto = _html(pedido, resumo, suporte, site, endereco)
    sender_email = os.environ.get("SENDER_EMAIL") or rem.get("email")
    p = {
        "sender": {"name": rem.get("nome") or "Descrevi", "email": sender_email},
        "to": [{"email": pedido["email"], "name": pedido.get("nome") or None}],
        "subject": assunto,
        "htmlContent": html,
        "textContent": texto,
        "tags": ["descrevi-entrega"],
        "attachment": [_anexo(a) for a in arquivos if a.exists()],
    }
    reply = os.environ.get("REPLY_TO") or rem.get("reply_to")
    if reply:
        p["replyTo"] = {"email": reply, "name": rem.get("nome") or "Descrevi"}
    return p


def send(payload: dict, nome: str) -> dict:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    # no DRY_RUN não gravamos o base64 inteiro (arquivos grandes); só metadados dos anexos
    gravavel = dict(payload)
    metas = []
    for a in gravavel.get("attachment") or []:
        metas.append({"name": a.get("name"), "contentType": a.get("contentType"), "bytes": len(base64.b64decode(a["content"])) if a.get("content") else 0})
    gravavel["attachment"] = metas
    f = OUTBOX / f"{nome}.json"
    f.write_text(json.dumps(gravavel, ensure_ascii=False, indent=1), encoding="utf-8")
    if dry_run() or not os.environ.get("BREVO_API_KEY"):
        return {"dry_run": True, "saved": str(f)}
    req = urllib.request.Request(API, data=json.dumps(payload).encode(), method="POST",
                                 headers={"api-key": os.environ["BREVO_API_KEY"], "Content-Type": "application/json",
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {"dry_run": False, "response": json.loads(r.read() or b"{}"), "saved": str(f)}
