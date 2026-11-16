"""Simulador de webhooks da Kiwify (só local) para a Descrevi.

POST <url>?signature=<HMAC-SHA1 hex do corpo cru, chave = token>.
Docs: https://docs.kiwify.com.br/api-reference/webhooks/receiving
"""
from __future__ import annotations
import argparse, hashlib, hmac, json, os, sys, urllib.error, urllib.request, uuid
from datetime import datetime, timedelta, timezone

STATUS = {
    "order_approved": "paid", "order_rejected": "refused",
    "order_refunded": "refunded", "chargeback": "chargedback",
}
PRODUTO = {"product_id": "bbbbbbbb-0000-4ccc-8ddd-ffffffffffff", "product_name": "Anúncio Pronto"}
OFERTAS = {
    "3": {"product_offer_id": "cccccccc-3333-4ccc-8ddd-ffffffffffff", "product_offer_name": "3 anúncios"},
    "10": {"product_offer_id": "cccccccc-aaaa-4ccc-8ddd-ffffffffffff", "product_offer_name": "10 anúncios"},
}


def payload(evento, email, nome="Cliente Teste", order_id=None, pacote="3", agora=None):
    agora = agora or datetime.now(timezone.utc)
    brt = (agora - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
    order_id = order_id or str(uuid.uuid4())
    order_status = STATUS.get(evento, "paid")
    oferta = OFERTAS.get(str(pacote), OFERTAS["3"])
    return {
        "order_id": order_id, "order_ref": order_id[:8].upper(), "order_status": order_status,
        "product_type": "digital", "payment_method": "credit_card", "store_id": "LOJA-TESTE",
        "installments": 1, "created_at": brt, "updated_at": brt,
        "approved_date": brt if order_status == "paid" else None,
        "refunded_at": brt if order_status in ("refunded", "chargedback") else None,
        "webhook_event_type": evento,
        "Product": {**PRODUTO, **oferta},
        "Customer": {"full_name": nome, "first_name": nome.split()[0], "email": email},
        "Commissions": {"charge_amount": 12700 if str(pacote) == "10" else 4700, "currency": "BRL"},
    }


def assinar(corpo: bytes, token: str) -> str:
    return hmac.new(token.encode(), corpo, hashlib.sha1).hexdigest()


def enviar(url, corpo: bytes, assinatura: str):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}signature={assinatura}", data=corpo, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evento")
    ap.add_argument("--email", required=True)
    ap.add_argument("--nome", default="Cliente Teste")
    ap.add_argument("--order")
    ap.add_argument("--pacote", default="3", choices=["3", "10"])
    ap.add_argument("--url", default="http://localhost:8788/kiwify")
    ap.add_argument("--token", default=os.environ.get("KIWIFY_TOKEN", "test-token-descrevi"))
    a = ap.parse_args()
    p = payload(a.evento, a.email, a.nome, a.order, a.pacote)
    corpo = json.dumps(p, ensure_ascii=False, separators=(",", ":")).encode()
    status, resp = enviar(a.url, corpo, assinar(corpo, a.token))
    print(json.dumps({"status": status, "resposta": resp, "order_id": p["order_id"]}, ensure_ascii=False))
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
