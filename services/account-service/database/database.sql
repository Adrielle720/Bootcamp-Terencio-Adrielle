-- Banco do account-service: contas, titulares, guardas, eventos e notificações de conta.
-- Clientes moram no customer-service: aqui só a customer_key (sem FK entre bancos).

CREATE TABLE account_statuses(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO account_statuses (enumerator) VALUES
('PENDING'),
('ACTIVE'),
('BLOCKED'),
('CANCELED'),
('CLOSING'),
('CLOSED');

CREATE TABLE accounts(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL UNIQUE,
    account_number                  VARCHAR(10) NOT NULL UNIQUE,
    account_status_id               INTEGER NOT NULL REFERENCES account_statuses(id),
    name                            VARCHAR(255) NOT NULL,
    transfer_limit_cents            BIGINT,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE account_events(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES accounts(id),
    account_status_id               INTEGER NOT NULL REFERENCES account_statuses(id),
    actor_customer_key              CHAR(36),
    reason                          VARCHAR(255),
    payload                         JSONB,
    event_at                        TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE holder_roles(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO holder_roles (enumerator) VALUES
('MASTER'),
('MEMBER'),
('MINOR');

-- Ids fixos: os índices únicos parciais abaixo dependem deles, porque o
-- predicado de um índice não aceita subconsulta.
CREATE TABLE holder_statuses(
    id                              INTEGER PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO holder_statuses (id, enumerator) VALUES
(1, 'INVITED'),
(2, 'PENDING_GUARDIANSHIP'),
(3, 'ACTIVE'),
(4, 'DECLINED'),
(5, 'CANCELED'),
(6, 'LEFT');

-- customer_key fica vazia enquanto o convidado ainda não é cliente: o
-- convite guarda só o contato. Nome, CPF e nascimento são copiados no
-- aceite e nunca mudam depois.
CREATE TABLE account_holders(
    id                              SERIAL PRIMARY KEY,
    account_holder_key              CHAR(36) NOT NULL UNIQUE,
    account_id                      INTEGER NOT NULL REFERENCES accounts(id),
    customer_key                    CHAR(36),
    holder_role_id                  INTEGER NOT NULL REFERENCES holder_roles(id),
    holder_status_id                INTEGER NOT NULL REFERENCES holder_statuses(id),
    invited_email                   VARCHAR(255),
    invited_phone                   VARCHAR(20),
    name                            VARCHAR(255),
    document_number                 CHAR(14),
    birth_date                      DATE,
    monthly_limit_cents             BIGINT,
    invited_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    joined_at                       TIMESTAMP,
    left_at                         TIMESTAMP,
    CHECK (customer_key IS NOT NULL OR invited_email IS NOT NULL OR invited_phone IS NOT NULL)
);

-- Uma conta por pessoa (INVITED, PENDING_GUARDIANSHIP ou ACTIVE), mantendo quem saiu no histórico.
CREATE UNIQUE INDEX one_open_holder_per_customer ON account_holders(customer_key) WHERE holder_status_id IN (1, 2, 3);

-- Um convite pendente por contato de quem ainda não é cliente.
CREATE UNIQUE INDEX one_pending_invite_per_email ON account_holders(invited_email) WHERE holder_status_id = 1 AND customer_key IS NULL;
CREATE UNIQUE INDEX one_pending_invite_per_phone ON account_holders(invited_phone) WHERE holder_status_id = 1 AND customer_key IS NULL;

CREATE INDEX account_holders_by_account ON account_holders(account_id);

CREATE TABLE account_holder_events(
    id                              SERIAL PRIMARY KEY,
    account_holder_id               INTEGER NOT NULL REFERENCES account_holders(id),
    holder_status_id                INTEGER NOT NULL REFERENCES holder_statuses(id),
    holder_role_id                  INTEGER NOT NULL REFERENCES holder_roles(id),
    reason                          VARCHAR(255),
    payload                         JSONB,
    event_at                        TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE kinship_degrees(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    requires_custody_order          BOOLEAN NOT NULL
);

INSERT INTO kinship_degrees (enumerator, requires_custody_order) VALUES
('MOTHER', FALSE),
('FATHER', FALSE),
('GRANDPARENT', TRUE),
('SIBLING', TRUE),
('UNCLE_AUNT', TRUE),
('LEGAL_GUARDIAN', TRUE);

CREATE TABLE guardianship_statuses(
    id                              INTEGER PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO guardianship_statuses (id, enumerator) VALUES
(1, 'PENDING_DOCUMENTS'),
(2, 'IN_ANALYSIS'),
(3, 'APPROVED'),
(4, 'REJECTED'),
(5, 'ENDED');

CREATE TABLE guardianships(
    id                              SERIAL PRIMARY KEY,
    guardianship_key                CHAR(36) NOT NULL UNIQUE,
    minor_account_holder_id         INTEGER NOT NULL REFERENCES account_holders(id),
    guardian_account_holder_id      INTEGER NOT NULL REFERENCES account_holders(id),
    kinship_degree_id               INTEGER NOT NULL REFERENCES kinship_degrees(id),
    guardianship_status_id          INTEGER NOT NULL REFERENCES guardianship_statuses(id),
    requested_at                    TIMESTAMP NOT NULL DEFAULT(NOW()),
    decided_at                      TIMESTAMP
);

-- Um responsável aprovado por menor.
CREATE UNIQUE INDEX one_approved_guardianship_per_minor ON guardianships(minor_account_holder_id) WHERE guardianship_status_id = 3;

CREATE TABLE guardianship_document_purposes(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO guardianship_document_purposes (enumerator) VALUES
('GUARDIAN_ID'),
('MINOR_BIRTH_CERTIFICATE'),
('CUSTODY_ORDER');

CREATE TABLE guardianship_documents(
    id                              SERIAL PRIMARY KEY,
    guardianship_id                 INTEGER NOT NULL REFERENCES guardianships(id),
    guardianship_document_purpose_id INTEGER NOT NULL REFERENCES guardianship_document_purposes(id),
    document_key                    CHAR(36) NOT NULL,
    confirmed_at                    TIMESTAMP
);

CREATE TABLE guardianship_events(
    id                              SERIAL PRIMARY KEY,
    guardianship_id                 INTEGER NOT NULL REFERENCES guardianships(id),
    guardianship_status_id          INTEGER NOT NULL REFERENCES guardianship_statuses(id),
    reason                          VARCHAR(255),
    payload                         JSONB,
    event_at                        TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE notification_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO notification_types (enumerator) VALUES
('INVITATION'),
('HOLDER_JOINED'),
('ACCOUNT_BLOCKED'),
('GUARDIANSHIP_DECIDED');

CREATE TABLE notifications(
    id                              SERIAL PRIMARY KEY,
    notification_key                CHAR(36) NOT NULL UNIQUE,
    customer_key                    CHAR(36) NOT NULL,
    account_id                      INTEGER NOT NULL REFERENCES accounts(id),
    notification_type_id            INTEGER NOT NULL REFERENCES notification_types(id),
    payload                         JSONB,
    read_at                         TIMESTAMP,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

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
