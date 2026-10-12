# Banco Tera — contas conjuntas

Um banco só de contas conjuntas, para grupos que dividem despesas: de 2 a 6
titulares por conta, uma conta por pessoa, convites por e-mail ou celular,
depósito gratuito, transferência com tarifa por faixa e extrato como livro de
registros. A especificação completa está na RFC do time:
[docs/RFC-Banco-de-contas-conjuntas.pdf](docs/RFC-Banco-de-contas-conjuntas.pdf)
(o texto-fonte, editável, está em [docs/RFC-Banco-de-contas-conjuntas.md](docs/RFC-Banco-de-contas-conjuntas.md)).

## Subir e testar

Pré-requisitos: Docker com Compose e Python 3.11.

```bash
docker compose up -d --build --wait

python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt        # Windows: .venv\Scripts\pip
.venv/bin/pytest -v                                  # Windows: .venv\Scripts\pytest -v
```

Nenhum passo manual: o `.env` é opcional (os padrões estão no
`docker-compose.yml` e em `.env.example`). Os testes esperam os serviços
responderem `/health_check` antes de começar.

- Mudou um `database.sql`? `docker compose down -v` (o banco só roda o `.sql` ao nascer).
- Mudou um `requirements.txt`? `docker compose build --no-cache`.

## Como é montado

| Serviço | Porta | Banco | O que faz |
| --- | --- | --- | --- |
| customer-service | 8001 | customer-db | Cadastro, birô de CPF, esteira de documentos |
| account-service | 8002 | account-db | Contas, convites, titulares, guarda de menores, bloqueio, limites |
| transaction-service | 8003 | transaction-db | Saldos, depósitos, transferências, tarifa, ledger |
| statement-service | 8004 | nenhum | Extrato, composto a partir do account e do transaction |
| mock | 1080 | — | Mockserver: birô (`/bureau`) e análise de documentos (`/document-analysis`) |

Cada serviço segue as camadas do `bootcamp-base-api` (resource → controller →
repository → model, schema JSON na entrada e DTO na saída) e só fala com os
outros por HTTP, em rotas `/internal/...` protegidas pelo `INTERNAL-TOKEN`.
Todo dado de dinheiro mora no banco do transaction-service, para as garantias
dependerem de uma única transação local.

## Testes

Os testes ficam em `tests/`, fora dos serviços, e falam só HTTP (nenhum
importa `src/`). Cada teste cria os próprios dados pela API, com CPF, e-mail
e celular únicos, então o banco não precisa ser limpo e a ordem não importa.

O que foi implementado, as escolhas onde a RFC não definia e as divergências
estão em [docs/relatorio-implementacao.md](docs/relatorio-implementacao.md).
