# PROJECT_CONTEXT

## Objetivo

O Mestre RPG AI sera uma aplicacao web de RPG conduzida por IA, iniciada sobre D&D 5e SRD 5.1 (2014). Esta etapa implementa apenas a fundacao web, configuracoes, estado do servidor e integracao de diagnostico com Ollama.

## Tecnologias aprovadas

- Python 3.12
- FastAPI e Uvicorn
- HTTPX
- Pydantic Settings
- HTML, CSS e JavaScript
- Pytest
- SQLite apenas em etapas futuras

## Separacao das IAs

- Qwen-Coder 32B: gera e mantem codigo.
- Gemma 3 12B: motor narrativo futuro da aplicacao.
- O Gemma nunca sera autoridade sobre dados mecanicos.

## Arquitetura

A aplicacao utiliza FastAPI com lifespan, configuracao centralizada, cliente Ollama modular e frontend servido localmente. SQLite sera integrado posteriormente sem alterar o ponto de entrada ou a separacao dos modulos.

## Decisoes da Etapa 1

- Ollama permanece ligado apenas a `127.0.0.1`.
- A API web inicia independentemente da IA.
- Configuracoes sao carregadas por variaveis de ambiente e `.env`.
- Logs sao escritos em `data/logs/app.log`.
- A estrutura YAML em `configuration/settings.example.yaml` serve como referencia; nesta etapa o carregamento efetivo usa Pydantic Settings e `.env`.
