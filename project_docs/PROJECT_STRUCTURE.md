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

## Alteracoes da Etapa 1

- Criados todos os modulos Python, arquivos estaticos, testes e scripts BAT listados acima.
- Criados `.env.example`, `.gitignore`, `requirements.txt` e `README.md`.
- Criados os diretórios de dados e backups exigidos pela estrutura.
- Criado `.venv` com Python 3.12.10 para desenvolvimento local.

## Dependencias

FastAPI, Uvicorn, HTTPX, Pydantic Settings, Jinja2 e Pytest.
