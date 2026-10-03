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

CREATE TABLE holder_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    UNIQUE(enumerator)
);

INSERT INTO holder_status (enumerator) VALUES
('INVITED'),
('ACTIVE'),
('DECLINED'),
('CANCELED'),
('LEFT');

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

CREATE TABLE account_holder(
    id                              SERIAL PRIMARY KEY,
    holder_key                      CHAR(36) NOT NULL,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    role                            VARCHAR(10) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES holder_status(id),
    guardian_holder_id              INTEGER REFERENCES account_holder(id),
    monthly_limit_cents             BIGINT,
    invited_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    joined_at                       TIMESTAMP,
    left_at                         TIMESTAMP,
    UNIQUE(holder_key)
);

CREATE TABLE account_balance(
    account_id                      INTEGER PRIMARY KEY REFERENCES account(id),
    balance_cents                   BIGINT NOT NULL CHECK (balance_cents >= 0),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE deposit(
    id                              SERIAL PRIMARY KEY,
    transaction_key                 CHAR(36) NOT NULL,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    amount_cents                    BIGINT NOT NULL CHECK (amount_cents >= 1000),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(transaction_key)
);

CREATE TABLE ledger_entry(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    deposit_id                      INTEGER REFERENCES deposit(id),
    entry_type                      VARCHAR(20) NOT NULL,
    amount_cents                    BIGINT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
