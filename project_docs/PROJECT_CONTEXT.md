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
- SQLite
- SQLAlchemy 2.x
- Alembic

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

## Auditoria e decisoes da Microetapa 2.1

- SQLite utiliza SQLAlchemy 2.x com um engine independente da camada HTTP.
- O banco usa `check_same_thread=False` em SQLite para compatibilidade assincrona.
- Conexoes SQLite ativam `PRAGMA foreign_keys=ON` e `PRAGMA busy_timeout=5000`.
- Bancos em disco usam WAL; bancos em memoria nao usam WAL.
- Existe um contexto somente leitura sem commit automatico e um contexto transacional explicito com commit ou rollback.
- A verificacao de banco da API usa uma rota sincronizada curta, sem bloquear o loop com tarefas extensas.
- O estado geral fica degradado quando o banco obrigatorio estiver indisponivel; Ollama permanece reportado separadamente.
- Alembic reutiliza a URL central do projeto ou uma URL temporaria fornecida pelo teste.

## Microetapa 2.2 - Usuarios

- E implementada uma entidade `User` com UUID, username, email, display_name, estado ativo e timestamps.
- Username e email sao normalizados em minusculas antes da persistencia.
- Validacoes usam Pydantic e restricoes SQLAlchemy/Alembic.
- Repositorio, servico e schemas possuem responsabilidades separadas.
- Desativacao e reativacao sao operacoes logicas explicitas.
- A funcionalidade nao contem login, senha, token, convite, permissao ou rota HTTP.
- A validacao de e-mail usa uma expressao regular basica para formato e normalizacao; nao garante conformidade RFC completa nem existencia da caixa.

## Microetapa 2.3 - Autenticacao

- Senhas sao protegidas com Argon2id por meio de `pwdlib`.
- Sessoes persistentes usam tokens aleatorios de 256 bits armazenados somente como SHA-256.
- O prazo absoluto de sessao e configuravel por `SESSION_DURATION_HOURS`.
- Cookies usam `mestre_session` com HttpOnly, SameSite=Lax e Secure em producao.
- CSRF usa token independente enviado em `X-CSRF-Token` e hash persistido na sessao.
- Operacoes sensiveis exigem Origin ou Referer confiavel configurado por `TRUSTED_ORIGINS`.
- Login inexistente usa verificacao Argon2 ficticia para reduzir diferenca temporal.
- Login publicamente exposto na rota HTTP existe somente para contas provisionadas internamente; nao existe cadastro publico nesta etapa.

## Microetapa 2.4 - Convites

- Convites sao individuais, de uso unico e armazenam somente o SHA-256 do token.
- Validade padrao configuravel de 48 horas.
- A criacao e revogacao administrativa permanecem internas; nao existe papel administrativo nesta etapa.
- A aceitação aceita cadastro publico apenas mediante convite valido.
- campaign_id prepara associacao futura sem criar tabela ou dependencia artificial de campanha.
- O aceite reutiliza UserService e AuthService dentro da mesma sessao transacional.
- O argumento booleano administrativo e apenas uma barreira interna, nao autorizacao real.
- Limitacao persistente de tentativas no aceite publico permanece pendente antes da exposicao externa.

## Microetapa 2.5.1 - Estrutura fundamental de campanhas

- `Campaign` armazena nome, descricao, Owner por chave estrangeira, estado, classificacao de duracao, duracao planejada da sessao, frequencia e datas de inicio/conclusao prevista.
- O estado inicial e `PREPARATION`; as transicoes do Owner sao inicio, pausa, retomada, encerramento e reabertura explicita de `ENDED` para `PREPARATION`.
- A reabertura e uma acao explicita do Owner e gera evento de auditoria. Campanhas encerradas sao preservadas e nao podem ser editadas ate serem reabertas.
- Criacao exige usuario existente e ativo. A identidade do Owner vem da sessao autenticada; endpoints mutaveis tambem verificam Origin/Referer e CSRF.
- A classificacao e `ONE_SHOT`, `SHORT`, `MEDIUM` ou `LONG`; a frequencia e `WEEKLY`, `BIWEEKLY`, `MONTHLY` ou `IRREGULAR`.
- A duracao planejada da sessao e persistida em minutos, limitada a 120-240, com padrao de 180 minutos. Duracao real nao e calculada porque ainda nao existem sessoes persistidas.
- Como nao havia infraestrutura de auditoria, foi criada a tabela de dominio `campaign_audit_events`; criacao, atualizacoes relevantes, transicoes e reabertura sao registradas na mesma transacao da alteracao.
- Tentativas de operacoes por nao-Owners sao registradas no logger `mestre_rpg` e rejeitadas pelo service.
- O limite tecnico total opcional e configuravel por `CAMPAIGN_MAX_TOTAL`; sem configuracao nao ha limite numerico. Nao foi criado painel, papel ou endpoint ADM nesta microetapa.
- `UserInvite.campaign_id` permanece opcional sem chave estrangeira, preservando convites antigos e adiando a associacao referencial para a microetapa de participantes.
- A API adiciona rotas autenticadas de criacao, consulta, edicao, transicao e consulta de auditoria. Nao adiciona participantes, sessoes, personagens, integracao narrativa ou exclusao de campanhas.
