# Ajustes na copy da Vitrine (copy_v1.md, texto final de 15/11/2026)

A página de vendas (`site/index.html`) segue o texto final de `/workspace/anuncio_pronto/copy_v1.md`, inclusive o subtítulo “já no limite de caracteres de cada plataforma” e o parágrafo da Shopee (“guias de integração citam até 120 caracteres”). A checagem do gerador também usa o teto de 120 na Shopee (ver `docs/limites.md`). Lista do que a página acrescenta ou detalha, além da copy de vendas:

1. **Link do anúncio.** Na seção “Como funciona”, no FAQ e no “o que não fazemos”, ficou explícito que o link, se informado, **não é acessado**. A copy de vendas menciona o link só como referência; o produto exige deixar claro que ele nunca é baixado.

2. **Seção nova, pedida no escopo:** “Experimente: um título grátis”, com CTA para `titulo.html`, sem promessa de venda ou de ranking, e com o limite de 3 gerações por dia. Não está na copy de vendas.

3. **Entrega.** Mencionei PDF e planilha no passo 3, porque é o que o fluxo realmente envia.

4. **E-mail de suporte.** `contato@valorasolucoes.com`, o valor único em `config.json` (`remetente.suporte`), `site/js/config.js` e `SUPORTE_EMAIL` do Worker. É a única menção permitida a esse domínio na Descrevi: não entra o nome da marca correspondente, nem URL do site correspondente. O controlador nos textos legais continua sendo a FIT TECNOLOGIA E SERVICOS ADMINISTRATIVOS LTDA. A FAQ usa a frase da copy: “A nota fiscal de serviço pode ser solicitada pelo e-mail de suporte.”

5. **Botões de checkout.** Continuam com os preços R$ 47 / R$ 127, mas os `href` só apontam para a Kiwify quando `config.js` tiver os links. Enquanto isso, a nota na hero diz que os links entram depois da criação dos dois produtos.

6. **FAQ sobre IA.** “seguem as regras de título” passou a “passam por checagens das regras de título e conteúdo de cada plataforma”, que é o que o gerador faz de fato.

7. **Rodapé.** Razão social da FIT, CNPJ, endereço e o aviso de que a Descrevi não é afiliada ao Mercado Livre nem à Shopee (não estava na copy; é informação institucional, não uma promessa). Sem nome ou site de outra marca.

8. **Bloco de exemplo de título** (produtos ilustrativos, não clientes), para mostrar o tipo de correção. Os PDFs completos ficam em `amostra/`.

9. **Descrição da Kiwify e as 3 respostas de Reddit** da copy_v1.md não foram para o site (não são a landing). Permanecem no arquivo da Vitrine.

Nada foi acrescentado sobre aumento de vendas, posição na busca ou “anúncio que converte”.
