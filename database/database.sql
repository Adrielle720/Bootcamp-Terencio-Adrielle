-- Schema compartilhado pelos quatro servicos.
-- As tabelas entram junto com cada funcionalidade, via TDD.

CREATE TABLE customer(
    id                              SERIAL PRIMARY KEY,
    customer_key                    CHAR(36) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    mother_name                     VARCHAR(255) NOT NULL,
    birthdate                       DATE NOT NULL,
    birth_city                      VARCHAR(255) NOT NULL,
    residence_city                  VARCHAR(255) NOT NULL,
    income_cents                    BIGINT NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    phone                           VARCHAR(20) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(customer_key),
    UNIQUE(document_number),
    UNIQUE(email),
    UNIQUE(phone)
);

CREATE TABLE account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    UNIQUE(enumerator)
);

INSERT INTO account_status (enumerator) VALUES
('PENDING'),
('ACTIVE'),
('BLOCKED'),
('CANCELED'),
('CLOSING'),
('CLOSED');

-- Os ids são fixos porque os índices parciais logo abaixo dependem deles:
-- predicado de índice não aceita subconsulta.
CREATE TABLE holder_status(
    id                              INTEGER PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    UNIQUE(enumerator)
);

INSERT INTO holder_status (id, enumerator) VALUES
(1, 'INVITED'),
(2, 'ACTIVE'),
(3, 'DECLINED'),
(4, 'CANCELED'),
(5, 'LEFT'),
(6, 'PENDING_GUARDIANSHIP');

CREATE TABLE account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL,
    account_number                  VARCHAR(10) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    transfer_limit_cents            BIGINT,
    is_institution                  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key),
    UNIQUE(account_number)
);

-- Toda mudança de estado da conta, com quem fez e por quê (R4).
CREATE TABLE account_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    actor_customer_key              CHAR(36),
    reason                          VARCHAR(255),
    event_at                        TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- customer_id fica vazio enquanto o convidado ainda não é cliente:
-- o convite guarda só o contato (invited_email ou invited_phone).
CREATE TABLE account_holder(
    id                              SERIAL PRIMARY KEY,
    holder_key                      CHAR(36) NOT NULL,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    customer_id                     INTEGER REFERENCES customer(id),
    role                            VARCHAR(10) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES holder_status(id),
    invited_email                   VARCHAR(255),
    invited_phone                   VARCHAR(20),
    monthly_limit_cents             BIGINT,
    invited_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    joined_at                       TIMESTAMP,
    left_at                         TIMESTAMP,
    UNIQUE(holder_key),
    CHECK (customer_id IS NOT NULL OR invited_email IS NOT NULL OR invited_phone IS NOT NULL)
);

-- Uma pessoa só pode ter um vínculo aberto (INVITED, ACTIVE ou PENDING_GUARDIANSHIP).
CREATE UNIQUE INDEX one_open_holder_per_customer ON account_holder(customer_id) WHERE status_id IN (1, 2, 6);

-- Um convite pendente por contato de quem ainda não é cliente.
CREATE UNIQUE INDEX one_pending_invite_per_email ON account_holder(invited_email) WHERE status_id = 1 AND customer_id IS NULL;
CREATE UNIQUE INDEX one_pending_invite_per_phone ON account_holder(invited_phone) WHERE status_id = 1 AND customer_id IS NULL;

-- Só a conta de liquidação pode ficar negativa: ela representa o
-- dinheiro que entrou de fora em cada depósito.
CREATE TABLE account_balance(
    account_id                      INTEGER PRIMARY KEY REFERENCES account(id),
    balance_cents                   BIGINT NOT NULL,
    allows_negative                 BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK (allows_negative OR balance_cents >= 0)
);

CREATE TABLE deposit(
    id                              SERIAL PRIMARY KEY,
    deposit_key                     CHAR(36) NOT NULL,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    amount_cents                    BIGINT NOT NULL CHECK (amount_cents >= 1000),
    idempotency_key                 VARCHAR(64),
    request_hash                    CHAR(64),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(deposit_key),
    UNIQUE(account_id, idempotency_key)
);

CREATE TABLE transfer(
    id                              SERIAL PRIMARY KEY,
    transfer_key                    CHAR(36) NOT NULL,
    origin_account_id               INTEGER NOT NULL REFERENCES account(id),
    destination_account_id          INTEGER NOT NULL REFERENCES account(id),
    requested_by_id                 INTEGER NOT NULL REFERENCES customer(id),
    verified_holder_id              INTEGER NOT NULL REFERENCES account_holder(id),
    amount_cents                    BIGINT NOT NULL CHECK (amount_cents >= 1000),
    fee_cents                       BIGINT NOT NULL DEFAULT 0,
    adult_count                     INTEGER NOT NULL DEFAULT 0,
    idempotency_key                 VARCHAR(64) NOT NULL,
    request_hash                    CHAR(64) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(transfer_key),
    UNIQUE(origin_account_id, idempotency_key),
    CHECK (origin_account_id <> destination_account_id)
);

-- Ledger de partidas dobradas: os lançamentos de cada operação somam zero.
CREATE TABLE ledger_entry(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    deposit_id                      INTEGER REFERENCES deposit(id),
    transfer_id                     INTEGER REFERENCES transfer(id),
    entry_type                      VARCHAR(20) NOT NULL,
    amount_cents                    BIGINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    CHECK ((deposit_id IS NULL) <> (transfer_id IS NULL))
);

CREATE INDEX ledger_entry_by_account ON ledger_entry(account_id, created_at);

-- As duas contas da instituição: receitas (recebe as tarifas) e
-- liquidação (debitada em cada depósito). Sem titulares, saldo zero.
INSERT INTO account (account_key, account_number, name, status_id, is_institution) VALUES
('00000000-0000-0000-0000-000000000001', '00000000-0', 'Instituição - receitas', (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), TRUE),
('00000000-0000-0000-0000-000000000002', '00000000-1', 'Instituição - liquidação', (SELECT id FROM account_status WHERE enumerator = 'ACTIVE'), TRUE);

INSERT INTO account_balance (account_id, balance_cents, allows_negative) VALUES
((SELECT id FROM account WHERE account_key = '00000000-0000-0000-0000-000000000001'), 0, FALSE),
((SELECT id FROM account WHERE account_key = '00000000-0000-0000-0000-000000000002'), 0, TRUE);
