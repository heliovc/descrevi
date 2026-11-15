"""Checagens automáticas do Anúncio Pronto.

Não raspamos Mercado Livre nem Shopee. Os limites e regras vêm de documentação
pública citada em docs/limites.md. Em caso de dúvida, usamos o teto mais conservador
e registramos a fonte.
"""
from __future__ import annotations
import re
import unicodedata

ML_TITULO = 60          # settings.max_title_length típico; conferido em categorias MLB via API pública
ML_DESCRICAO = 50_000   # settings.max_description_length (API de categorias)
SHOPEE_TITULO = 120     # teto da página de vendas e da checagem (mais curto que os 256 citados por integradores BR; a central BR não publica o número)
SHOPEE_DESCRICAO = 5_000  # Ideris e Anymarket; Mainô cita 10.000 — usamos o menor

# Palavras que o ML oficialmente não quer no título, ou que equivalem a contato/promessa.
# "estoque": developers.mercadolivre.com.br/pt_br/publicacao-de-produtos
# frete/parcelamento/devolução/promo: mesma página ("Evite colocar no título informações sobre outros serviços")
# novo/usado/recondicionado: mesma página (vão nas características)
RX_ML_PROIBIDO = re.compile(
    r"\b(estoque|frete(?:\s*gr[aá]tis)?|promo[cç][aã]o|oferta|desconto|parcelamento|"
    r"devolu[cç](?:[aã]o|[oõ]es)|novo|usada?|recondicionad[oa]|"
    r"whatsapp|whats\s*app|\bzap\b|telegram|instagram|facebook|telefone|celular|"
    r"e-?mail|gmail|hotmail|www|https?|"
    r"mais\s+vendid[oa]s?|best\s*sellers?|n[uú]mero\s*1|n[oº°]\s*1|"
    r"l[ií]der(?:es)?\s+de\s+vendas|top\s*1|n[uú]mero\s+um)\b",
    re.I,
)
RX_SHOPEE_PROIBIDO = re.compile(
    r"\b(estoque|frete(?:\s*gr[aá]tis)?|promo[cç][aã]o|oferta|desconto|sale|"
    r"hot\s*item|best\s*sellers?|mais\s+vendid[oa]s?|"
    r"whatsapp|whats\s*app|\bzap\b|telegram|instagram|facebook|telefone|celular|"
    r"e-?mail|gmail|www|https?)\b",
    re.I,
)
# Sinais/símbolos que o ML pede para evitar no título ("não use sinais de pontuação nem símbolos")
# e a Shopee trata como risco de keyword spam. Medidas (1 L, 40x30, 220V) e hífen simples passam.
RX_SIMBOLOS = re.compile(r"[!?*$#@%&+=_\"'“”‘’•·♥★☆✨🔥💯✅❌▶►•]|[\u2600-\u27BF]|[\U0001F300-\U0001FAFF]")
RX_CONTATO = re.compile(
    r"(whatsapp|whats\s*app|\bzap\b|telegram|instagram|facebook|\bemail\b|e-mail|"
    r"\b(?:www\.|https?://)|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"\b(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-\s]?\d{4}\b)",
    re.I,
)
RX_LINK = re.compile(r"https?://|www\.", re.I)
RX_MEDIDA = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|m|km|ml|l|lt|litro|litros|kg|g|mg|w|v|va|hz|wats?|volts?|"
    r"pol(?:egadas?)?|\"|mah|gb|tb|mb|rpm|dpi|lbs?|oz|un|unid(?:ades?)?)\b",
    re.I,
)

RX_CONFIRMAR = re.compile(r"\[confirmar:\s*([^\]]+?)\]", re.I)


def texto_sem_confirmacoes(texto: str) -> str:
    """Remove blocos [confirmar: …] para não tratar o placeholder como fato inventado."""
    return RX_CONFIRMAR.sub(" ", texto or "")


def extrair_confirmacoes(*textos: str) -> list[str]:
    vistos, out = set(), []
    for t in textos:
        for m in RX_CONFIRMAR.finditer(t or ""):
            item = " ".join(m.group(1).split()).strip(" .;,:")
            if not item:
                continue
            k = _norm(item)
            if k not in vistos:
                vistos.add(k)
                out.append(item)
    return out


def _textos_gerados(anuncio: dict) -> list[str]:
    textos = []
    for t in anuncio.get("titulos_ml") or []:
        textos.append((t or {}).get("texto") or "")
    ts = anuncio.get("titulo_shopee") or {}
    textos.append(ts.get("texto") or "")
    desc = anuncio.get("descricao") or {}
    textos.extend([
        desc.get("o_que_e") or "", desc.get("texto_corrido") or "",
        desc.get("o_que_vem") or "", desc.get("cuidados") or "",
        " ".join(desc.get("especificacoes") or []),
    ])
    for par in anuncio.get("ficha_tecnica") or []:
        if isinstance(par, dict):
            textos.append(f"{par.get('caracteristica') or ''} {par.get('valor') or ''}")
    for p in anuncio.get("perguntas") or []:
        textos.append(f"{(p or {}).get('pergunta') or ''} {(p or {}).get('resposta') or ''}")
    for f in anuncio.get("roteiro_fotos") or []:
        textos.append(f"{(f or {}).get('o_que_mostrar') or ''} {(f or {}).get('dica') or ''}")
    textos.append(anuncio.get("observacoes") or "")
    for p in anuncio.get("pendencias") or []:
        textos.append(str(p))
    return textos


def listar_confirmacoes(anuncio: dict) -> list[str]:
    """Itens [confirmar: …] encontrados no texto gerado, na ordem de aparição, sem repetir."""
    return extrair_confirmacoes(*_textos_gerados(anuncio))


class Problema(dict):
    def __init__(self, nivel: str, campo: str, mensagem: str, fonte: str = ""):
        super().__init__(nivel=nivel, campo=campo, mensagem=mensagem, fonte=fonte)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _texto_entrada(item: dict) -> str:
    partes = [item.get("nome_produto"), item.get("categoria"), item.get("especificacoes"),
              item.get("diferenciais"), item.get("marca")]
    return " ".join(str(p or "") for p in partes)



def restaurar_acentos(texto: str, origem: str) -> str:
    """Devolve acentos do texto de origem às palavras geradas sem acento.

    Não inventa palavra: só corrige a grafia quando o vendedor já escreveu a forma acentuada.
    """
    mapa: dict[str, str] = {}
    for w in re.findall(r"[A-Za-zÀ-ÿ]+", origem or ""):
        k = _norm(w).replace(" ", "")
        if not k:
            continue
        # prefere a forma que tem marca diacrítica
        atual = mapa.get(k)
        if atual is None or (any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", w))
                             and not any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", atual))):
            mapa[k] = w

    def troca(m):
        w = m.group(0)
        orig = mapa.get(_norm(w).replace(" ", ""))
        if not orig:
            return w
        if w.isupper():
            return orig.upper()
        if w[0].isupper():
            return orig[0].upper() + orig[1:]
        return orig[0].lower() + orig[1:] if len(orig) > 1 else orig.lower()

    return re.sub(r"[A-Za-zÀ-ÿ]+", troca, texto or "")


def aplicar_acentos(anuncio: dict, item: dict) -> dict:
    origem = _texto_entrada(item)
    for t in anuncio.get("titulos_ml") or []:
        t["texto"] = restaurar_acentos(t.get("texto") or "", origem)
    ts = anuncio.get("titulo_shopee")
    if isinstance(ts, dict) and ts.get("texto"):
        ts["texto"] = restaurar_acentos(ts["texto"], origem)
    return anuncio

def medidas(texto: str) -> set[str]:
    return {m.group(0).lower().replace(" ", "") for m in RX_MEDIDA.finditer(texto or "")}


def maiusculas_excessivas(texto: str) -> bool:
    letras = [c for c in texto if c.isalpha()]
    if len(letras) < 8:
        return False
    return sum(1 for c in letras if c.isupper()) / len(letras) > 0.8


def contar_marcas_citadas(titulo: str, item: dict) -> list[str]:
    """Aproxima marcas citadas no título da Shopee (teto oficial: 3).

    Usa a marca do próprio produto (se informada) e nomes próprios após
    'para' / 'compatível com'. Não é um cadastro oficial de marcas.
    """
    encontradas: list[str] = []
    marca = (item.get("marca") or "").strip()
    if marca and re.search(r"\b" + re.escape(marca) + r"\b", titulo, re.I):
        encontradas.append(marca)
    m = re.search(r"(?:compat[ií]vel\s+com|para)\s+(.+)$", titulo, re.I)
    if m:
        trecho = m.group(1)
        partes = re.split(r",|;|/|\be\b", trecho, flags=re.I)
        for p in partes:
            nome = p.strip(" .")
            if len(nome) >= 2 and nome.lower() not in {"o", "a", "os", "as", "de", "do", "da"}:
                encontradas.append(nome)
    # unique case-insensitive, ordem de aparição
    vistos, out = set(), []
    for n in encontradas:
        k = _norm(n)
        if k not in vistos:
            vistos.add(k)
            out.append(n)
    return out


def checar_titulo_ml(texto: str, item: dict) -> list[Problema]:
    out: list[Problema] = []
    t = (texto or "").strip()
    fonte = "https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos"
    if not t:
        out.append(Problema("erro", "titulo_ml", "título vazio", fonte))
        return out
    if len(t) > ML_TITULO:
        out.append(Problema("erro", "titulo_ml", f"título com {len(t)} caracteres (limite {ML_TITULO}, por categoria via max_title_length)", fonte))
    if RX_ML_PROIBIDO.search(t):
        out.append(Problema("erro", "titulo_ml", f"termo não permitido no título do Mercado Livre: “{RX_ML_PROIBIDO.search(t).group(0)}”", fonte))
    if RX_SIMBOLOS.search(t):
        out.append(Problema("erro", "titulo_ml", "o Mercado Livre pede para não usar sinais de pontuação nem símbolos no título", fonte))
    if RX_CONTATO.search(t):
        out.append(Problema("erro", "titulo_ml", "título parece conter contato, link ou rede social", fonte))
    if maiusculas_excessivas(t):
        out.append(Problema("erro", "titulo_ml", "título em caixa alta demais; use maiúscula só no necessário", fonte))
    # Marca de terceiro sem "para"/"compatível com"
    # (só alerta se o vendedor declarou que o produto é genérico/compatível)
    return out


def checar_titulo_shopee(texto: str, item: dict) -> list[Problema]:
    out: list[Problema] = []
    t = (texto or "").strip()
    fonte_spam = "https://seller.shopee.com.br/edu/article/20972/Whats-keywords-spam"
    fonte_int = "teto usado: 120 caracteres (página de vendas da Descrevi; a central do vendedor no Brasil não publica o número)"
    if not t:
        out.append(Problema("erro", "titulo_shopee", "título vazio", fonte_spam))
        return out
    if len(t) > SHOPEE_TITULO:
        out.append(Problema("erro", "titulo_shopee", f"título com {len(t)} caracteres (teto usado: {SHOPEE_TITULO})", fonte_int))
    if RX_SHOPEE_PROIBIDO.search(t):
        out.append(Problema("erro", "titulo_shopee", f"termo não permitido ou arriscado no título da Shopee: “{RX_SHOPEE_PROIBIDO.search(t).group(0)}”", fonte_spam))
    if RX_SIMBOLOS.search(t) or "#" in t:
        out.append(Problema("erro", "titulo_shopee", "símbolos, emoji ou hashtag no título — a Shopee trata excesso disso como keyword spam", fonte_spam))
    if RX_CONTATO.search(t):
        out.append(Problema("erro", "titulo_shopee", "título parece conter contato ou link", "https://help.shopee.com.br/portal/4/article/76225"))
    marcas = contar_marcas_citadas(t, item)
    if len(marcas) > 3:
        out.append(Problema("erro", "titulo_shopee", f"mais de 3 marcas no título ({', '.join(marcas)})", fonte_spam))
    # repetição grosseira (keyword spam)
    toks = [w for w in re.split(r"\W+", _norm(t)) if len(w) >= 4]
    if toks:
        from collections import Counter
        comuns = [(w, n) for w, n in Counter(toks).items() if n >= 3]
        if comuns:
            out.append(Problema("erro", "titulo_shopee", f"palavra repetida demais no título (risco de keyword spam): {comuns[0][0]}", fonte_spam))
    if maiusculas_excessivas(t):
        out.append(Problema("aviso", "titulo_shopee", "título em caixa alta demais", fonte_spam))
    return out


def checar_descricao(texto: str, plataforma: str) -> list[Problema]:
    out: list[Problema] = []
    t = texto or ""
    limite = ML_DESCRICAO if plataforma == "ml" else SHOPEE_DESCRICAO
    fonte = ("API de categorias do Mercado Livre (max_description_length)" if plataforma == "ml"
             else "guias de integração Shopee BR (Ideris/Anymarket: 5.000 caracteres)")
    if len(t) > limite:
        out.append(Problema("erro", "descricao", f"descrição com {len(t)} caracteres (limite usado: {limite})", fonte))
    if RX_LINK.search(t) or RX_CONTATO.search(t):
        out.append(Problema("erro", "descricao", "descrição contém link, contato ou rede social — as duas plataformas proíbem isso",
                            "ML: seller_contact not_allowed; Shopee: help.shopee.com.br artigo 76225 e Ideris"))
    if re.search(r"<\s*(a|img|script|html|br|p|div)\b", t, re.I):
        out.append(Problema("erro", "descricao", "descrição deve ser texto puro, sem HTML (Mercado Livre e Shopee)",
                            "https://developers.mercadolivre.com.br/descricao-de-produtos"))
    if re.search(r"\bmais\s+vendid[oa]s?\b|\bbest\s*seller\b", t, re.I):
        out.append(Problema("erro", "descricao", "não usamos “mais vendido” nem equivalente", "política da Descrevi (sem promessa de venda/ranking)"))
    return out


def checar_inventados(anuncio: dict, item: dict) -> list[Problema]:
    """Marca medidas/unidades que aparecem no texto gerado e não estavam nos dados enviados."""
    out: list[Problema] = []
    origem = medidas(_texto_entrada(item))
    blocos = []
    for t in anuncio.get("titulos_ml") or []:
        blocos.append(("titulo_ml", t.get("texto") or ""))
    ts = anuncio.get("titulo_shopee") or {}
    blocos.append(("titulo_shopee", ts.get("texto") or ""))
    desc = anuncio.get("descricao") or {}
    blocos.append(("descricao", " ".join([
        desc.get("o_que_e") or "", desc.get("texto_corrido") or "", desc.get("o_que_vem") or "",
        desc.get("cuidados") or "", " ".join(desc.get("especificacoes") or []),
    ])))
    for par in anuncio.get("ficha_tecnica") or []:
        if isinstance(par, dict):
            blocos.append(("ficha_tecnica", f"{par.get('caracteristica','')} {par.get('valor','')}"))
    for p in anuncio.get("perguntas") or []:
        blocos.append(("perguntas", f"{p.get('pergunta','')} {p.get('resposta','')}"))
    vistos = set()
    for campo, txt in blocos:
        for med in medidas(texto_sem_confirmacoes(txt)):
            if med not in origem and med not in vistos:
                vistos.add(med)
                out.append(Problema("erro", campo, f"medida ou unidade “{med}” não aparece nos dados enviados — não inventamos especificação (use [confirmar: {med}] se o dado faltar)", ""))
    return out


def montar_descricao_corrida(desc: dict) -> str:
    partes = []
    if desc.get("o_que_e"):
        partes.append(desc["o_que_e"].strip())
    specs = desc.get("especificacoes") or []
    if specs:
        partes.append("Especificações:")
        partes.extend(f"• {s}" if not str(s).startswith("•") else str(s) for s in specs)
    if desc.get("o_que_vem"):
        partes.append("O que vem na embalagem:\n" + desc["o_que_vem"].strip())
    if desc.get("cuidados"):
        partes.append("Cuidados:\n" + desc["cuidados"].strip())
    if desc.get("texto_corrido"):
        # Preferimos o texto corrido se ele já estiver completo; senão montamos.
        tc = desc["texto_corrido"].strip()
        if len(tc) >= 80:
            return tc
    return "\n\n".join(partes).strip()


def checar_estrutura(anuncio: dict, item: dict) -> list[Problema]:
    out: list[Problema] = []
    tits = anuncio.get("titulos_ml") or []
    if len(tits) != 3:
        out.append(Problema("erro", "titulos_ml", f"eram esperadas 3 opções de título do Mercado Livre, vieram {len(tits)}"))
    if not (anuncio.get("titulo_shopee") or {}).get("texto"):
        # Só é erro se o vendedor pediu Shopee ou ambos
        if (item.get("plataforma") or "ambos") in ("shopee", "ambos"):
            out.append(Problema("erro", "titulo_shopee", "faltou o título da Shopee"))
    perguntas = anuncio.get("perguntas") or []
    if len(perguntas) != 5:
        out.append(Problema("erro", "perguntas", f"eram esperadas 5 perguntas e respostas, vieram {len(perguntas)}"))
    fotos = anuncio.get("roteiro_fotos") or []
    if len(fotos) != 8:
        out.append(Problema("erro", "roteiro_fotos", f"eram esperadas 8 fotos no roteiro, vieram {len(fotos)}"))
    if not (anuncio.get("ficha_tecnica") or []):
        out.append(Problema("aviso", "ficha_tecnica", "ficha técnica vazia — provavelmente faltaram características no formulário"))
    return out


def checar(anuncio: dict, item: dict) -> list[Problema]:
    probs: list[Problema] = []
    probs.extend(checar_estrutura(anuncio, item))
    plat = (item.get("plataforma") or "ambos").lower()
    if plat in ("ml", "ambos"):
        for t in anuncio.get("titulos_ml") or []:
            probs.extend(checar_titulo_ml(t.get("texto") or "", item))
    if plat in ("shopee", "ambos"):
        probs.extend(checar_titulo_shopee((anuncio.get("titulo_shopee") or {}).get("texto") or "", item))
    desc = montar_descricao_corrida(anuncio.get("descricao") or {})
    if plat in ("ml", "ambos"):
        probs.extend(checar_descricao(desc, "ml"))
    if plat in ("shopee", "ambos"):
        probs.extend(checar_descricao(desc, "shopee"))
    # descrição também não deve ter contato mesmo se plataforma for só uma
    probs.extend(checar_inventados(anuncio, item))
    # dedup
    vistos, unicos = set(), []
    for p in probs:
        k = (p["nivel"], p["campo"], p["mensagem"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(p)
    return unicos


def tem_erro(probs: list[Problema]) -> bool:
    return any(p["nivel"] == "erro" for p in probs)
