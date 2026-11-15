// E-mails e páginas simples do Worker da Descrevi (pacote Anúncio Pronto).
const C = { bg: "#eef4f1", card: "#ffffff", ink: "#12241d", muted: "#5b675f", accent: "#1a4a3c", line: "#d5e0da", head: "#1a4a3c", warn_bg: "#fef3e2", warn: "#8a4b08" };
const FONT = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;";
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function botao(href, rotulo) {
  return `<a href="${esc(href)}" style="display:inline-block;${FONT}font-size:16px;font-weight:700;color:#ffffff;background:${C.accent};border-radius:8px;padding:13px 22px;text-decoration:none;">${esc(rotulo)}</a>`;
}

function moldura(env, preheader, corpo, motivo) {
  const produto = esc(env.SENDER_NAME || "Descrevi");
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${produto}</title></head><body style="margin:0;padding:0;background:${C.bg};">
<div style="display:none;max-height:0;overflow:hidden;">${esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${C.bg};"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:${C.card};border-radius:10px;overflow:hidden;border:1px solid ${C.line};">
<tr><td style="background:${C.head};padding:18px 24px;${FONT}font-size:20px;font-weight:800;color:#ffffff;">${produto}</td></tr>
<tr><td style="padding:26px 24px 8px 24px;${FONT}font-size:15px;line-height:23px;color:${C.ink};">${corpo}</td></tr>
<tr><td style="padding:16px 24px 24px 24px;border-top:1px solid ${C.line};${FONT}font-size:12px;line-height:18px;color:${C.muted};">
Você recebe este e-mail porque ${motivo ? esc(motivo) : "comprou o pacote Anúncio Pronto, da Descrevi"}. Dúvidas: responda este e-mail ou escreva para ${esc(env.SUPORTE_EMAIL)}.<br>
A Descrevi entrega o texto e o roteiro de fotos a partir dos dados que você envia. Não publicamos no seu lugar, não pedimos senha e não garantimos vendas nem posição na busca.<br>
<a href="${esc(env.SITE_URL)}/privacidade.html" style="color:${C.muted};">Política de privacidade</a> · <a href="${esc(env.SITE_URL)}/termos.html" style="color:${C.muted};">Termos de uso</a><br>
${esc(env.ENDERECO_REMETENTE || "")}
</td></tr></table></td></tr></table></body></html>`;
}

export function formularioEnvio(env, p, link) {
  const n = p.quantidade;
  const assunto = `Anúncio Pronto: preencha o formulário dos seus ${n} anúncio${n > 1 ? "s" : ""}`;
  const corpo = `<p style="margin:0 0 14px 0;font-size:20px;line-height:27px;font-weight:800;">Pagamento confirmado</p>
<p style="margin:0 0 12px 0;">Você comprou o pacote Anúncio Pronto (${n} anúncio${n > 1 ? "s" : ""}). Agora cole os dados de cada produto no formulário. O link do anúncio atual é opcional e serve só como referência — não acessamos a página.</p>
<p style="margin:0 0 22px 0;">${botao(link, "Preencher o formulário")}</p>
<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">O link é pessoal; não compartilhe. Se o botão não abrir, copie: ${esc(link)}</p>
<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">Assim que recebermos os ${n} produto${n > 1 ? "s" : ""}, preparamos o material e enviamos por e-mail em até 24 horas. Garantia de 7 dias pela Kiwify.</p>`;
  const texto = `Pagamento confirmado.\n\nPreencha o formulário dos seus ${n} anúncio(s) (link pessoal):\n${link}\n\nO link do anúncio, se você informar, é só referência — não acessamos a página.\nDúvidas: ${env.SUPORTE_EMAIL}`;
  return { assunto, html: moldura(env, "Cole os dados de cada produto para receber o anúncio pronto.", corpo, "comprou o pacote Anúncio Pronto, da Descrevi"), texto };
}

export function lembreteFormulario(env, p, link, n) {
  const assunto = n > 1 ? "Ainda falta preencher o formulário do Anúncio Pronto" : "Lembrete: falta o formulário do seu Anúncio Pronto";
  const corpo = `<p style="margin:0 0 14px 0;font-size:19px;line-height:26px;font-weight:800;">Ainda não recebemos os dados dos produtos</p>
<p style="margin:0 0 12px 0;">Sua compra está confirmada, mas o material só é montado depois que você cola as informações de cada produto.</p>
<p style="margin:0 0 22px 0;">${botao(link, "Preencher o formulário")}</p>
<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">Se o botão não abrir, copie: ${esc(link)}</p>`;
  return { assunto, html: moldura(env, "Falta preencher o formulário para montarmos o anúncio.", corpo), texto: `Ainda falta preencher o formulário: ${link}` };
}

export function entregaPronta(env, p, resumo) {
  const n = p.quantidade;
  const assunto = `Seu Anúncio Pronto (${n} anúncio${n > 1 ? "s" : ""}) está no anexo`;
  const corpo = `<p style="margin:0 0 14px 0;font-size:20px;line-height:27px;font-weight:800;">Material pronto para colar</p>
<p style="margin:0 0 12px 0;">Segue o pacote Anúncio Pronto em PDF e planilha (xlsx e CSV). Use os textos nos campos do Mercado Livre e da Shopee. Revise antes de publicar: o texto usa só o que você enviou no formulário.</p>
${resumo ? `<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">${esc(resumo)}</p>` : ""}
<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">Não publicamos no seu lugar e não pedimos senha. Não há garantia de vendas nem de posição na busca — isso depende de preço, estoque, reputação, frete e fotos.</p>`;
  const texto = `Seu Anúncio Pronto está no anexo (PDF, planilha e CSV).\n\nRevise antes de publicar. Dúvidas: ${env.SUPORTE_EMAIL}`;
  return { assunto, html: moldura(env, "PDF e planilha com títulos, descrição, ficha, perguntas e roteiro de fotos.", corpo), texto };
}

export function geracaoFalhou(env, p, motivo) {
  const assunto = "Não conseguimos concluir o seu Anúncio Pronto — já estamos vendo";
  const corpo = `<p style="margin:0 0 14px 0;font-size:19px;line-height:26px;font-weight:800;">Houve um problema na geração</p>
<p style="margin:0 0 12px 0;">Não foi possível montar o material automaticamente. Vamos revisar o pedido. Se preferir, responda este e-mail ou escreva para ${esc(env.SUPORTE_EMAIL)}.</p>
${motivo ? `<p style="margin:0 0 12px 0;font-size:13px;color:${C.muted};">Detalhe técnico: ${esc(motivo)}</p>` : ""}`;
  return { assunto, html: moldura(env, "Houve um problema ao montar o material. Já vamos olhar.", corpo), texto: `Houve um problema ao montar o material. Contato: ${env.SUPORTE_EMAIL}` };
}

export function pagina(titulo, corpoHtml) {
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>${esc(titulo)} · Descrevi</title>
<style>body{margin:0;background:${C.bg};${FONT}color:${C.ink}}main{max-width:520px;margin:48px auto;background:#fff;border:1px solid ${C.line};border-radius:10px;padding:28px}
h1{font-size:22px;margin:0 0 12px}p{line-height:1.55}button,a.b{display:inline-block;background:${C.accent};color:#fff;border:0;border-radius:8px;padding:12px 20px;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none}
.m{color:${C.muted};font-size:14px}</style></head><body><main>${corpoHtml}</main></body></html>`;
}
