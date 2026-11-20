# PROJECT_RULES

1. Manter narrativa e dados mecanicos separados.
2. O backend sera autoridade sobre dados oficiais.
3. O frontend nao determinara estados oficiais.
4. Nunca expor Ollama ou dados internos a internet.
5. Preservar responsabilidades modulares distintas.
6. Nao remover funcionalidades aprovadas sem autorizacao.
7. Nao alterar tecnologias aprovadas sem justificativa e autorizacao.
8. Nao antecipar funcionalidades de etapas futuras.
9. Preservar compatibilidade entre modulos.
10. Priorizar codigo modular, seguro e testavel.
11. A infraestrutura de banco sera independente da API e nao sera exposta diretamente.
12. Migracoes SQLite serao revisadas e nao devem ser destrutivas.
13. Nao criar entidades de usuarios, campanhas ou permissoes antes da microetapa correspondente.
14. Operacoes de banco nao devem criar ou alterar tabelas sem uma migracao Alembic autorizada.
15. Contextos de sessao devem fechar sempre e nao devem realizar commits implicitos.
16. Escritas devem usar um contexto transacional explicito com rollback em falha.
17. PRAGMAS SQLite devem ser aplicados por conexao e sem alterar dados existentes.
