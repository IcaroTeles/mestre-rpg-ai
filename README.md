# Mestre RPG AI

Versao: `v0.1`

Fundacao web para uma aplicacao de RPG conduzida por IA, iniciada na Etapa 1.

## Requisitos

- Python 3.12
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
