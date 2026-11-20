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

SQLAlchemy 2.x e Alembic foram adicionados na Microetapa 2.1.

FastAPI, Uvicorn, HTTPX, Pydantic Settings, Jinja2 e Pytest.
