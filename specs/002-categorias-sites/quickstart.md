# Quickstart: validar Categorias e Sites

Pré-requisito: ambiente da 001 funcionando (`uv sync`, `.env` preenchido). Dados só inventados.

## 1. Testes automáticos

```powershell
uv run pytest                    # tudo, inclusive normalização de sites e migração 0002
uv run pytest -m lento           # desempenho com 10.000 notas (SC-003, SC-004)
```

Cobertura esperada (ver [data-model.md](data-model.md) e [research.md](research.md) R2):

- `site()`: `www.`/`m.`/outros subdomínios, `.com.br`, `.co.uk`, `github.io`, porta,
  maiúsculas, IPv4/IPv6, `localhost`, `xn--`↔acento, `com.br` sozinho, URL malformada, sem esquema.
- URLs vindas de entidade `url`, `text_link` (Bot API) e `text_link`/`link` (exportação).
- Edição troca o site; edição link→texto apaga os sites; importação grava os sites.
- `reclassificar_sites` duas vezes = mesmo resultado; não altera nenhuma outra coluna da nota.

## 2. Notas antigas (US3)

```powershell
# copie um banco da 001 (de teste) e aponte DATABASE_PATH para a cópia
uv run --env-file .env alembic upgrade head
```

Esperado: o comando termina sem erro; no painel, aba Link → a soma dos botões de site cobre
todos os links (uma nota com dois sites conta nos dois). Rodar `alembic downgrade 0001` e
`upgrade head` de novo dá as mesmas contagens.

## 3. Painel (US1, US2)

```powershell
uv run --env-file .env python -m notas.painel
```

Em `http://127.0.0.1:8000`:

1. As abas mostram contagens; a soma das abas de tipo = "Todas" (SC-006).
2. Aba Link → botões de site; `www.youtube.com` e `m.youtube.com` aparecem só como `youtube.com`.
3. Clicar num site, buscar uma palavra, recarregar: aba, site e busca continuam.
4. Clicar de novo no site ativo → volta a "Todos os sites".
5. `/?tipo=link&site=nao-existe.com` → "Nenhuma nota encontrada", sem erro.
6. Navegar só com Tab/Enter pelas abas e botões.

## 4. Ao vivo (US4)

Com o bot rodando, mandar `https://m.facebook.com/evento` no grupo → em até 10 s aparece em
`facebook.com`. Editar para `https://youtu.be/x` → passa para `youtu.be`.
