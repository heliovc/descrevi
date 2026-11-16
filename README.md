# Descrevi · pacote Anúncio Pronto

Texto de anúncio para Mercado Livre e Shopee, a partir dos dados que o vendedor cola no formulário. Site: `https://heliovc.github.io/descrevi/`. Worker: `https://descrevi-intake.heliovcastro.workers.dev`.

Site e Worker em produção. `DRY_RUN=false` no Worker e na Action (envio real pela Brevo).

## O que já roda aqui

- Worker local (`wrangler dev --local`, porta 8788): webhook Kiwify (HMAC-SHA1, idempotente), e-mail do formulário (Brevo em DRY_RUN), GET/POST do pedido, reembolso revoga o link, título grátis com teto (3/IP/dia e teto global), rotina de lembrete e **purge de 30 dias**.
- Gerador Python: Gemini (se houver `GEMINI_API_KEY`) ou mock, checagens das regras das plataformas, retry, PDF + xlsx + CSV, e-mail DRY_RUN.
- Site estático (landing, formulário, título grátis, termos e privacidade).
- e2e em `e2e/run_e2e.py`.
- Duas amostras em `amostra/`.

O link opcional do anúncio é **só referência**: é gravado e impresso na saída; **nunca é baixado**.

## Como rodar localmente

```bash
cd intake/worker
npm install
npx wrangler d1 execute descrevi --local --persist-to ../../e2e/.estado-worker --file=schema.sql
npx wrangler dev --local --port 8788 --persist-to ../../e2e/.estado-worker
# em outro terminal, na raiz:
python3 intake/mock/kiwify_sim.py order_approved --email teste@example.com --pacote 3 --url http://localhost:8788/kiwify
python3 -m gerador.gerar --local-json caminho/pedido.json --enviar --saida gerador/saida
python3 e2e/run_e2e.py
```

Chave Gemini: defina `GEMINI_API_KEY` no ambiente, ou `GEMINI_ENV_FILE` apontando para um arquivo fora deste repo (em testes locais pode ser o da Fornecia). **Não copie a chave para cá.** O Chefe providencia uma chave de projeto separado antes da produção.

`DRY_RUN` fica `true` por padrão. Não ligue envio real sem aprovação do dono.

## O que o Chefe ainda precisa arrumar (antes de publicar)

Ver `docs/chefe-checklist.md`.
