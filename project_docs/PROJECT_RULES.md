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
18. O UUID de usuario sera gerado pelo backend e nunca recebido como identificador oficial do cliente.
19. Username e email serao normalizados antes da busca ou persistencia.
20. Exclusao fisica de usuarios nao sera implementada nesta microetapa.
21. Operacoes administrativas de usuario nao serao expostas por HTTP antes da autenticacao.
22. Username e email devem ter unicidade case-insensitive garantida tambem pelo banco.
23. Senhas nunca serao armazenadas ou registradas em texto puro.
24. Tokens de sessao serao armazenados somente como hash e entregues por cookie HttpOnly.
25. Operacoes de estado autenticadas exigirao CSRF e validacao de origem.
26. Login nao fara enumeração de contas ou exposicao de detalhes criptograficos.
27. Convites armazenarao somente hash do token e nunca serao reutilizaveis apos consumo.
28. Convites nao poderao atribuir privilegios administrativos.
29. Cadastro por convite e consumo serao transacionais.
30. Convites internos nao podem ser autorizados por qualquer usuario autenticado automaticamente.
31. UserService, AuthService e InviteService devem compartilhar a transacao do aceite sem commits intermediarios.
32. O aceite publico exigira rate limiting persistente antes da exposicao externa.
