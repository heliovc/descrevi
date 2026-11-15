# Limites e regras usados na checagem automática

Não há raspagem do Mercado Livre nem da Shopee. Os números abaixo vêm de documentação pública ou da API pública de categorias. Onde a fonte oficial brasileira não publica um teto, usamos o valor conservador e declaramos a divergência.

## Mercado Livre

| Campo | Valor usado | Fonte |
|---|---|---|
| Título | **60 caracteres** (típico; o valor oficial é por categoria, em `settings.max_title_length`) | API pública `GET https://api.mercadolibre.com/categories/{id}` — conferido em 15/11/2026 para MLB1055 (Celulares e Smartphones) e MLB1574 (Casa, Móveis e Decoração): ambos `max_title_length: 60`. Documentado em https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos (atualizado em 09/01/2026). |
| Descrição | 50.000 caracteres, **texto puro** (`plain_text`) | Mesma API (`max_description_length: 50000`). Descrição em https://developers.mercadolivre.com.br/descricao-de-produtos |
| Fotos (informação, não é o nosso roteiro de 8) | `max_pictures_per_item: 12` nas categorias consultadas | Mesma API |
| Palavra “estoque” no título | Não permitida (publicação moderada) | https://developers.mercadolivre.com.br/pt_br/publicacao-de-produtos |
| Frete, parcelamento, devolução, promoção no título | Evitar; a plataforma já exibe esses dados | Idem |
| “Novo”, “usado”, “recondicionado” no título | Não incluir; vão nas características | Idem |
| Marca de terceiro | Só para indicar compatibilidade, com “para” ou “compatível com” | Idem |
| Pontuação e símbolos no título | “Separe as palavras com espaço não use sinais de pontuação nem símbolos.” | Idem |
| Contato do vendedor | `seller_contact: not_allowed` nas categorias consultadas; a documentação lembra que comprador e vendedor não trocam contato imediatamente | Idem + campo da API de categorias |

A checagem também recusa “mais vendido”, “best seller” e equivalentes (política da Descrevi, não uma cláusula citada nessa página do ML) e sinaliza título em caixa alta demais (orientação comum das centrais de vendedores; não está no trecho oficial acima como regra rígida).

## Shopee

| Campo | Valor usado | Fonte |
|---|---|---|
| Título (teto da checagem) | **256 caracteres** | Guias de integração no Brasil: Ideris (https://atendimento.ideris.com.br/hc/pt-br/articles/21406464506647-Boas-práticas-de-anúncios-para-a-Shopee), Anymarket e Mainô. A central do vendedor no Brasil **não publica o número** nos artigos 2731 e 20972. Um material oficial de outro país (Malásia, “Optimising your Product Listings”) cita **120**. Geramos títulos legíveis, não “no teto”, e recusamos o que passar de 256. |
| Descrição | **5.000 caracteres** (o menor entre as fontes) | Ideris e Anymarket: 5.000. Mainô cita 10.000. Usamos 5.000. |
| Fórmula do nome | Nome do produto + Marca + Especificações/Tipo (a central também cita Marca + Nome + Modelo) | https://seller.shopee.com.br/edu/article/2731 e https://seller.shopee.com.br/edu/article/20972 |
| Até 3 marcas no título | Sim | Artigo 20972 (keyword spam), central do vendedor BR |
| Keyword spam, símbolos, hashtag | Recusados no título | Artigo 20972 |
| Links externos, contato, loja de fora, promoção na descrição | Recusados | Artigo 76225 da Central de Ajuda BR (https://help.shopee.com.br/portal/4/article/76225) e Ideris |
| “Best seller”, “hot item”, “sale”, “free shipping” | Evitar | Material oficial de outro país (PDF MY) e política da Descrevi; no Brasil, o artigo 2868 trata de spam de palavras-chave e de característica incorreta |

## O que a checagem não faz

- Não consulta o `max_title_length` da categoria real do produto (o vendedor não informa o ID da categoria do ML). Usamos 60, que é o valor típico, e o PDF avisa para conferir o contador do painel.
- Não baixa anúncio, busca ou página do vendedor.
- Não afirma que o texto “passa na moderação”.
