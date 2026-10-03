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
