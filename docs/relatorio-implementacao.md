# Relatório de implementação

Estado do `main` em 12/10/2026, conferido contra a RFC em
[RFC-Banco-de-contas-conjuntas.pdf](RFC-Banco-de-contas-conjuntas.pdf). A suíte tem
**153 testes de integração**, todos verdes, inclusive num clone limpo do GitHub construído sem cache
(`docker compose build --no-cache`, venv novo, `pytest -v`). Depois da suíte, o
banco do transaction-service foi conferido direto: os lançamentos somam zero,
cada operação fecha em zero, todo saldo é a soma dos seus lançamentos e nenhum
saldo de cliente ficou negativo.

## Como subir e testar

```bash
docker compose up -d --build --wait
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -v
```

## O que está implementado e testado

| Serviço | Testes | O que cobre |
| --- | --- | --- |
| customer-service | 25 | Cadastro com birô (2001 a 2009), CPF repetido sem chamar o birô (verify do Mockserver), idempotência, cadastro concorrente do mesmo CPF, consulta com status e pendências, esteira de documentos (aprovado, pendente com motivo, pendência resolvida por documento novo, reprovado, 2011, 2012, 2013), cliente APPROVED com identidade (RG ou CNH) + comprovante |
| account-service | 62 | Abertura com convites por e-mail ou celular (inclusive para não clientes), 2010, 2021, 2022, 2024, 2032, 2033, idempotência; consulta da conta com saldo e titulares; convites, aceite, recusa e cancelamento (2025, 2026, 2028, 2030, 2031, 2033); concorrência (mesma pessoa, mesmo contato, última vaga); bloqueio e desbloqueio; limites; guarda de menores (mãe, avó com e sem documento de guarda, documento pendente, documento de guarda recusado que cancela o convite do menor, 2034 a 2038) |
| transaction-service | 46 | Depósito (idempotente, 2020, 2026, 2047); transferência com as faixas e fronteiras da tarifa, 2 a 6 adultos, a mesma tarifa com e sem menor na conta, transferência sem saldo que deixa os dois saldos iguais, receitas e liquidação, soma zero, 2040 a 2047, destino inexistente e CPF de fora com respostas idênticas, concorrência (saldo, mesma chave, transferências cruzadas), limite da conta, limite mensal do menor |
| statement-service | 11 | Extrato com resumo, ordem, paginação, filtros (tipo, sentido, titular, período), soma dos itens igual ao saldo, transferência recusada fora do extrato, 400 para período inválido, 404 2020, detalhe com lançamentos, 404 2050 |
| infraestrutura | 9 | `/` e `/health_check` dos quatro serviços e o Mockserver |

Também implementado, sem teste dedicado:

- 503 QIT002090 quando um serviço interno não responde. Os testes falam só HTTP e não derrubam containers.
- Menor que completa 18 anos vira MEMBER e a guarda termina (ENDED), com eventos. Testar exigiria manipular o relógio.
- Notificações gravadas no mesmo commit da operação (convite, entrada de titular, bloqueio, guarda decidida, depósito, transferência enviada e recebida). A RFC não define rota para lê-las.
- Eventos com payload em `customer_events`, `account_events`, `account_holder_events` e `guardianship_events`.

## O que não foi implementado

- Os itens que a RFC marca como próximo passo: boleto, estorno, divisão de despesas, empréstimo, encerramento (CLOSING e CLOSED) e saída de titulares.
- Rota para ler notificações.
- Reavaliar uma guarda que ficou em PENDING_DOCUMENTS. Hoje o responsável pede uma guarda nova quando o documento for aprovado.

## Divergências e escolhas para o time ajustar na RFC

**Modelo de dados**

1. `transfers.origin_account_number` foi acrescentada. O extrato precisa do número da conta de origem na transferência recebida, e o transaction-service não tem outro lugar de onde tirá-lo.
2. Os ids de `holder_statuses` são fixos, na ordem do prompt (INVITED=1, PENDING_GUARDIANSHIP=2, ACTIVE=3, DECLINED=4, CANCELED=5, LEFT=6), porque os índices únicos parciais usam esses ids. `guardianship_statuses` também tem ids fixos (APPROVED=3).
3. `documents.expiration_date` é opcional: certidão de nascimento não vence.

**Rotas internas**

4. O contexto (`/internal/accounts/{key}/context`) responde 404 QIT002020 quando quem pede não é titular ativo, em vez de devolver um campo dizendo isso.
5. Há uma rota interna a mais: `GET /internal/accounts/{key}/transactions/{transaction_key}`, para o detalhe do extrato. A `/entries` filtra o titular pelo parâmetro `made_by` (uma customer_key), e o statement-service traduz o `holder_key` público para ela.
6. O account-service lê o saldo pela `/entries?limit=1` do transaction-service.
7. Código novo QIT002014 (documento inexistente) para a rota interna `GET /internal/documents/{key}`.

**Regras**

8. Cancelar uma conta pendente deixa os convites CANCELED e o master LEFT. Sem isso, o índice de uma conta por pessoa não deixaria o master abrir outra.
9. Convidar numa conta cancelada: quem foi master recebe 409 QIT002026, e qualquer outra pessoa recebe 404 QIT002020 (R8).
10. Cancelar convite pedido por quem não é titular ativo da conta dá 404 QIT002030. Limite mensal pedido por quem não é titular ativo dá 404 QIT002020.
11. Uma conta só com o master e um menor fica ACTIVE quando a guarda é aprovada: o menor ativo ativa a conta pendente.
12. Guarda da mãe cujo nome não bate com o `mother_name` do menor dá 422 QIT002036, porque a RFC não tem código próprio para isso.
13. Documentos da guarda: documento inexistente, de outra pessoa ou do tipo errado não conta, e o que faltar vira 422 QIT002036. Documento ainda pendente deixa a guarda em PENDING_DOCUMENTS. Documento exigido recusado na análise recusa a guarda (REJECTED) e cancela o convite do menor, como no fluxo da avó; se era o último vínculo pendente de uma conta PENDING, a conta é cancelada. O documento de guarda pode ser do responsável ou do menor.
14. `GET /guardianships/{key}` é visível ao menor, ao responsável e a qualquer titular ativo da conta. Para os outros, 404 QIT002038.
15. Análise que devolve PENDING sem motivo grava a pendência como ILLEGIBLE. Resultado fora de APPROVED, PENDING ou REJECTED vira 502 QIT002013.
16. Cliente REJECTED (documento reprovado) não tem caminho de volta.
17. Conta BLOCKED ainda aceita convites. Só CANCELED, CLOSING e CLOSED recusam.
18. A `Idempotency-Key` é obrigatória só na transferência. É opcional em `POST /customers`, `POST /accounts` e depósito, e não existe em documentos, convites e guardas.
19. Extrato: `limit` acima de 100 dá 400 em vez de ser cortado em 100. `holder_key` que não é titular ativo devolve lista vazia. `total_out_cents` não inclui a tarifa, que vem em `total_fee_cents` (como no exemplo da RFC).
20. O limite mensal do menor não desconta transferências estornadas, porque o estorno não existe ainda.
21. Contrato do birô: o CPF vai só com os dígitos no caminho (`/bureau/cpf/12345678909`).

23. Status do cliente: cada documento enviado por quem ainda está em PENDING_DOCUMENTS grava o evento IN_ANALYSIS e volta a PENDING_DOCUMENTS (pendência ou documento faltando) ou segue para APPROVED ou REJECTED, como no diagrama da RFC. A análise é síncrona, então IN_ANALYSIS aparece só nos eventos, nunca numa consulta. Cliente já APPROVED que envia outro documento (a certidão, o termo de guarda) não muda de status, a não ser que o documento seja recusado.
24. A guarda passa por IN_ANALYSIS (evento) antes de APPROVED ou REJECTED. A volta de PENDING_DOCUMENTS para IN_ANALYSIS quando a pendência é resolvida não é automática: o responsável pede uma guarda nova.
25. `GET /customers/{key}/documents` mostra só as pendências abertas, como diz a rota. As resolvidas continuam no banco, com `resolved_at`.

**Inconsistências dentro da própria RFC**

Nos itens 26 a 28 o time decidiu (12/10) que vale o que o código faz. A RFC
deve ser corrigida nesses trechos.

26. **Decidido: `transfer_key`.** A tabela de rotas diz `transfer_key`, mas o passo 10 do fluxo "Transferir" e a tabela de testes ("o mesmo transaction_key") dizem `transaction_key`. A resposta da transferência usa `transfer_key`. No extrato, cada item continua usando `transaction_key`, porque pode ser depósito ou transferência. Corrigir na RFC: passo 10 do fluxo "Transferir" e a linha "Idempotência" da tabela de testes.
27. **Decidido: a cópia é feita no aceite.** O "Principal desafio" diz que nome, CPF e nascimento são "copiados no convite"; as regras de titulares e o fluxo do aceite dizem "no aceite". O código copia no aceite (e na abertura, para o master), porque no convite a pessoa pode ainda não ser cliente. Corrigir na RFC: o "Principal desafio" da transferência.
28. **Decidido: a transferência trava três saldos.** O passo 5 diz "trava os dois saldos", e o passo 9 grava três. O código trava origem, destino e receitas, em ordem crescente de id, porque o saldo de receitas também muda no mesmo commit. Corrigir na RFC: o passo 5 do fluxo "Transferir".
29. A RFC diz que o `conftest.py` guarda as funções que criam clientes e contas prontas. Elas estão em `tests/utils/` (customer_utils, account_utils, minor_utils), e o `conftest.py` cuida da espera pelos serviços.

**Processo**

30. O ciclo vermelho → verde com um commit por passo foi seguido até o limite por transferência (histórico do `main` até `51da739`). A migração para um banco por serviço, a esteira de documentos e a guarda entraram em commits maiores, com os testes escritos junto do código, e não em commits vermelhos separados.
