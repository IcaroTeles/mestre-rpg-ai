# Mestre RPG AI

Versao: `v0.1`

Fundacao web para uma aplicacao de RPG conduzida por IA, iniciada na Etapa 1.

## Requisitos

- Python 3.12
- SQLAlchemy 2.x
- Alembic
- Ollama local opcional em `http://127.0.0.1:11434`
- Modelo configurado: `gemma3:12b`

## Instalacao no Windows

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

## Execucao

```bat
python run.py
```

Ou:

```bat
scripts\start_server.bat
```

A interface sera aberta em `http://127.0.0.1:8000/`.

## Rotas

- `GET /`: pagina inicial
- `GET /api/health`: estado geral da aplicacao
- `GET /api/health/ollama`: versao, disponibilidade e instalacao do modelo

O Ollama nao deve ser publicado na rede. A indisponibilidade dele nao impede a API web.

## Testes

```bat
.venv\Scripts\python.exe -m pytest -v
```

## Configuracao

Use variaveis de ambiente ou copie `.env.example` para `.env`. Consulte tambem `configuration/settings.example.yaml`. Chaves principais:

- `HOST`
- `PORT`
- `OLLAMA_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT`
- `ENVIRONMENT`

## Banco de dados

A infraestrutura SQLite usa SQLAlchemy 2.x e Alembic. Por padrao, o arquivo fica em `data/mestre_rpg.db`.

Para verificar o banco sem criar tabelas:

```bat
.venv\Scripts\python.exe -m alembic current
```

Nesta versao nao existem tabelas de usuarios, campanhas ou permissoes.

## Semantica das sessoes

- `session_scope()` e destinado a leitura e nao realiza commit.
- `transaction_scope()` realiza commit apos sucesso e rollback apos excecao.
- Conexoes SQLite ativam integridade de chaves estrangeiras e timeout de espera.

## Autenticacao da Microetapa 2.3

- Senhas usam Argon2id por meio de `pwdlib[argon2]`.
- Sessoes persistem no SQLite e usam cookies HttpOnly.
- Operacoes autenticadas de logout exigem `X-CSRF-Token`.
- Rate limiting persistente nao esta implementado; nao exponha o login publicamente sem essa protecao.

## Convites da Microetapa 2.4

- Convites de uso unico sao gerados pela camada interna.
- A aceitação publica ocorre em `POST /api/invites/accept`.
- Tokens sao aleatorios de 256 bits e armazenados apenas como SHA-256.
- Não existe interface administrativa ou envio automatico nesta etapa.

## Gerenciamento interno de usuarios

A Microetapa 2.2 implementa modelo, schemas, repository e service para usuarios.
Nao existem rotas HTTP, login, senha ou autenticacao nesta etapa.
