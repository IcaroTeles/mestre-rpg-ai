# DEVELOPMENT_LOG

## Etapa 1 - Fundacao do Mestre RPG AI

- **Data:** 2026-11-20
- **Status:** CONCLUIDA
- **Objetivos:** criar a base web, configuracoes, diagnostico Ollama, frontend inicial, scripts, documentacao e testes.

### Implementacao

- Estrutura modular criada em `app/`, `tests/`, `scripts/`, `data/` e `project_docs/`.
- FastAPI configurada com lifespan, pagina inicial, saude geral e saude do Ollama.
- Cliente Ollama implementado com verificacao de `/api/version`, `/api/tags` e instalacao do modelo.
- Ambiente Python 3.12.10 instalado e ambiente virtual criado em `.venv`.

### Dependencias adicionadas

- FastAPI, Uvicorn, HTTPX, Pydantic Settings, Jinja2, Pytest e pytest-asyncio.

### Validacao

- Ambiente instalado e validado com Python 3.12.10.
- Dependencias instaladas no ambiente virtual `.venv`.
- Resultado de `pytest -v`: 7 testes aprovados, 0 falhas.
- Servidor iniciado efetivamente com `python run.py` em `127.0.0.1:8000`.
- Navegador validou `http://127.0.0.1:8000/` com titulo "Mestre RPG AI" e estados visuais.
- `GET /` respondeu HTTP 200.
- `GET /api/health` respondeu `"status": "ok"`.
- `GET /api/health/ollama` respondeu no ambiente real com Ollama disponivel e modelo `gemma3:12b` instalado.
- Os testes com mocks comprovaram Ollama indisponivel e modelo ausente sem impedir o servidor.
- `data/logs/app.log` foi criado e registrou inicializacao, encerramento e falha simulada de Ollama.

### Erros encontrados e solucoes

- O sistema nao possuia Python 3.12 inicialmente; Python 3.12.10 foi instalado e o `.venv` foi recriado com essa versao.
- Nenhum erro de implementacao impediu a aprovacao dos testes.

### Decisoes tecnicas

- Pydantic Settings usa variaveis de ambiente com nomes diretos, como `HOST`, `PORT` e `OLLAMA_MODEL`.
- O arquivo YAML permanece como exemplo nesta etapa; nao foi introduzida carga YAML adicional.
- O Ollama nao participa do lifespan, garantindo inicializacao independente.

### Pendencias

- Nenhuma pendencia da Etapa 1.
- Etapa 2 nao iniciada.

## Microetapa 2.1 - Infraestrutura do banco de dados

- **Data:** 2026-11-20
- **Status:** CONCLUIDA
- **Objetivos:** criar infraestrutura inicial SQLite, SQLAlchemy e Alembic sem modelos ou endpoints de dados.

### Implementacao

- Criado `app/core/database.py` com engine SQLAlchemy, sessao, contexto de fechamento e consulta de disponibilidade.
- Criada `app/core/database_models.py` com uma base Declarative vazia.
- Criado `alembic.ini` e o pacote `migrations/`, sem revisoes ou tabelas.
- Adicionado caminho configuravel para `data/mestre_rpg.db`, com criacao automatica do diretorio.
- `/api/health` passou a informar o estado do banco como `ok` ou `degraded`, sem impedir o servidor.
- Nenhuma tabela de usuario, campanha, autenticacao ou permissao foi criada.
- O comportamento de Ollama permaneceu separado e sem alteracoes.

### Dependencias adicionadas

- SQLAlchemy >=2.0,<3.0
- Alembic >=1.14,<2.0

### Validacao

- Resultado de `pytest -v`: 10 testes aprovados, 0 falhas.
- Testes de banco em memoria, banco temporario em disco e gerenciamento de sessao aprovados.
- `alembic current` confirmou o contexto SQLite.
- `alembic history` confirmou a configuracao sem revisoes criadas.
- Servidor iniciado com `python run.py` em `127.0.0.1:8000`.
- `GET /` respondeu HTTP 200.
- `GET /api/health` respondeu status geral `ok` e banco `ok`.
- `GET /api/health/ollama` permaneceu funcional.
- Arquivo SQLite criado em `data/mestre_rpg.db`.

### Erros encontrados e solucoes

- A primeira versao do teste esperava que `Session.is_active` fosse falso apos fechamento; o comportamento observado mostrou que essa propriedade nao representa o fechamento. O teste foi corrigido para usar `session_scope()` e verificar encerramento da transacao.

### Decisoes tecnicas

- SQLAlchemy usa URL SQLite configuravel e URL relativa ao projeto por padrao.
- Em banco temporario, strings `sqlite:///:memory:` usam pool adequado.
- Alembic reutiliza a configuracao central da aplicacao.
- Nenhuma migracao foi criada ou aplicada porque esta microetapa nao possui tabelas.

### Pendencias

- Nenhuma pendencia da Microetapa 2.1.
- Microetapa 2.2 nao iniciada.

## Auditoria tecnica da Microetapa 2.1

- **Data:** 2026-11-20
- **Status:** CONCLUIDA
- **Resultado:** APROVADA PARA MERGE, sujeita a existencia segura da branch destino.

### Problemas encontrados e classificacao

- **Media:** `session_scope()` fechava a sessao mas nao implementava rollback ou separacao explicita entre leitura e escrita.
- **Media:** falta de transacao transacional com commit explicito e rollback.
- **Media:** ausencia de PRAGMA foreign keys e busy_timeout por conexao.
- **Baixa:** falta de estrategia WAL para banco SQLite em disco.
- **Media:** `/api/health` executava SQLAlchemy em handler assincrono.
- **Alta para operacoes futuras:** Alembic ignorava uma URL temporaria fornecida pela configuracao de migracao.
- **Media:** cobertura insuficiente para falhas de conexao, excecoes, isolamento e descarte do engine.
- **Baixa:** configuracao do Alembic emitia aviso de path separator.

### Correcoes realizadas

- `session_scope()` passou a operar sem commit automatico, com rollback e encerramento garantido.
- Adicionado `transaction_scope()` com commit em sucesso e rollback em excecao.
- SQLAlchemy passou a ativar foreign keys, busy timeout e, em disco, WAL.
- Banco em memoria continua com StaticPool e nao ativa WAL.
- `/api/health` passou a ser sincronizado e reporta banco degradado sem expor detalhes internos.
- Alembic passou a respeitar uma URL fornecida em `Config`; usa a URL central apenas como fallback.
- Adicionado `path_separator = os` ao `alembic.ini`.
- Ampliados testes de memoria, disco, diretorios, sessoes, rollback, commit, isolamento, indisponibilidade, pragmas e Alembic.

### Validacao

- Suíte ampliada: 21 testes aprovados, 0 reprovados.
- Python 3.12.10 no Windows validado.
- `alembic current` executado sem alterar dados.
- Servidor iniciado com `python run.py`.
- `GET /` respondeu HTTP 200.
- `GET /api/health` respondeu status geral `ok` e banco `ok`.
- `GET /api/health` com banco indisponivel foi testado como `degraded`.
- `/api/health/ollama` manteve o estado separado e funcional.
- Inspecao SQLite confirmou que nenhuma tabela de negocio foi criada.

### Decisoes tecnicas

- Read-only e escritas possuem ciclos separados para evitar commits implicitos.
- PRAGMA foreign_keys e busy_timeout sao aplicados em toda conexao SQLite.
- WAL e aplicado apenas em banco em disco.
- Falhas de banco sao ocultadas no endpoint e representadas por estado degradado.
- Nenhuma migracao funcional foi criada.

### Operacoes Git

- Auditoria realizada na branch `microetapa-2.1`.
- Nenhum comando destrutivo ou force push utilizado.
- A branch destino correta foi confirmada como `v0.1`; nao existe branch `V.01`.
- Commit de origem da Microetapa 2.1: `1eba1fc`.
- Commit final da auditoria antes do merge: `fda2d07`.
- Integracao validada em `v0.1` pelo commit de merge `b8a0fe2`.

## Microetapa 2.2 - Cadastro e gerenciamento interno de usuarios

- **Data:** 2026-11-20
- **Branch:** `microetapa-2.2`
- **Status:** PRONTO PARA AUDITORIA
- **Objetivos:** implementar modelo, schemas, repository, service, migracao e testes de usuarios sem HTTP ou autenticacao.

### Implementacao

- Criado `app/core/user_engine/` com schemas, repository e service.
- Adicionado modelo SQLAlchemy `User` reutilizando `Base`.
- Campos incluem UUID, username, email, display_name, is_active, created_at e updated_at.
- Username e email sao normalizados em minusculas.
- Criada validacao para tamanhos e caracteres permitidos.
- Criada migracao Alembic `7dce4f9a21b1` para a tabela users.
- Service oferece criar, buscar, listar, atualizar, desativar e reativar usuarios.

### Dependencias

- Nenhuma dependencia nova; Pydantic existente faz a validacao basica de e-mail.

### Validacao

- Suíte completa inicial: 46 testes aprovados, 0 reprovados.
- Cobertos: validacoes, normalizacao, duplicidade, buscas, paginacao, atualizacao, estados, persistencia, rollback e migracao.
- Testes da Etapa 1 e das Microetapas 2.1 e 2.2 integrados na mesma suite.
- Servidor iniciado em `127.0.0.1:8000`; `/`, `/api/health` e `/api/health/ollama` responderam corretamente.
- Nenhuma dependencia externa nova foi necessaria.

### Pendencias

- Revisao final de imports e diff.
- Inicializacao real do servidor e rotas existentes.
- Publicacao da branch microetapa-2.2.
- Microetapa 2.3 nao iniciada.

## Microetapa 2.3 - Autenticacao e sessoes

- **Data:** 2026-11-20
- **Status:** EM ANDAMENTO
- **Status:** PRONTO PARA AUDITORIA
- **Branch:** microetapa-2.3
- **Baseline:** v0.1 em 9535c1443ea438981829f07f769be6b9ecdd04fc ou descendente autorizado.

### Implementacao

- Senhas Argon2id via pwdlib.
- Modelo User recebeu password_hash nullable.
- Criada entidade UserSession com token_hash e csrf_token_hash.
- Implementados auth repository, service, schemas e dependencias.
- Implementados POST /api/auth/login, GET /api/auth/me e POST /api/auth/logout.
- Cookie mestre_session usa atributos HttpOnly, SameSite=Lax e Secure fora do ambiente local.
- CSRF exige X-CSRF-Token e valida origin para operacoes de estado.

### Limites conhecidos

- Rate limiting persistente nao foi implementado nesta etapa.
- Conta provisionamento publico nao foi implementado.
- Exposicao publica antes da 2.4 exige implementar limitacao persistente de tentativas.

### Dependencias

- pwdlib[argon2] >=0.2,<1.0

### Validacao final

- Suíte completa: 74 testes aprovados, 0 reprovados.
- Upgrade head, downgrade para 8e1a4b2c53d7 e reupgrade head aprovados em banco temporario.
- Servidor iniciado em 127.0.0.1:8000.
- `/`, `/api/health` e `/api/health/ollama` responderam corretamente.
- Rate limiting persistente ficou registrado como limitacao para exposicao publica.

## Correcoes apos auditoria da Microetapa 2.2

- **Data:** 2026-11-20
- **Commit auditado:** `717794830db74295358e9a03c9b95a99f10d4846`
- **Status:** PRONTO PARA NOVA AUDITORIA

### Correcoes implementadas

- Substituidos os indices convencionais por indices unicos funcionais em `LOWER(username)` e `LOWER(email)`.
- Atualizado o modelo SQLAlchemy para refletir as expressões funcionais.
- Atualizada a revisao inicial da tabela users.
- Criada revisao Alembic corretiva `8e1a4b2c53d7` para bancos ja migrados.
- O downgrade corretivo restaura indices convencionais antes da retirada da tabela pela revisao base.
- A fixture de usuarios passou a executar `alembic upgrade head` em banco SQLite temporario.
- Mantido o teste separado de upgrade/downgrade.
- Adicionados testes diretos de insercao com `Jogador`/`jogador` e `Mestre@exemplo.com`/`mestre@exemplo.com`.
- Documentada a limitacao da validacao basica de e-mail; nao foi adicionada dependencia nova.

### Validacao

- Suíte completa: 49 testes aprovados, 0 reprovados.
- Testes do UserService executados sobre estrutura criada pela migracao real.
- Insercoes diretas no SQLite rejeitadas para duplicidade case-insensitive.
- Migração upgrade head e downgrade base validadas em banco temporario.

## Correcao final do historico Alembic da Microetapa 2.2

- **Data:** 2026-11-20
- **Status:** PRONTO PARA NOVA AUDITORIA
- A revisao original `7dce4f9a21b1` foi restaurada com indices convencionais.
- A revisao `8e1a4b2c53d7` permanece como conversao para indices funcionais LOWER.
- Bancos novos chegam diretamente ao estado head com unicidade case-insensitive.
- Bancos ja existentes aplicam a revisao corretiva sem alterar dados.
- Dados conflitantes fazem a conversao falhar antes da substituicao dos indices e sem apagar registros.
- Testes cobrem upgrade intermediario, preservacao de dados, indices funcionais, downgrade/reupgrade e falha segura.
