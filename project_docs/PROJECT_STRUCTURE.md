# PROJECT_STRUCTURE

## Estrutura

- `app/main.py`: aplicacao FastAPI, lifespan, rotas, templates, arquivos estaticos e tratamento de erros.
- `app/config.py`: configuracoes Pydantic Settings.
- `app/core/ai_engine/ollama_client.py`: consultas locais de versao e modelos.
- `app/frontend/`: HTML, CSS e JavaScript da pagina inicial.
- `configuration/settings.example.yaml`: referencia das configuracoes.
- `data/`: dados locais e logs; e protegido pelo `.gitignore`.
- `scripts/`: scripts BAT para iniciar e orientar encerramento.
- `tests/`: testes de importacao, pagina, saude e Ollama.
- `project_docs/`: contexto permanente da implementacao.
- `run.py`: ponto de entrada Uvicorn.
- `app/core/database.py`: engine, sessoes e verificacao SQLAlchemy do SQLite.
- `app/core/database_models.py`: base Declarative vazia para modelos futuros.
- `alembic.ini` e `migrations/`: configuracao e controle de migracoes.
- `tests/test_database.py`: testes temporarios de disponibilidade, arquivo e sessoes SQLite.

## Alteracoes da Etapa 1

- Criados todos os modulos Python, arquivos estaticos, testes e scripts BAT listados acima.
- Criados `.env.example`, `.gitignore`, `requirements.txt` e `README.md`.
- Criados os diretórios de dados e backups exigidos pela estrutura.
- Criado `.venv` com Python 3.12.10 para desenvolvimento local.

## Dependencias

## Auditoria da Microetapa 2.1

- `app/core/database.py`: corrigido para usar SQLAlchemy URL parsing, SQLite PRAGMA por conexao, WAL em disco, StaticPool em memoria e ciclos de sessao com rollback.
- `app/main.py`: `/api/health` passou a ser uma rota sincronizada curta e a reportar banco degradado sem alterar o estado de Ollama.
- `migrations/env.py`: aceita URL temporaria definida pelo Alembic, mantendo a configuracao central como fallback.
- `tests/test_database.py`: ampliado para cobrir rollback, commit, isolamento, indisponibilidade, pragmas, WAL, diretorios e Alembic.

SQLAlchemy 2.x e Alembic foram adicionados na Microetapa 2.1.

FastAPI, Uvicorn, HTTPX, Pydantic Settings, Jinja2 e Pytest.

## Microetapa 2.2 - Usuarios

- `app/core/database_models.py`: modelo declarativo `User` reutilizando `Base`.
- `app/core/user_engine/user_schemas.py`: schemas de entrada e saida.
- `app/core/user_engine/user_repository.py`: consultas e persistencia SQLAlchemy.
- `app/core/user_engine/user_service.py`: validacoes, duplicidade, transacoes e estados.
- `migrations/versions/20261120_0215_create_users.py`: migracao da tabela users.
- `tests/test_users.py`: validacoes, unicidade, persistencia, estados e migracao.

## Microetapa 2.3 - Autenticacao

- `app/core/auth_engine/`: hashes, repository, service, schemas e dependencias.
- `app/api/routes/auth.py`: login, identificacao e logout.
- `migrations/versions/20261120_0245_auth_sessions.py`: password_hash e user_sessions.
- `tests/test_auth.py`: senhas, login, cookies, CSRF, sessoes e migracoes.

## Microetapa 2.4 - Convites

- `app/core/database_models.py`: entidade `UserInvite`.
- `app/core/invite_engine/`: schemas, repositorio e servico de convites.
- `app/api/routes/invites.py`: aceitação pública protegida por origem.
- `migrations/versions/20261120_0310_user_invites.py`: tabela e indices de convites.
- `tests/test_invites.py`: criação, aceite, revogacao, concorrencia e migracao.

## Correcoes da auditoria da Microetapa 2.2

- `migrations/versions/20261120_0235_case_insensitive_users.py`: converte unicidade para indices funcionais de LOWER.
- `tests/test_users.py`: fixture usa Alembic e inclui insercoes SQLite case-insensitive.

Nenhuma dependencia nova foi necessaria; Pydantic existente valida o formato basico de e-mail.

## Microetapa 2.5.1 - Campanhas

- `app/core/campaign_engine/campaign_types.py`: estados, classificacoes de duracao e frequencias.
- `app/core/campaign_engine/campaign_schemas.py`: validacao e serializacao de campanhas e eventos de auditoria.
- `app/core/campaign_engine/campaign_repository.py`: consultas e persistencia SQLAlchemy.
- `app/core/campaign_engine/campaign_service.py`: criacao, propriedade, atualizacao, auditoria e transicoes.
- `app/core/database_models.py`: modelos `Campaign` e `CampaignAuditEvent`; `UserInvite.campaign_id` continua sem FK.
- `app/api/routes/campaigns.py`: rotas autenticadas `/api/campaigns`; escritas exigem origem confiavel e CSRF.
- `app/core/auth_engine/auth_dependencies.py`: verificacoes compartilhadas de origem e CSRF, usadas pelas rotas de campanha.
- `migrations/versions/20261120_0445_campaign_foundation.py`: tabelas, constraints, FKs e indices de campanhas/auditoria.
- `tests/test_campaigns.py`: regras, autenticacao, transicoes, auditoria, integridade e round-trip de migracao.
