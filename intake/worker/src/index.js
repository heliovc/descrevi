// Descrevi intake (Cloudflare Worker + D1)
//   POST /kiwify?signature=…     webhook da Kiwify (HMAC-SHA1 do corpo cru; idempotente)
//   GET  /pedido                 dados do pedido pelo token (página do formulário)
//   POST /pedido/enviar          formulário com N produtos (link só referência; nunca buscado)
//   POST /titulo-gratis          1 título (Turnstile + 3/IP/dia + teto global)
//   GET  /interno/pedido         Action/CLI busca o pedido (Bearer EXPORT_TOKEN)
//   POST /interno/status         Action/CLI marca enviado|falhou
//   GET  /admin/outbox  POST /admin/rotina
//   scheduled                    lembrete de formulário + purge de 30 dias
import * as T from "./templates.js";

const enc = new TextEncoder();
const agora = () => new Date().toISOString();
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const json = (obj, status = 200, extra = {}) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8", ...extra } });

async function hmacHex(hash, key, bytes) {
  const k = await crypto.subtle.importKey("raw", enc.encode(key), { name: "HMAC", hash }, false, ["sign"]);
  return [...new Uint8Array(await crypto.subtle.sign("HMAC", k, bytes))].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function igualConstante(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
const tokenAleatorio = () => [...crypto.getRandomValues(new Uint8Array(24))].map((b) => b.toString(16).padStart(2, "0")).join("");
const normEmail = (e) => String(e || "").trim().toLowerCase();

function autorizado(req, env) {
  const h = req.headers.get("authorization") || "";
  return !!env.EXPORT_TOKEN && igualConstante(h, `Bearer ${env.EXPORT_TOKEN}`);
}
function cors(req, env) {
  const origem = req.headers.get("origin") || "";
  const ok = (env.ORIGENS_PERMITIDAS || env.SITE_URL || "").split(",").map((s) => {
    try { return new URL(s.trim()).origin; } catch { return ""; }
  }).filter(Boolean);
  // páginas locais do e2e (qualquer localhost)
  const local = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(origem);
  return (ok.includes(origem) || local)
    ? { "access-control-allow-origin": origem, "access-control-allow-methods": "GET,POST,OPTIONS", "access-control-allow-headers": "content-type", vary: "origin" }
    : {};
}

async function enviar(env, dest, tipo, msg) {
  const dry = env.DRY_RUN !== "false" || !env.BREVO_API_KEY;
  let resposta = null;
  if (!dry) {
    const r = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: { "api-key": env.BREVO_API_KEY, "content-type": "application/json", accept: "application/json" },
      body: JSON.stringify({
        sender: { name: env.SENDER_NAME, email: env.SENDER_EMAIL },
        ...(env.REPLY_TO ? { replyTo: { email: env.REPLY_TO, name: env.SENDER_NAME } } : {}),
        to: [{ email: dest.email, name: dest.nome || undefined }],
        subject: msg.assunto, htmlContent: msg.html, textContent: msg.texto, tags: [`descrevi-${tipo}`],
      }),
    });
    resposta = `${r.status} ${(await r.text()).slice(0, 300)}`;
  }
  await env.DB.prepare("INSERT INTO outbox (pedido_id,email,tipo,assunto,html,texto,dry_run,resposta,criado_em) VALUES (?,?,?,?,?,?,?,?,?)")
    .bind(dest.id || null, dest.email, tipo, msg.assunto, msg.html, msg.texto, dry ? 1 : 0, resposta, agora()).run();
}

function linkFormulario(env, p) { return `${env.SITE_URL}/formulario.html?t=${p.token}`; }

function pacoteDoProduto(env, prod) {
  const id3 = (env.KIWIFY_PRODUTO_3 || "").trim();
  const id10 = (env.KIWIFY_PRODUTO_10 || "").trim();
  if (id3 && prod === id3) return { pacote: "3", quantidade: 3 };
  if (id10 && prod === id10) return { pacote: "10", quantidade: 10 };
  return null;
}

async function aplicarPedido(env, ev, tipo) {
  const email = normEmail(ev.Customer?.email ?? ev.customer?.email);
  const nome = (ev.Customer?.full_name || ev.Customer?.first_name || ev.customer?.name || "").trim().slice(0, 120);
  const orderId = ev.order_id || null;
  const info = pacoteDoProduto(env, ev.Product?.product_id);
  let p = orderId ? await env.DB.prepare("SELECT * FROM pedidos WHERE order_id=?").bind(orderId).first() : null;
  if (tipo === "order_approved") {
    if (ev.order_status && ev.order_status !== "paid") return `pedido ignorado (order_status=${ev.order_status})`;
    if (!info) return "pedido ignorado (produto desconhecido)";
    if (p && p.status === "reembolsado") return "pedido ignorado (já reembolsado)";
    if (p) return `pedido sem mudança (${p.status})`;
    if (!EMAIL_RE.test(email)) return "ATENÇÃO: compra aprovada sem e-mail válido no payload";
    p = { id: crypto.randomUUID(), email, token: tokenAleatorio(), order_id: orderId, nome, status: "pago", ...info };
    await env.DB.prepare("INSERT INTO pedidos (id,email,nome,order_id,token,pacote,quantidade,status,criado_em,atualizado_em) VALUES (?,?,?,?,?,?,?,?,?,?)")
      .bind(p.id, email, nome || null, orderId, p.token, p.pacote, p.quantidade, "pago", agora(), agora()).run();
    const agoraIso = agora();
    for (let i = 1; i <= p.quantidade; i++) {
      await env.DB.prepare("INSERT INTO itens (id,pedido_id,indice,preenchido,criado_em,atualizado_em) VALUES (?,?,?,?,?,?)")
        .bind(crypto.randomUUID(), p.id, i, 0, agoraIso, agoraIso).run();
    }
    await enviar(env, { id: p.id, email, nome }, "formulario", T.formularioEnvio(env, p, linkFormulario(env, p)));
    return `pedido novo→pago (${p.quantidade} anúncios, e-mail do formulário)`;
  }
  if (!p) return "pedido ignorado (desconhecido)";
  if (tipo === "order_refunded" || tipo === "chargeback") {
    await env.DB.prepare("UPDATE pedidos SET status=?, revogado_em=?, atualizado_em=? WHERE id=?")
      .bind("reembolsado", agora(), agora(), p.id).run();
    return `pedido ${p.status}→reembolsado (link revogado)`;
  }
  return `pedido registrado sem ação (${tipo})`;
}

async function dispararGeracao(env, pedido) {
  const token = env.GITHUB_DISPATCH_TOKEN, repo = env.GITHUB_REPO || "heliovc/descrevi";
  if (!token) return "aguardando_geracao_manual";
  try {
    const r = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
      method: "POST",
      headers: { authorization: `Bearer ${token}`, accept: "application/vnd.github+json", "x-github-api-version": "2022-11-28",
        "content-type": "application/json", "user-agent": "descrevi-intake" },
      body: JSON.stringify({ event_type: "anuncio-gerar", client_payload: { pedido_id: pedido.id, email: pedido.email } }),
    });
    return r.status === 204 ? "disparado" : `falha_dispatch_${r.status}`;
  } catch (_) { return "falha_dispatch"; }
}

async function pedidoPorToken(env, tkn) {
  return tkn && tkn.length >= 32 ? await env.DB.prepare("SELECT * FROM pedidos WHERE token=?").bind(tkn).first() : null;
}

async function pedidoGet(req, env, url) {
  const h = cors(req, env);
  const p = await pedidoPorToken(env, url.searchParams.get("t") || "");
  if (!p) return json({ erro: "link inválido ou expirado" }, 404, h);
  if (p.status === "reembolsado") return json({ erro: "este pedido foi reembolsado; o link não vale mais" }, 410, h);
  const { results: itens } = await env.DB.prepare("SELECT indice,nome_produto,categoria,especificacoes,diferenciais,plataforma,link_referencia,preenchido FROM itens WHERE pedido_id=? ORDER BY indice").bind(p.id).all();
  return json({
    email: p.email, nome: p.nome, pacote: p.pacote, quantidade: p.quantidade,
    status: p.status, preenchidos: (itens || []).filter((i) => i.preenchido).length,
    itens: itens || [],
  }, 200, h);
}

function textoCurto(v, max) { return String(v ?? "").trim().slice(0, max); }

function validarItem(b, erros, prefixo) {
  const nome = textoCurto(b.nome_produto, 200);
  const categoria = textoCurto(b.categoria, 120);
  const especificacoes = textoCurto(b.especificacoes, 4000);
  const diferenciais = textoCurto(b.diferenciais, 2000);
  const plataforma = String(b.plataforma || "ambos").trim().toLowerCase();
  const link = textoCurto(b.link_referencia, 500);
  if (!nome) erros.push(`${prefixo}: informe o nome do produto`);
  if (!categoria) erros.push(`${prefixo}: informe a categoria`);
  if (!especificacoes) erros.push(`${prefixo}: cole as características (medidas, material, o que vem na caixa)`);
  if (!["ml", "shopee", "ambos"].includes(plataforma)) erros.push(`${prefixo}: plataforma inválida`);
  if (link) {
    // Só valida formato. NUNCA faz fetch.
    try {
      const u = new URL(link);
      if (!/^https?:$/i.test(u.protocol)) erros.push(`${prefixo}: o link deve começar com http:// ou https://`);
    } catch {
      erros.push(`${prefixo}: link de referência inválido (é opcional; deixe em branco se não tiver)`);
    }
  }
  return { nome_produto: nome, categoria, especificacoes, diferenciais, plataforma, link_referencia: link || null };
}

async function pedidoEnviar(req, env) {
  const h = cors(req, env);
  let b; try { b = await req.json(); } catch { return json({ erro: "JSON inválido" }, 400, h); }
  const p = await pedidoPorToken(env, String(b.token || b.t || ""));
  if (!p) return json({ erro: "link inválido ou expirado" }, 404, h);
  if (p.status === "reembolsado") return json({ erro: "este pedido foi reembolsado; o link não vale mais" }, 410, h);
  if (p.status === "enviado") return json({ erro: "este pedido já foi entregue" }, 409, h);
  if (p.status === "em_geracao") return json({ ok: true, status: p.status, detalhe: "já em geração" }, 200, h);
  const lista = Array.isArray(b.itens) ? b.itens : [b];
  const erros = [];
  if (!b.consentimento) erros.push("é preciso concordar com o uso dos dados para montar o material (LGPD)");
  const porIndice = new Map();
  for (const it of lista) {
    const indice = Number(it.indice);
    if (!Number.isInteger(indice) || indice < 1 || indice > p.quantidade) {
      erros.push(`índice inválido: ${it.indice}`);
      continue;
    }
    porIndice.set(indice, validarItem(it, erros, `produto ${indice}`));
  }
  if (erros.length) return json({ erro: "dados incompletos", detalhes: erros }, 422, h);
  const agoraIso = agora();
  for (const [indice, d] of porIndice) {
    await env.DB.prepare(`UPDATE itens SET nome_produto=?, categoria=?, especificacoes=?, diferenciais=?, plataforma=?, link_referencia=?, preenchido=1, atualizado_em=?
      WHERE pedido_id=? AND indice=?`)
      .bind(d.nome_produto, d.categoria, d.especificacoes, d.diferenciais, d.plataforma, d.link_referencia, agoraIso, p.id, indice).run();
  }
  const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM itens WHERE pedido_id=? AND preenchido=1").bind(p.id).first();
  const preenchidos = row?.n || 0;
  let status = p.status;
  let dispatch = null;
  if (preenchidos >= p.quantidade) {
    status = "recebido";
    await env.DB.prepare("UPDATE pedidos SET status=?, recebido_em=?, atualizado_em=? WHERE id=?")
      .bind(status, agoraIso, agoraIso, p.id).run();
    dispatch = await dispararGeracao(env, p);
    await env.DB.prepare("UPDATE pedidos SET status=?, detalhe=?, atualizado_em=? WHERE id=?")
      .bind(dispatch === "disparado" ? "em_geracao" : "recebido", dispatch, agora(), p.id).run();
    if (dispatch === "disparado") status = "em_geracao";
  } else {
    await env.DB.prepare("UPDATE pedidos SET atualizado_em=? WHERE id=?").bind(agoraIso, p.id).run();
  }
  return json({ ok: true, status, preenchidos, quantidade: p.quantidade, dispatch }, 200, h);
}

async function internoPedido(req, env, url) {
  if (!autorizado(req, env)) return json({ erro: "não autorizado" }, 401);
  const id = url.searchParams.get("id") || "";
  const p = id ? await env.DB.prepare("SELECT * FROM pedidos WHERE id=?").bind(id).first() : null;
  if (!p) return json({ erro: "pedido não encontrado" }, 404);
  if (p.status === "reembolsado") return json({ erro: "reembolsado" }, 410);
  const { results: itens } = await env.DB.prepare("SELECT * FROM itens WHERE pedido_id=? ORDER BY indice").bind(p.id).all();
  return json({ pedido: p, itens: itens || [] });
}

async function internoStatus(req, env) {
  if (!autorizado(req, env)) return json({ erro: "não autorizado" }, 401);
  let b; try { b = await req.json(); } catch { return json({ erro: "JSON inválido" }, 400); }
  const id = String(b.pedido_id || ""), status = String(b.status || "");
  if (!id || !["enviado", "falhou", "em_geracao"].includes(status)) return json({ erro: "pedido_id ou status inválido" }, 422);
  const p = await env.DB.prepare("SELECT * FROM pedidos WHERE id=?").bind(id).first();
  if (!p) return json({ erro: "pedido não encontrado" }, 404);
  if (p.status === "reembolsado") return json({ ok: true, ignorado: "reembolsado" }, 200);
  if (p.status === status) return json({ ok: true, status, duplicado: true }, 200);
  const enviado = status === "enviado" ? agora() : p.enviado_em;
  await env.DB.prepare("UPDATE pedidos SET status=?, detalhe=?, enviado_em=?, atualizado_em=? WHERE id=?")
    .bind(status, String(b.detalhe || "").slice(0, 1000), enviado, agora(), id).run();
  if (status === "falhou") {
    let motivo = "";
    try { motivo = JSON.parse(b.detalhe || "{}").erro || ""; } catch (_) { motivo = String(b.detalhe || ""); }
    await enviar(env, { id: p.id, email: p.email, nome: p.nome }, "falhou", T.geracaoFalhou(env, p, motivo.slice(0, 300)));
  }
  return json({ ok: true, status }, 200);
}

function mascararEmail(e) {
  const s = String(e || "");
  const i = s.indexOf("@");
  if (i < 1) return "***";
  return `${s[0]}***${s.slice(i)}`;
}
function queryMascarada(url) {
  const q = new URLSearchParams(url.search);
  if (q.has("signature")) q.set("signature", (q.get("signature") || "").slice(0, 6) + "…");
  return q.toString();
}
function resumoSeguro(raw) {
  let ev = null;
  try { ev = JSON.parse(new TextDecoder().decode(raw)); } catch { ev = null; }
  const resumo = ev ? {
    webhook_event_type: ev.webhook_event_type ?? null,
    order_id: ev.order_id ?? null,
    order_status: ev.order_status ?? null,
    product_id: ev.Product?.product_id ?? null,
    customer_email: mascararEmail(ev.Customer?.email),
  } : { raw_bytes: raw.length };
  return { ev, resumo: JSON.stringify(resumo) };
}
async function logWebhook(env, row) {
  try {
    await env.DB.prepare("INSERT INTO webhook_log (ts,path,query,content_type,status,resultado,body_excerpt,webhook_event_type,order_id,product_id) VALUES (?,?,?,?,?,?,?,?,?,?)")
      .bind(agora(), row.path || "", row.query || "", row.contentType || "", row.status ?? null, (row.resultado || "").slice(0, 2000),
        (row.bodyExcerpt || "").slice(0, 1500), row.eventType || null, row.orderId || null, row.productId || null).run();
  } catch (_) {}
}

async function kiwify(req, env, url) {
  const raw = new Uint8Array(await req.arrayBuffer());
  const meta = { path: url.pathname, query: queryMascarada(url), contentType: req.headers.get("content-type") || "" };
  { const { ev, resumo } = resumoSeguro(raw);
    Object.assign(meta, { eventType: ev?.webhook_event_type, orderId: ev?.order_id, productId: ev?.Product?.product_id, bodyExcerpt: resumo }); }
  const responder = async (resp) => {
    let resultado = "";
    try { resultado = (await resp.clone().text()).slice(0, 2000); } catch (_) {}
    await logWebhook(env, { ...meta, status: resp.status, resultado });
    return resp;
  };
  try {
    const sig = (url.searchParams.get("signature") || "").toLowerCase();
    const tokens = [env.KIWIFY_TOKEN, env.KIWIFY_TOKEN_ANTIGO].filter(Boolean);
    if (!tokens.length) return await responder(json({ erro: "KIWIFY_TOKEN não configurado" }, 500));
    let valido = false;
    for (const t of tokens) if (igualConstante(await hmacHex("SHA-1", t, raw), sig)) valido = true;
    if (!valido) return await responder(json({ erro: "assinatura inválida" }, 401));
    let ev;
    try { ev = JSON.parse(new TextDecoder().decode(raw)); } catch { return await responder(json({ erro: "JSON inválido" }, 400)); }
    const tipo = ev.webhook_event_type;
    if (!tipo) return await responder(json({ ok: true, ignorado: "sem webhook_event_type" }));
    const prod = ev.Product?.product_id;
    const conhecidos = [env.KIWIFY_PRODUTO_3, env.KIWIFY_PRODUTO_10].map((s) => (s || "").trim()).filter(Boolean);
    if (conhecidos.length && prod && !conhecidos.includes(prod)) return await responder(json({ ok: true, ignorado: "outro produto" }));
    const chave = `${ev.order_id || "sem-order"}|${tipo}`;
    const ins = await env.DB.prepare("INSERT OR IGNORE INTO eventos (chave,tipo,order_id,recebido_em) VALUES (?,?,?,?)")
      .bind(chave, tipo, ev.order_id || null, agora()).run();
    if (!ins.meta.changes) {
      const r = await env.DB.prepare("SELECT resultado FROM eventos WHERE chave=?").bind(chave).first();
      return await responder(json({ ok: true, duplicado: true, resultado: r?.resultado }));
    }
    try {
      const resultado = await aplicarPedido(env, ev, tipo);
      const ped = ev.order_id ? await env.DB.prepare("SELECT id FROM pedidos WHERE order_id=?").bind(ev.order_id).first() : null;
      await env.DB.prepare("UPDATE eventos SET resultado=?, pedido_id=? WHERE chave=?").bind(resultado, ped?.id || null, chave).run();
      return await responder(json({ ok: true, resultado }));
    } catch (e) {
      await env.DB.prepare("DELETE FROM eventos WHERE chave=?").bind(chave).run();
      return await responder(json({ erro: String(e.message || e) }, 500));
    }
  } catch (_) {
    return await responder(json({ erro: "erro interno" }, 500));
  }
}

function ipDe(req) {
  return (req.headers.get("cf-connecting-ip") || req.headers.get("x-forwarded-for") || "").split(",")[0].trim();
}
async function hashIp(env, ip) {
  const sal = env.LINK_SECRET || "descrevi";
  const buf = await crypto.subtle.digest("SHA-256", enc.encode(`${sal}:${ip || "sem-ip"}`));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function verificarTurnstile(env, token, ip) {
  if ((env.TURNSTILE_SECRET || "") === "local-skip") return true;
  if (!env.TURNSTILE_SECRET || !token) return false;
  const body = new URLSearchParams({ secret: env.TURNSTILE_SECRET, response: token });
  if (ip) body.set("remoteip", ip);
  try {
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body });
    const j = await r.json();
    return !!j.success;
  } catch (_) { return false; }
}

const PROIBIDOS_TITULO = /\b(estoque|frete\s*gr[aá]tis|promo[cç][aã]o|oferta|desconto|parcelamento|devolu[cç][aã]o|whatsapp|whats\s*app|\bzap\b|instagram|telefone|celular|e-?mail|mais\s+vendid[oa]s?|best\s*seller|n[uú]mero\s*1|l[ií]der\s+de\s+vendas)\b/i;

function montarTituloLocal(b) {
  const partes = [b.nome_produto, b.marca, b.especificacoes, b.diferenciais]
    .map((s) => String(s || "").replace(/[\n\r]+/g, " ").trim()).filter(Boolean);
  let t = partes.join(" ");
  t = t.replace(/[^\p{L}\p{N}\s×x/\-]/gu, " ");
  t = t.replace(PROIBIDOS_TITULO, " ");
  t = t.replace(/\s+/g, " ").trim();
  // Evita CAIXA ALTA no título inteiro
  if (t && t === t.toUpperCase()) t = t.toLowerCase().replace(/(^|\s)\S/g, (m) => m.toUpperCase());
  if (t.length > 60) t = t.slice(0, 60).replace(/\s+\S*$/, "").trim();
  return t.slice(0, 60);
}

async function tituloGratis(req, env) {
  const h = cors(req, env);
  let b; try { b = await req.json(); } catch { return json({ erro: "JSON inválido" }, 400, h); }
  const ip = ipDe(req);
  const token = String(b.turnstile || b["cf-turnstile-response"] || b.token_turnstile || "");
  if (!(await verificarTurnstile(env, token, ip))) return json({ erro: "não foi possível verificar que você não é um robô; recarregue e tente de novo" }, 403, h);
  const nome = textoCurto(b.nome_produto || b.nome, 200);
  const especificacoes = textoCurto(b.especificacoes, 1000);
  if (!nome) return json({ erro: "informe o nome do produto" }, 422, h);
  const dia = new Date().toISOString().slice(0, 10);
  const iph = await hashIp(env, ip);
  const teto = Number(env.TITULO_TETO || 80);
  const porIp = 3;
  const glob = await env.DB.prepare("SELECT COUNT(*) AS n FROM titulos_gratis WHERE dia=?").bind(dia).first();
  if ((glob?.n || 0) >= teto) return json({ erro: "o limite diário do gerador grátis foi atingido. Tente amanhã, ou conheça o pacote Anúncio Pronto." }, 429, h);
  const doIp = await env.DB.prepare("SELECT COUNT(*) AS n FROM titulos_gratis WHERE dia=? AND ip_hash=?").bind(dia, iph).first();
  if ((doIp?.n || 0) >= porIp) return json({ erro: "você já usou as 3 gerações grátis de hoje. O pacote Anúncio Pronto entrega o anúncio completo." }, 429, h);
  // Reserva o uso ANTES de gerar (evita estouro em cliques simultâneos).
  await env.DB.prepare("INSERT INTO titulos_gratis (dia,ip_hash,criado_em) VALUES (?,?,?)").bind(dia, iph, agora()).run();
  const usadosIp = (doIp?.n || 0) + 1;
  let titulo = "", fonte = "local";
  if (env.GEMINI_API_KEY) {
    try {
      const prompt = `Escreva 1 título de anúncio para o Mercado Livre, em português do Brasil.
Regras obrigatórias:
- No máximo 60 caracteres (conte todos, inclusive espaços).
- Estrutura: Produto + Marca + modelo + especificações que identifiquem o produto.
- Não use a palavra "estoque". Não mencione frete, parcelamento, devolução, promoção, oferta, desconto, "novo"/"usado".
- Sem pontuação ou símbolos; separe palavras com espaço. Sem emoji. Sem CAIXA ALTA no título inteiro. Mantenha acentos do português (é, ç, ã); acento não é símbolo.
- Sem telefone, e-mail, WhatsApp, site ou redes. Sem "mais vendido" ou promessa de posição/vendas.
- Marca de terceiro só com "para" ou "compatível com".
- Use SOMENTE os dados abaixo. Não invente medida, material, marca ou modelo.
Produto: ${nome}
Categoria: ${textoCurto(b.categoria, 120)}
Especificações: ${especificacoes}
Diferenciais: ${textoCurto(b.diferenciais, 500)}
Responda só o título, sem aspas.`;
      const r = await fetch("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent", {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
        body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { temperature: 0.3, maxOutputTokens: 80 } }),
      });
      if (r.ok) {
        const j = await r.json();
        const partes = (((j.candidates || [])[0] || {}).content || {}).parts || [];
        titulo = partes.map((p) => p.text || "").join("").replace(/[\n\r]+/g, " ").replace(/^["'“”]+|["'“”]+$/g, "").trim();
        fonte = "gemini";
      }
    } catch (_) { titulo = ""; }
  }
  if (!titulo) titulo = montarTituloLocal({ nome_produto: nome, marca: b.marca, especificacoes, diferenciais: b.diferenciais });
  if (titulo.length > 60) titulo = titulo.slice(0, 60).replace(/\s+\S*$/, "").trim();
  if (!titulo) return json({ erro: "não foi possível montar um título com esses dados" }, 422, h);
  return json({
    ok: true, titulo, caracteres: titulo.length, limite: 60, fonte,
    restantes_hoje: Math.max(0, porIp - usadosIp),
    aviso: "Revise antes de publicar. Este é só um título, gerado a partir dos dados que você colou. Não garante vendas nem posição na busca.",
  }, 200, h);
}

async function adminOutbox(req, env, url) {
  if (!autorizado(req, env)) return json({ erro: "não autorizado" }, 401);
  const n = Math.min(50, Number(url.searchParams.get("n") || 20));
  const { results } = await env.DB.prepare("SELECT id,pedido_id,email,tipo,assunto,dry_run,resposta,criado_em FROM outbox ORDER BY id DESC LIMIT ?").bind(n).all();
  return json({ outbox: (results || []).map((r) => ({ ...r, email: mascararEmail(r.email) })) });
}

export async function rotina(env) {
  const corte = new Date(Date.now() - 24 * 36e5).toISOString();
  const corteRep = new Date(Date.now() - 72 * 36e5).toISOString();
  let lembretes = 0;
  try {
    const { results } = await env.DB.prepare(`SELECT * FROM pedidos WHERE status='pago'
      AND criado_em <= ? AND lembretes < 3 AND (ultimo_lembrete IS NULL OR ultimo_lembrete <= ?) LIMIT 20`).bind(corte, corteRep).all();
    for (const p of results || []) {
      await enviar(env, { id: p.id, email: p.email, nome: p.nome }, "lembrete", T.lembreteFormulario(env, p, linkFormulario(env, p), p.lembretes + 1));
      await env.DB.prepare("UPDATE pedidos SET lembretes=?, ultimo_lembrete=?, atualizado_em=? WHERE id=?")
        .bind(p.lembretes + 1, agora(), agora(), p.id).run();
      lembretes++;
    }
  } catch (_) {}
  const limite = new Date(Date.now() - 30 * 864e5).toISOString();
  const out = await env.DB.prepare("DELETE FROM outbox WHERE criado_em < ?").bind(limite).run();
  try { await env.DB.prepare("DELETE FROM webhook_log WHERE ts < ?").bind(limite).run(); } catch (_) {}
  try { await env.DB.prepare("DELETE FROM titulos_gratis WHERE criado_em < ?").bind(limite).run(); } catch (_) {}
  let itensApagados = 0, pedidosApagados = 0;
  try {
    const velhos = await env.DB.prepare("SELECT id FROM pedidos WHERE criado_em < ?").bind(limite).all();
    const ids = (velhos.results || []).map((r) => r.id);
    for (const id of ids) {
      const a = await env.DB.prepare("DELETE FROM itens WHERE pedido_id=?").bind(id).run();
      itensApagados += a.meta.changes;
    }
    const p = await env.DB.prepare("DELETE FROM pedidos WHERE criado_em < ?").bind(limite).run();
    pedidosApagados = p.meta.changes;
  } catch (_) {}
  return { lembretes, outbox_apagados: out.meta.changes, pedidos_apagados: pedidosApagados, itens_apagados: itensApagados };
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url), p = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(req, env) });
      if (p === "/kiwify" && req.method === "POST") return await kiwify(req, env, url);
      if (p === "/pedido" && req.method === "GET") return await pedidoGet(req, env, url);
      if (p === "/pedido/enviar" && req.method === "POST") return await pedidoEnviar(req, env);
      if (p === "/titulo-gratis" && req.method === "POST") return await tituloGratis(req, env);
      if (p === "/interno/pedido" && req.method === "GET") return await internoPedido(req, env, url);
      if (p === "/interno/status" && req.method === "POST") return await internoStatus(req, env);
      if (p === "/admin/outbox" && req.method === "GET") return await adminOutbox(req, env, url);
      if (p === "/admin/rotina" && req.method === "POST") {
        if (!autorizado(req, env)) return json({ erro: "não autorizado" }, 401);
        return json(await rotina(env));
      }
      if (p === "/") return json({ ok: true, servico: "descrevi-intake" });
      return json({ erro: "não encontrado" }, 404);
    } catch (e) {
      return json({ erro: "erro interno" }, 500);
    }
  },
  async scheduled(_ev, env, ctx) { ctx.waitUntil(rotina(env)); },
};
