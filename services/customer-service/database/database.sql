-- Banco do customer-service: clientes, documentos, pendências, análises e eventos.

CREATE TABLE customer_statuses(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO customer_statuses (enumerator) VALUES
('PENDING_DOCUMENTS'),
('IN_ANALYSIS'),
('APPROVED'),
('REJECTED'),
('BLOCKED');

CREATE TABLE customers(
    id                              SERIAL PRIMARY KEY,
    customer_key                    CHAR(36) NOT NULL UNIQUE,
    customer_status_id              INTEGER NOT NULL REFERENCES customer_statuses(id),
    document_number                 CHAR(14) NOT NULL UNIQUE,
    name                            VARCHAR(255) NOT NULL,
    mother_name                     VARCHAR(255) NOT NULL,
    birth_date                      DATE NOT NULL,
    birth_city                      VARCHAR(255) NOT NULL,
    residence_city                  VARCHAR(255) NOT NULL,
    income_cents                    BIGINT NOT NULL,
    email                           VARCHAR(255) NOT NULL UNIQUE,
    phone                           VARCHAR(20) NOT NULL UNIQUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE customer_events(
    id                              SERIAL PRIMARY KEY,
    customer_id                     INTEGER NOT NULL REFERENCES customers(id),
    customer_status_id              INTEGER NOT NULL REFERENCES customer_statuses(id),
    reason                          VARCHAR(255),
    payload                         JSONB,
    event_at                        TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE document_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO document_types (enumerator) VALUES
('RG'),
('CNH'),
('PROOF_OF_ADDRESS'),
('BIRTH_CERTIFICATE'),
('CUSTODY_ORDER');

CREATE TABLE document_statuses(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO document_statuses (enumerator) VALUES
('IN_ANALYSIS'),
('PENDING'),
('APPROVED'),
('REJECTED');

CREATE TABLE documents(
    id                              SERIAL PRIMARY KEY,
    document_key                    CHAR(36) NOT NULL UNIQUE,
    customer_id                     INTEGER NOT NULL REFERENCES customers(id),
    document_type_id                INTEGER NOT NULL REFERENCES document_types(id),
    document_status_id              INTEGER NOT NULL REFERENCES document_statuses(id),
    document_number                 VARCHAR(50) NOT NULL,
    expiration_date                 DATE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE pendency_reasons(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO pendency_reasons (enumerator) VALUES
('ILLEGIBLE'),
('EXPIRED'),
('DATA_MISMATCH'),
('MISSING_PAGE');

CREATE TABLE document_pendencies(
    id                              SERIAL PRIMARY KEY,
    document_id                     INTEGER NOT NULL REFERENCES documents(id),
    pendency_reason_id              INTEGER NOT NULL REFERENCES pendency_reasons(id),
    description                     VARCHAR(255),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    resolved_at                     TIMESTAMP
);

CREATE TABLE analysis_types(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE
);

INSERT INTO analysis_types (enumerator) VALUES
('BUREAU_CPF'),
('DOCUMENT');

CREATE TABLE analyses(
    id                              SERIAL PRIMARY KEY,
    customer_id                     INTEGER NOT NULL REFERENCES customers(id),
    document_id                     INTEGER REFERENCES documents(id),
    analysis_type_id                INTEGER NOT NULL REFERENCES analysis_types(id),
    result                          VARCHAR(50) NOT NULL,
    payload                         JSONB,
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
