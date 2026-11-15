"""PDF do pacote Anúncio Pronto, da Descrevi."""
from __future__ import annotations
import html
from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable, ListFlowable, ListItem, PageBreak,
)

FONTS = Path(__file__).resolve().parent / "fonts"
FOREST = HexColor("#1a4a3c")
FOREST2 = HexColor("#12352c")
FOREST_SOFT = HexColor("#e4efe9")
INK = HexColor("#1a221c")
INK_SOFT = HexColor("#3d4a43")
MUTED = HexColor("#5b675f")
LINE = HexColor("#d5cdbe")
PAPER = HexColor("#f3eee4")
CARD = HexColor("#fffdf8")
WARN_BG = HexColor("#f7eadc")
WARN = HexColor("#7a3e12")

DISCLAIMER = (
    "Material gerado pela Descrevi (pacote Anúncio Pronto) a partir dos dados que você colou no formulário. "
    "Revise antes de publicar. Não inventamos característica: se algo importante faltou, isso aparece em “Itens para você confirmar”, com o marcador [confirmar: …]. "
    "A Descrevi não publica no seu lugar, não pede senha e não garante vendas nem posição na busca — isso depende de preço, estoque, reputação, frete e fotos. "
    "O link do anúncio, se você informou, entra só como referência e não foi acessado."
)


def _fonts():
    if getattr(_fonts, "_ok", False):
        return
    pdfmetrics.registerFont(TTFont("SourceSans", str(FONTS / "SourceSansPro-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("SourceSans-Bold", str(FONTS / "SourceSansPro-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("SourceSans-Semi", str(FONTS / "SourceSansPro-Semibold.ttf")))
    pdfmetrics.registerFont(TTFont("SourceSans-It", str(FONTS / "SourceSansPro-It.ttf")))
    pdfmetrics.registerFontFamily(
        "SourceSans", normal="SourceSans", bold="SourceSans-Bold",
        italic="SourceSans-It", boldItalic="SourceSans-Bold",
    )
    _fonts._ok = True


def E(s) -> str:
    return html.escape(str(s or ""), quote=False).replace("\n", "<br/>")


def estilos():
    _fonts()
    S = {}
    S["h1"] = ParagraphStyle("h1", fontName="SourceSans-Bold", fontSize=22, leading=26, textColor=FOREST, spaceAfter=6)
    S["h2"] = ParagraphStyle("h2", fontName="SourceSans-Semi", fontSize=14, leading=18, textColor=FOREST, spaceBefore=10, spaceAfter=4)
    S["h3"] = ParagraphStyle("h3", fontName="SourceSans-Semi", fontSize=11.5, leading=15, textColor=FOREST2, spaceBefore=6, spaceAfter=3)
    S["corpo"] = ParagraphStyle("corpo", fontName="SourceSans", fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY)
    S["corpo_l"] = ParagraphStyle("corpo_l", fontName="SourceSans", fontSize=10, leading=14, textColor=INK, alignment=TA_LEFT)
    S["titulo"] = ParagraphStyle("titulo", fontName="SourceSans-Semi", fontSize=11, leading=15, textColor=INK)
    S["muted"] = ParagraphStyle("muted", fontName="SourceSans", fontSize=8.5, leading=12, textColor=MUTED)
    S["aviso"] = ParagraphStyle("aviso", fontName="SourceSans", fontSize=9, leading=13, textColor=WARN)
    S["kicker"] = ParagraphStyle("kicker", fontName="SourceSans-Semi", fontSize=8, leading=11, textColor=FOREST, tracking=0.6)
    S["rodape"] = ParagraphStyle("rodape", fontName="SourceSans", fontSize=7.5, leading=10, textColor=MUTED, alignment=TA_CENTER)
    S["centro"] = ParagraphStyle("centro", fontName="SourceSans", fontSize=10, leading=14, textColor=INK, alignment=TA_CENTER)
    return S


def _cabecalho_rodape(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(FOREST)
    canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("SourceSans-Semi", 9)
    canvas.drawString(18 * mm, A4[1] - 9 * mm, "Descrevi  ·  Anúncio Pronto")
    canvas.setFont("SourceSans", 8)
    canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 9 * mm, f"{doc.page}")
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, A4[0], 14 * mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("SourceSans", 7)
    canvas.drawCentredString(A4[0] / 2, 7 * mm, "Revise antes de publicar. Sem garantia de vendas ou posição na busca.")
    canvas.restoreState()


def _tabela(linhas, colunas, larguras):
    data = [colunas] + linhas
    t = Table(data, colWidths=larguras, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "SourceSans-Semi"),
        ("FONTNAME", (0, 1), (-1, -1), "SourceSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), FOREST),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("BACKGROUND", (0, 1), (-1, -1), CARD),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
    ]))
    return t


def _email_suporte() -> str:
    import json
    cfg = Path(__file__).resolve().parent.parent / "config.json"
    if cfg.exists():
        return ((json.loads(cfg.read_text()) or {}).get("remetente") or {}).get("suporte") or ""
    return ""


def _confirmacoes(anuncio: dict) -> list[str]:
    from gerador.checagem import listar_confirmacoes
    lista = list(anuncio.get("confirmacoes") or listar_confirmacoes(anuncio))
    # inclui pendências que ainda não estejam representadas
    ja = set(s.lower() for s in lista)
    for p in anuncio.get("pendencias") or []:
        txt = str(p).strip()
        if txt and txt.lower() not in ja and not any(txt.lower() in x.lower() or x.lower() in txt.lower() for x in lista):
            lista.append(txt)
            ja.add(txt.lower())
    avisos = [c["mensagem"] for c in (anuncio.get("_checagens") or []) if c.get("nivel") == "aviso"]
    for a in avisos:
        if a.lower() not in ja:
            lista.append(a)
            ja.add(a.lower())
    return lista


def _bloco_produto(S, item, anuncio, idx, total):
    from gerador.checagem import montar_descricao_corrida, ML_TITULO, SHOPEE_TITULO
    flow = []
    flow.append(Paragraph(f"ANÚNCIO {idx} DE {total}", S["kicker"]))
    flow.append(Paragraph(E(item.get("nome_produto") or "Produto"), S["h1"]))
    meta = []
    if item.get("categoria"):
        meta.append(f"Categoria: {item['categoria']}")
    plat = {"ml": "Mercado Livre", "shopee": "Shopee", "ambos": "Mercado Livre e Shopee"}.get(item.get("plataforma") or "ambos", item.get("plataforma") or "")
    if plat:
        meta.append(f"Destino: {plat}")
    if item.get("link_referencia"):
        meta.append(f"Link informado (só referência, não acessado): {item['link_referencia']}")
    if meta:
        flow.append(Paragraph(E(" · ".join(meta)), S["muted"]))
    confs = _confirmacoes(anuncio)
    if confs:
        flow.append(Paragraph("Itens para você confirmar", S["h2"]))
        flow.append(Paragraph("O gerador não inventou estes dados. Complete ou confirme antes de publicar.", S["muted"]))
        for c in confs:
            rotulo = c if c.lower().startswith("[confirmar:") else f"[confirmar: {c}]"
            flow.append(Paragraph(f"• {E(rotulo)}", S["aviso"]))
    flow.append(Spacer(1, 4 * mm))

    if (item.get("plataforma") or "ambos") in ("ml", "ambos"):
        flow.append(Paragraph("Títulos para o Mercado Livre (até 60 caracteres)", S["h2"]))
        linhas = []
        for i, t in enumerate(anuncio.get("titulos_ml") or [], 1):
            txt = (t.get("texto") or "").strip()
            enf = t.get("enfoque") or ""
            linhas.append([
                Paragraph(str(i), S["corpo_l"]),
                Paragraph(E(txt), S["titulo"]),
                Paragraph(f"{len(txt)}/{ML_TITULO}", S["muted"]),
                Paragraph(E(enf), S["muted"]),
            ])
        if linhas:
            flow.append(_tabela(linhas, [
                Paragraph("#", S["muted"]), Paragraph("Título", S["muted"]),
                Paragraph("Caracteres", S["muted"]), Paragraph("Enfoque", S["muted"]),
            ], [12 * mm, 105 * mm, 22 * mm, 35 * mm]))

    if (item.get("plataforma") or "ambos") in ("shopee", "ambos"):
        flow.append(Paragraph("Título para a Shopee (até 120 caracteres)", S["h2"]))
        ts = (anuncio.get("titulo_shopee") or {}).get("texto") or ""
        flow.append(Paragraph(E(ts), S["titulo"]))
        flow.append(Paragraph(f"{len(ts)}/{SHOPEE_TITULO} caracteres.", S["muted"]))

    flow.append(Paragraph("Descrição (texto puro, pronta para colar)", S["h2"]))
    desc = montar_descricao_corrida(anuncio.get("descricao") or {})
    flow.append(Paragraph(E(desc) or "—", S["corpo_l"]))

    flow.append(Paragraph("Ficha técnica", S["h2"]))
    ficha = anuncio.get("ficha_tecnica") or []
    if ficha:
        flinhas = []
        for par in ficha:
            flinhas.append([
                Paragraph(E(par.get("caracteristica")), S["corpo_l"]),
                Paragraph(E(par.get("valor")), S["corpo_l"]),
            ])
        flow.append(_tabela(flinhas, [Paragraph("Característica", S["muted"]), Paragraph("Valor", S["muted"])], [70 * mm, 104 * mm]))
    else:
        flow.append(Paragraph("Nenhum par característica/valor pôde ser montado com os dados enviados.", S["aviso"]))

    flow.append(Paragraph("Perguntas e respostas", S["h2"]))
    for i, p in enumerate(anuncio.get("perguntas") or [], 1):
        flow.append(Paragraph(f"<b>{i}. {E(p.get('pergunta'))}</b>", S["corpo_l"]))
        flow.append(Paragraph(E(p.get("resposta")), S["corpo_l"]))
        flow.append(Spacer(1, 1.5 * mm))

    flow.append(Paragraph("Roteiro de 8 fotos", S["h2"]))
    flow.append(Paragraph("A Descrevi não tira as fotos: este é o roteiro para você ou o seu fotógrafo.", S["muted"]))
    rlinhas = []
    for f in sorted(anuncio.get("roteiro_fotos") or [], key=lambda x: x.get("ordem") or 0):
        rlinhas.append([
            Paragraph(str(f.get("ordem") or ""), S["corpo_l"]),
            Paragraph(E(f.get("o_que_mostrar")), S["corpo_l"]),
            Paragraph(E(f.get("dica")), S["muted"]),
        ])
    if rlinhas:
        flow.append(_tabela(rlinhas, [
            Paragraph("#", S["muted"]), Paragraph("O que mostrar", S["muted"]), Paragraph("Dica", S["muted"]),
        ], [12 * mm, 100 * mm, 62 * mm]))

    if anuncio.get("observacoes"):
        flow.append(Paragraph("Observações", S["h3"]))
        flow.append(Paragraph(E(anuncio["observacoes"]), S["muted"]))
    return flow


def renderizar(pedido: dict, itens_gerados: list[dict], destino: Path) -> Path:
    _fonts()
    S = estilos()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(destino), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title="Anúncio Pronto · Descrevi", author="Descrevi",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="a4", frames=frame, onPage=_cabecalho_rodape)])

    story = []
    story.append(Paragraph("DESCREVI", S["kicker"]))
    story.append(Paragraph("Anúncio Pronto", S["h1"]))
    q = pedido.get("quantidade") or len(itens_gerados)
    story.append(Paragraph(f"Pacote com {q} anúncio{'s' if q != 1 else ''}.", S["corpo"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(DISCLAIMER, S["aviso"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Limites usados nesta entrega: título do Mercado Livre com até 60 caracteres (max_title_length da categoria, conferido na API pública). "
        "Título da Shopee com até 120 caracteres. "
        "Descrição da Shopee checada contra 5.000 caracteres (fonte conservadora). "
        "Regras de “estoque”, marcas de terceiro e keyword spam vêm da documentação oficial citada em nosso material interno.",
        S["muted"],
    ))

    total = len(itens_gerados)
    for i, bloco in enumerate(itens_gerados, 1):
        if i > 1:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 6 * mm))
        story.extend(_bloco_produto(S, bloco["item"], bloco["anuncio"], i, total))

    story.append(PageBreak())
    story.append(Paragraph("Como usar este material", S["h1"]))
    story.append(Paragraph(
        "1. Copie uma das opções de título do Mercado Livre para o campo de título (conte o limite no painel, que pode variar por categoria).<br/>"
        "2. Copie o título da Shopee no nome do produto. Confira o contador do campo no painel da Shopee.<br/>"
        "3. Cole a descrição em texto puro. Não coloque contato, link ou promoção.<br/>"
        "4. Transfira a ficha técnica para os campos de características da plataforma.<br/>"
        "5. As perguntas e respostas servem para a descrição ou para responder compradores — não invente o que não estava no formulário.<br/>"
        "6. Siga o roteiro de fotos. A foto 1 é a da busca.<br/>"
        "7. Se a seção “Itens para você confirmar” listar algo, complete ou confirme antes de publicar. O texto usa o marcador [confirmar: …] no lugar do dado que faltou.",
        S["corpo_l"],
    ))
    story.append(Spacer(1, 6 * mm))
    suporte = _email_suporte()
    story.append(Paragraph(
        "Descrevi · FIT TECNOLOGIA E SERVICOS ADMINISTRATIVOS LTDA · CNPJ 49.408.467/0001-64<br/>"
        "Rua Visconde de Pirajá, 414, sala 718, Ipanema, Rio de Janeiro/RJ, CEP 22410-002"
        + (f"<br/>Dúvidas: {E(suporte)}" if suporte else ""),
        S["muted"],
    ))
    doc.build(story)
    return destino
