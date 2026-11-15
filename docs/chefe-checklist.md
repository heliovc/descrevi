# O que falta no lado do Chefe / do dono (nada disso foi publicado)

1. **Dois produtos na Kiwify** (3 anúncios / R$ 47 e 10 anúncios / R$ 127), com os `product_id` reais e os links de checkout. Trocar os placeholders em `config.json`, `intake/worker/wrangler.toml` e `site/js/config.js`. Webhook HMAC apontando para `https://descrevi-intake.heliovcastro.workers.dev/kiwify?signature=…` (ou a URL definitiva). Token do webhook vira o secret `KIWIFY_TOKEN`.
2. **Repositório GitHub `heliovc/descrevi`**, Pages no endereço `https://heliovc.github.io/descrevi/`. O workflow `pages.yml` só roda no `workflow_dispatch` — não publicar antes da revisão. O site está em `site/`.
3. **Worker `descrevi-intake`** na conta Cloudflare (sugestão: a mesma `heliovcastro`, ciente de que o plano gratuito **divide** 100 mil requisições/dia, D1 e KV com a Fornecia). Criar o D1 `descrevi`, aplicar `schema.sql`, configurar os `[vars]` e os secrets: `KIWIFY_TOKEN`, `EXPORT_TOKEN`, `LINK_SECRET`, `BREVO_API_KEY`, `TURNSTILE_SECRET`, `GITHUB_DISPATCH_TOKEN`. `DRY_RUN` deve continuar `true` até o dono autorizar e-mail real.
4. **Turnstile** (par de chaves de produção) no gerador de título; colocar a site key em `config.js` / `wrangler.toml` e o secret no Worker.
5. **Chave Gemini de um projeto separado** (obrigatório para não dividir a cota da Fornecia). Secret `GEMINI_API_KEY` no GitHub e, se o título grátis for usar IA no Worker, também no Worker. Ver estimativa de cota no README do relatório.
6. **Remetente Brevo** e decisão do **e-mail de suporte**. A copy e os legais usam temporariamente `heliovcastro@gmail.com`. Não usar endereço da Valora sem aprovação explícita do dono.
7. **Busca formal no INPI** (pePI, classes 35 e 42) de DESCREVI e, por cautela, de ANUNCIO PRONTO. A busca rápida está em `docs/marca.md`.
8. Revisão dos rascunhos em `docs/legal/` e da landing (`docs/copy-ajustes.md` lista o que mudou em relação à copy da Vitrine).
9. Conferir, logado, as regras de autopromoção do Reddit antes de postar as respostas da copy (a Vitrine não conseguiu lê-las).

Nada disto deve ser feito por este repositório automaticamente: sem push, sem deploy, sem e-mail real, sem criar conta.
