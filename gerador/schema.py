"""Esquema JSON enviado ao Gemini (responseSchema) e validado depois."""
from __future__ import annotations

def schema_anuncio() -> dict:
    str_ = lambda desc, mx: {"type": "STRING", "description": desc, "maxLength": mx} if False else {"type": "STRING", "description": desc}
    return {
        "type": "OBJECT",
        "required": [
            "titulos_ml", "titulo_shopee", "descricao", "ficha_tecnica",
            "perguntas", "roteiro_fotos", "pendencias", "observacoes",
        ],
        "properties": {
            "titulos_ml": {
                "type": "ARRAY", "description": "Exatamente 3 opções de título para o Mercado Livre, cada uma com no máximo 60 caracteres.",
                "minItems": 3, "maxItems": 3,
                "items": {
                    "type": "OBJECT",
                    "required": ["texto"],
                    "properties": {
                        "texto": {"type": "STRING", "description": "Título com no máximo 60 caracteres, sem pontuação nem símbolos."},
                        "enfoque": {"type": "STRING", "description": "O que esta opção destaca (ex.: capacidade, material)."},
                    },
                },
            },
            "titulo_shopee": {
                "type": "OBJECT",
                "required": ["texto"],
                "properties": {
                    "texto": {"type": "STRING", "description": "Nome do produto na Shopee, mais completo, sem keyword spam e com no máximo 3 marcas."},
                    "enfoque": {"type": "STRING"},
                },
            },
            "descricao": {
                "type": "OBJECT",
                "required": ["o_que_e", "especificacoes", "o_que_vem", "cuidados"],
                "properties": {
                    "o_que_e": {"type": "STRING", "description": "Uma ou duas frases: o que é e para quem serve. Só com dados informados."},
                    "especificacoes": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Lista de especificações informadas pelo vendedor."},
                    "o_que_vem": {"type": "STRING", "description": "O que vem na embalagem, se informado; senão use o placeholder [confirmar: o que vem na embalagem]."},
                    "cuidados": {"type": "STRING", "description": "Cuidados ou modo de uso, só se informado."},
                    "texto_corrido": {"type": "STRING", "description": "Descrição completa em texto puro, pronta para colar, com quebras de linha."},
                },
            },
            "ficha_tecnica": {
                "type": "ARRAY",
                "description": "Pares característica/valor para os campos da plataforma. Só o que foi informado.",
                "items": {
                    "type": "OBJECT",
                    "required": ["caracteristica", "valor"],
                    "properties": {
                        "caracteristica": {"type": "STRING"},
                        "valor": {"type": "STRING"},
                    },
                },
            },
            "perguntas": {
                "type": "ARRAY", "minItems": 5, "maxItems": 5,
                "description": "5 perguntas frequentes e respostas baseadas só nos dados enviados. Se faltar dado, a resposta usa o placeholder [confirmar: <o que falta>].",
                "items": {
                    "type": "OBJECT",
                    "required": ["pergunta", "resposta"],
                    "properties": {
                        "pergunta": {"type": "STRING"},
                        "resposta": {"type": "STRING"},
                    },
                },
            },
            "roteiro_fotos": {
                "type": "ARRAY", "minItems": 8, "maxItems": 8,
                "description": "Roteiro de 8 fotos, em ordem, descrevendo o que cada uma precisa mostrar.",
                "items": {
                    "type": "OBJECT",
                    "required": ["ordem", "o_que_mostrar"],
                    "properties": {
                        "ordem": {"type": "INTEGER"},
                        "o_que_mostrar": {"type": "STRING"},
                        "dica": {"type": "STRING"},
                    },
                },
            },
            "pendencias": {
                "type": "ARRAY",
                "description": "Lista curta do que faltou (os mesmos itens escritos como [confirmar: …] no texto).",
                "items": {"type": "STRING"},
            },
            "observacoes": {"type": "STRING", "description": "Notas curtas para o vendedor (sem promessa de venda ou ranking)."},
        },
    }
