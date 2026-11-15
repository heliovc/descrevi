-- Descrevi · pedidos do pacote Anúncio Pronto (Cloudflare D1 = SQLite).
-- Minimização (LGPD): e-mail, nome, ids da Kiwify, textos que o vendedor colou no formulário
-- e o link de referência (nunca baixado). Não guardamos CPF, telefone, endereço, IP em claro
-- nem dados de cartão, mesmo que venham no webhook.
-- Retenção: 30 dias (rotina diária apaga pedidos, itens, outbox, logs e contadores antigos).

CREATE TABLE IF NOT EXISTS pedidos (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL,
  nome          TEXT,
  order_id      TEXT UNIQUE,
  token         TEXT NOT NULL UNIQUE,
  pacote        TEXT NOT NULL,          -- 3 | 10
  quantidade    INTEGER NOT NULL,
  status        TEXT NOT NULL,          -- pago | recebido | em_geracao | enviado | falhou | reembolsado
  detalhe       TEXT,
  criado_em     TEXT NOT NULL,
  atualizado_em TEXT NOT NULL,
  recebido_em   TEXT,
  enviado_em    TEXT,
  revogado_em   TEXT,
  lembretes     INTEGER NOT NULL DEFAULT 0,
  ultimo_lembrete TEXT
);
CREATE INDEX IF NOT EXISTS idx_pedidos_email ON pedidos(email);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_criado ON pedidos(criado_em);

CREATE TABLE IF NOT EXISTS itens (
  id               TEXT PRIMARY KEY,
  pedido_id        TEXT NOT NULL,
  indice           INTEGER NOT NULL,
  nome_produto     TEXT,
  categoria        TEXT,
  especificacoes   TEXT,
  diferenciais     TEXT,
  plataforma       TEXT,               -- ml | shopee | ambos
  link_referencia  TEXT,               -- só referência; NUNCA buscar/raspar
  preenchido       INTEGER NOT NULL DEFAULT 0,
  criado_em        TEXT NOT NULL,
  atualizado_em    TEXT NOT NULL,
  UNIQUE(pedido_id, indice)
);
CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens(pedido_id);

CREATE TABLE IF NOT EXISTS eventos (
  chave           TEXT PRIMARY KEY,
  tipo            TEXT NOT NULL,
  order_id        TEXT,
  pedido_id       TEXT,
  resultado       TEXT,
  recebido_em     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  pedido_id  TEXT,
  email      TEXT NOT NULL,
  tipo       TEXT NOT NULL,
  assunto    TEXT NOT NULL,
  html       TEXT NOT NULL,
  texto      TEXT NOT NULL,
  dry_run    INTEGER NOT NULL,
  resposta   TEXT,
  criado_em  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_log (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL,
  path         TEXT,
  query        TEXT,
  content_type TEXT,
  status       INTEGER,
  resultado    TEXT,
  body_excerpt TEXT,
  webhook_event_type TEXT,
  order_id     TEXT,
  product_id   TEXT
);

-- Contador do título grátis: só hash do IP e o dia (UTC). Sem o texto do produto.
CREATE TABLE IF NOT EXISTS titulos_gratis (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  dia       TEXT NOT NULL,
  ip_hash   TEXT NOT NULL,
  criado_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_titulos_dia_ip ON titulos_gratis(dia, ip_hash);
