"""Provedores de IA para o Anúncio Pronto.

DESCREVI_PROVIDER = gemini | mock  (padrão: gemini se houver GEMINI_API_KEY, senão mock)
DESCREVI_MODELS   = lista separada por vírgula (padrão: gemini-3.5-flash-lite,gemini-3.1-flash-lite)

Só os dados do PRODUTO (o que o vendedor colou) vão para o provedor.
E-mail, nome do comprador, order_id e o link de referência nunca vão.
O link não é baixado em lugar nenhum deste repositório.
"""
from __future__ import annotations
import json, os, re, time, urllib.request, urllib.error
from pathlib import Path
from gerador.schema import schema_anuncio
from gerador.checagem import ML_TITULO, SHOPEE_TITULO, SHOPEE_DESCRICAO

class ErroIA(RuntimeError):
    pass


def carregar_chave_local() -> None:
    """Carrega GEMINI_API_KEY do ambiente ou, só em teste local, de GEMINI_ENV_FILE.

    Não copia a chave para este repositório. O arquivo padrão da Fornecia só é lido
    se GEMINI_ENV_FILE apontar para ele.
    """
    if os.environ.get("GEMINI_API_KEY"):
        return
    p = os.environ.get("GEMINI_ENV_FILE")
    if not p:
        return
    path = Path(p)
    if not path.exists():
        return
    for linha in path.read_text().splitlines():
        if linha.startswith("GEMINI_API_KEY="):
            os.environ["GEMINI_API_KEY"] = linha.split("=", 1)[1].strip().strip('"').strip("'")
            return


PROMPT_SISTEMA = """Você escreve o texto de anúncios para vendedores do Mercado Livre e da Shopee, em português do Brasil.
Você NÃO publica o anúncio. Você só entrega texto e um roteiro de fotos, a partir dos dados que o vendedor enviou.

Regras obrigatórias:
- Use SOMENTE os dados fornecidos. Não invente marca, modelo, medida, material, voltagem, conteúdo da caixa, garantia, origem ou qualquer outra característica. Se faltar um dado, deixe o campo curto ou vazio e registre em "pendencias".
- Não faça promessa de venda, de posição na busca, de “mais vendido”, “nº 1”, “líder de vendas” ou equivalente.
- Não inclua telefone, e-mail, WhatsApp, site, rede social ou qualquer link.
- Não use a palavra "estoque" (em título ou descrição). Não escreva “estoque limitado”.
- Não use HTML. Descrição em texto puro, com quebras de linha.
- Títulos do Mercado Livre (exatamente 3 opções), cada um com NO MÁXIMO 60 caracteres (conte espaços). Estrutura: Produto + Marca + modelo + especificações que identifiquem o produto. Separe palavras com espaço; não use sinais de pontuação, símbolos nem emoji. Mantenha a acentuação normal do português (é, ç, ã, ó…): acento é letra, não símbolo, e conta como 1 caractere. Não retire acentos. Não coloque no título: frete, parcelamento, devolução, promoção, oferta, desconto, “novo”, “usado”, “recondicionado”, cor ou tamanho quando isso for variação. Marca de terceiro só com “para” ou “compatível com”. Evite caixa alta no título inteiro.
- Título da Shopee: mais completo, fácil de ler. Fórmula: Nome do produto + Marca + especificações/tipo (a central também cita Marca + Nome + Modelo). No máximo 3 marcas no título. Sem keyword spam (não repita a mesma palavra, não faça lista de termos soltos, sem símbolos, hashtag ou emoji). Sem “hot item”, “best seller”, “sale”, “frete grátis”. Pode ter até 256 caracteres, mas seja legível — não encha de palavras.
- Descrição organizada: o que é e para quem serve; especificações em lista; o que vem na embalagem (só se informado); cuidados (só se informado). Teto prático da Shopee que usamos: 5.000 caracteres.
- Ficha técnica: pares característica/valor só com o que foi informado.
- 5 perguntas e respostas que um comprador faria, respondidas só com os dados enviados. Se o dado não foi informado, diga isso com clareza na resposta (não invente).
- Roteiro de 8 fotos, em ordem, dizendo o que cada uma precisa mostrar (o vendedor ou o fotógrafo tira as fotos; você não gera imagem).
- Se o produto for genérico / sem marca, diga isso na ficha. Não atribua marca de terceiro ao produto; use “para” ou “compatível com” só quando o vendedor pediu.
- Não mencione Mercado Livre, Shopee, Descrevi ou concorrentes no texto que o vendedor vai colar no anúncio (títulos, descrição, ficha, Q&A). O roteiro de fotos pode ser neutro.
"""


def _payload_produto(item: dict) -> str:
    # O link de referência propositalmente NÃO entra no prompt (e nunca é baixado).
    return (
        f"Nome do produto: {item.get('nome_produto') or ''}\n"
        f"Categoria: {item.get('categoria') or ''}\n"
        f"Plataforma de destino: {item.get('plataforma') or 'ambos'}\n"
        f"Especificações / características coladas pelo vendedor:\n{item.get('especificacoes') or ''}\n\n"
        f"Diferenciais informados:\n{item.get('diferenciais') or '(não informado)'}\n"
    )


class ProvedorMock:
    nome = "mock"
    modelo = "mock-v1"

    def gerar(self, item: dict, erros_anteriores: list | None = None) -> dict:
        nome = (item.get("nome_produto") or "Produto").strip()
        specs = (item.get("especificacoes") or "").strip()
        diffs = (item.get("diferenciais") or "").strip()
        cat = (item.get("categoria") or "").strip()

        def corta(s, n):
            s = re.sub(r"[^\wÀ-ÿ\s×x/\-]", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            if len(s) <= n:
                return s
            return s[:n].rsplit(" ", 1)[0].strip()

        base = " ".join(p for p in (nome, diffs, specs) if p)
        t1 = corta(base, 60)
        # variações simples mudando a ordem (ainda dentro de 60)
        pedacos = [p for p in re.split(r"\s+", base) if p]
        t2 = corta(" ".join(pedacos[1:] + pedacos[:1]) if len(pedacos) > 2 else base, 60)
        t3 = corta(" ".join([nome] + [p for p in pedacos if p.lower() not in nome.lower().split()][:6]), 60)
        if t2 == t1:
            t2 = corta(f"{nome} {specs}", 60)
        if t3 in (t1, t2):
            t3 = corta(f"{nome} {diffs} {specs}", 60)

        shopee = corta(" ".join(p for p in (nome, diffs, specs, f"Categoria {cat}" if cat else "") if p), 180)
        linhas_spec = [ln.strip(" -•") for ln in specs.splitlines() if ln.strip()] or [specs] if specs else []
        pend = []
        if not specs:
            pend.append("Faltaram especificações (medidas, material, o que vem na caixa).")
        if not diffs:
            pend.append("Não foram informados diferenciais; o texto se ateve ao que foi dito no nome e nas especificações.")

        desc_partes = [
            f"{nome}" + (f" para quem busca {diffs}." if diffs else "."),
        ]
        if linhas_spec:
            desc_partes.append("Especificações:\n" + "\n".join(f"• {s}" for s in linhas_spec))
        desc_partes.append("O que vem na embalagem: não foi informado no formulário. Confirme antes de publicar.")
        texto = "\n\n".join(desc_partes)
        ficha = []
        if cat:
            ficha.append({"caracteristica": "Categoria informada", "valor": cat})
        for s in linhas_spec[:12]:
            if ":" in s:
                a, b = s.split(":", 1)
                ficha.append({"caracteristica": a.strip()[:80], "valor": b.strip()[:200]})
            else:
                ficha.append({"caracteristica": "Característica", "valor": s[:200]})
        perguntas = [
            {"pergunta": "Quais são as medidas ou a capacidade?",
             "resposta": next((s for s in linhas_spec if re.search(r"\d", s)), "Isso não foi informado no formulário. Complete antes de publicar.")},
            {"pergunta": "De que material é feito?",
             "resposta": next((s for s in linhas_spec if re.search(r"material|inox|acr[ií]lico|pl[aá]stico|algod[aã]o|madeira|vidro|silicone", s, re.I)), "O material não foi informado no formulário.")},
            {"pergunta": "O que vem na caixa?",
             "resposta": "O conteúdo da embalagem não foi informado no formulário. Inclua essa informação na descrição antes de publicar."},
            {"pergunta": "Tem garantia?",
             "resposta": "A garantia não foi informada no formulário. Só declare a garantia que você realmente oferece."},
            {"pergunta": "Quais são as cores ou tamanhos disponíveis?",
             "resposta": "Se houver variações de cor ou tamanho, cadastre-as no campo de variações da plataforma, não no título."},
        ]
        roteiro = [
            {"ordem": 1, "o_que_mostrar": f"Foto principal do {nome} de frente, fundo liso, bem iluminada, ocupando a maior parte do quadro.", "dica": "É a primeira imagem da busca; evite texto sobreposto e marca d’água com contato."},
            {"ordem": 2, "o_que_mostrar": "O mesmo produto em ângulo de 45 graus, mostrando volume e laterais.", "dica": "Mantenha o fundo e a luz iguais à foto 1."},
            {"ordem": 3, "o_que_mostrar": "Foto de costas ou do outro lado, para o comprador ver o produto inteiro.", "dica": ""},
            {"ordem": 4, "o_que_mostrar": "Detalhe de um diferencial informado (material, tampa, costura, conexão, display etc.).", "dica": "Só destaque o que você realmente informou no formulário."},
            {"ordem": 5, "o_que_mostrar": "Escala: o produto ao lado de um objeto comum (caneta, mão, caderno) ou com as medidas visíveis se você as tiver.", "dica": "Não invente medida na imagem."},
            {"ordem": 6, "o_que_mostrar": "O que vem na embalagem, com as peças dispostas e visíveis, se essa informação existir.", "dica": "Se o conteúdo não foi informado, tire a foto e complete o texto depois."},
            {"ordem": 7, "o_que_mostrar": "O produto em uso ou em contexto real (sem pessoa reconhecível, se possível).", "dica": ""},
            {"ordem": 8, "o_que_mostrar": "Etiqueta, selo, identificação ou detalhe de acabamento (se houver).", "dica": "Não fotografe documento pessoal nem dado de contato."},
        ]
        return {
            "titulos_ml": [
                {"texto": t1, "enfoque": "conjunto das informações"},
                {"texto": t2, "enfoque": "variação da ordem"},
                {"texto": t3, "enfoque": "nome em primeiro lugar"},
            ],
            "titulo_shopee": {"texto": shopee, "enfoque": "nome mais completo"},
            "descricao": {
                "o_que_e": desc_partes[0],
                "especificacoes": linhas_spec,
                "o_que_vem": "",
                "cuidados": "",
                "texto_corrido": texto,
            },
            "ficha_tecnica": ficha,
            "perguntas": perguntas,
            "roteiro_fotos": roteiro,
            "pendencias": pend + ["Conteúdo da embalagem não informado.", "Garantia não informada."],
            "observacoes": "Gerado no modo de teste (sem IA). Revise antes de publicar. Não há garantia de vendas nem de posição na busca.",
        }


class ProvedorGemini:
    nome = "gemini"

    def __init__(self, modelos: list[str] | None = None):
        self.key = os.environ.get("GEMINI_API_KEY") or ""
        if not self.key:
            raise ErroIA("GEMINI_API_KEY ausente")
        env_m = [m.strip() for m in (os.environ.get("DESCREVI_MODELS") or "").split(",") if m.strip()]
        self.modelos = modelos or env_m or ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
        self.modelo = self.modelos[0]

    def _post(self, modelo: str, corpo: dict, timeout: int = 120) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
        req = urllib.request.Request(
            url, data=json.dumps(corpo).encode("utf-8"), method="POST",
            headers={"content-type": "application/json", "x-goog-api-key": self.key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            corpo_err = e.read()[:600].decode("utf-8", "replace")
            corpo_err = corpo_err.replace(self.key, "***")
            raise ErroIA(f"HTTP {e.code} em {modelo}: {corpo_err}") from None

    def gerar(self, item: dict, erros_anteriores: list | None = None) -> dict:
        extra = ""
        if erros_anteriores:
            lista = "\n".join(f"- {e.get('campo')}: {e.get('mensagem')}" for e in erros_anteriores)
            extra = "\n\nA versão anterior falhou nestas checagens. Corrija tudo isto, sem inventar dados:\n" + lista
        corpo = {
            "systemInstruction": {"parts": [{"text": PROMPT_SISTEMA}]},
            "contents": [{"role": "user", "parts": [{"text": "Dados do produto enviados pelo vendedor:\n\n" + _payload_produto(item) + extra + "\n\nResponda com o JSON do esquema."}]}],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
                "responseSchema": schema_anuncio(),
                "maxOutputTokens": 4096,
            },
        }
        ultimo = None
        for modelo in self.modelos:
            for tentativa in range(3):
                try:
                    resp = self._post(modelo, corpo)
                    self.modelo = modelo
                    cand = (resp.get("candidates") or [{}])[0]
                    partes = (cand.get("content") or {}).get("parts") or []
                    txt = "".join(p.get("text", "") for p in partes)
                    if not txt:
                        raise ErroIA(f"resposta vazia ({cand.get('finishReason')})")
                    dados = json.loads(txt)
                    dados["_uso"] = resp.get("usageMetadata") or {}
                    dados["_modelo"] = modelo
                    return dados
                except (ErroIA, json.JSONDecodeError) as e:
                    ultimo = e
                    msg = str(e)
                    if "HTTP 429" in msg or "RESOURCE_EXHAUSTED" in msg:
                        break
                    if "HTTP 4" in msg and "HTTP 429" not in msg:
                        break
                    time.sleep(2 ** tentativa * 3)
        raise ErroIA(f"todos os modelos falharam: {ultimo}")


def provedor(nome: str | None = None):
    nome = (nome or os.environ.get("DESCREVI_PROVIDER") or "").strip().lower()
    if not nome:
        nome = "gemini" if os.environ.get("GEMINI_API_KEY") else "mock"
    if nome == "gemini":
        return ProvedorGemini()
    if nome == "mock":
        return ProvedorMock()
    raise ErroIA(f"provedor desconhecido: {nome}")
