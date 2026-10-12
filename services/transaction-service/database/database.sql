-- Banco do transaction-service: todo dado de dinheiro mora aqui, para as
-- garantias dependerem de uma única transação local. Contas e clientes são
-- referenciados pela key pública do outro serviço (sem FK entre bancos).

CREATE TABLE balance_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO balance_types (enumerator) VALUES
('CUSTOMER'),
('FEE_REVENUE'),
('SETTLEMENT');

-- Só a conta de liquidação pode ficar negativa: ela representa o dinheiro
-- que entrou de fora em cada depósito.
CREATE TABLE account_balances(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL UNIQUE,
    balance_type_id                 INTEGER NOT NULL REFERENCES balance_types(id),
    balance_cents                   BIGINT NOT NULL DEFAULT 0,
    allows_negative                 BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK (allows_negative OR balance_cents >= 0)
);

CREATE TABLE deposits(
    id                              SERIAL PRIMARY KEY,
    deposit_key                     CHAR(36) NOT NULL UNIQUE,
    account_key                     CHAR(36) NOT NULL,
    depositor_customer_key          CHAR(36) NOT NULL,
    depositor_name                  VARCHAR(255) NOT NULL,
    amount_cents                    BIGINT NOT NULL CHECK (amount_cents >= 1000),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE INDEX deposits_by_account ON deposits(account_key, created_at);

CREATE TABLE transfers(
    id                              SERIAL PRIMARY KEY,
    transfer_key                    CHAR(36) NOT NULL UNIQUE,
    origin_account_key              CHAR(36) NOT NULL,
    destination_account_key         CHAR(36) NOT NULL,
    requester_customer_key          CHAR(36) NOT NULL,
    requester_name                  VARCHAR(255) NOT NULL,
    origin_account_number           VARCHAR(10) NOT NULL,
    destination_account_number      VARCHAR(10) NOT NULL,
    verified_holder_name            VARCHAR(255) NOT NULL,
    amount_cents                    BIGINT NOT NULL CHECK (amount_cents >= 1000),
    fee_cents                       BIGINT NOT NULL,
    adult_count                     INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK (origin_account_key <> destination_account_key)
);

CREATE INDEX transfers_by_origin ON transfers(origin_account_key, created_at);
CREATE INDEX transfers_by_destination ON transfers(destination_account_key, created_at);

CREATE TABLE entry_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO entry_types (enumerator) VALUES
('SETTLEMENT_DEBIT'),
('DEPOSIT_CREDIT'),
('TRANSFER_DEBIT'),
('FEE_DEBIT'),
('TRANSFER_CREDIT'),
('FEE_CREDIT');

-- Ledger de partidas dobradas: os lançamentos de cada operação somam zero.
CREATE TABLE ledger_entries(
    id                              SERIAL PRIMARY KEY,
    account_balance_id              INTEGER NOT NULL REFERENCES account_balances(id),
    deposit_id                      INTEGER REFERENCES deposits(id),
    transfer_id                     INTEGER REFERENCES transfers(id),
    entry_type_id                   INTEGER NOT NULL REFERENCES entry_types(id),
    amount_cents                    BIGINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK ((deposit_id IS NULL) <> (transfer_id IS NULL))
);

CREATE INDEX ledger_entries_by_balance ON ledger_entries(account_balance_id, created_at);

CREATE TABLE fee_tiers(
    id                              SERIAL PRIMARY KEY,
    min_amount_cents                BIGINT NOT NULL,
    max_amount_cents                BIGINT,
    base_fee_cents                  BIGINT NOT NULL
);

INSERT INTO fee_tiers (min_amount_cents, max_amount_cents, base_fee_cents) VALUES
(1000, 9999, 50),
(10000, 29999, 200),
(30000, 99999, 500),
(100000, 499999, 900),
(500000, NULL, 1200);

CREATE TABLE notification_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO notification_types (enumerator) VALUES
('DEPOSIT_RECEIVED'),
('TRANSFER_SENT'),
('TRANSFER_RECEIVED');

CREATE TABLE notifications(
    id                              SERIAL PRIMARY KEY,
    notification_key                CHAR(36) NOT NULL UNIQUE,
    customer_key                    CHAR(36) NOT NULL,
    account_key                     CHAR(36) NOT NULL,
    notification_type_id            INTEGER NOT NULL REFERENCES notification_types(id),
    payload                         JSONB,
    read_at                         TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- scope = conta + rota: a mesma chave pode ser usada em contas diferentes.
CREATE TABLE idempotency_records(
    id                              SERIAL PRIMARY KEY,
    scope                           VARCHAR(255) NOT NULL,
    idempotency_key                 VARCHAR(64) NOT NULL,
    request_hash                    CHAR(64) NOT NULL,
    response_status                 INTEGER NOT NULL,
    response_body                   JSONB NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(scope, idempotency_key)
);

-- As duas contas da instituição: receitas (recebe as tarifas) e liquidação
-- (debitada em cada depósito). Não existem no account-service, então nunca
-- são destino de transferência.
INSERT INTO account_balances (account_key, balance_type_id, balance_cents, allows_negative) VALUES
('00000000-0000-0000-0000-000000000001', (SELECT id FROM balance_types WHERE enumerator = 'FEE_REVENUE'), 0, FALSE),
('00000000-0000-0000-0000-000000000002', (SELECT id FROM balance_types WHERE enumerator = 'SETTLEMENT'), 0, TRUE);
