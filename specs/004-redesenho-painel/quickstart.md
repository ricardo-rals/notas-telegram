# Quickstart: validar o redesenho (004)

## 1. Testes automáticos

```powershell
uv run pytest
```

Cobrem: barra lateral e contagens, aviso de falhas, cartões por tipo, `/novas`, estados vazios,
estrutura que o `painel.js` usa, e a varredura de exportações numa pasta falsa.

## 2. Painel numa cópia do banco

Subir o painel com `DATABASE_PATH` e `MEDIA_DIR` apontando para uma cópia, numa porta livre.

1. Barra lateral mostra só os tipos existentes, com contagens; clicar troca a lista sem recarregar
   e "voltar" restaura.
2. Janela de 360 px: categorias em faixa rolável; sem rolagem horizontal. Janela de 1920 px:
   ≥ 5 colunas.
3. Foto: clicar abre ampliada; `Esc` fecha e o foco volta à foto.
4. `/` foca a busca; `Esc` limpa.
5. Gravar uma nota nova na cópia (ou mandar no grupo, com o bot apontando para a cópia): o aviso
   aparece em até 10 s e os cartões não piscam; um áudio tocando continua.
6. Tema claro do Windows: texto legível; menos movimento ligado: sem animação.
7. `/importar`: as exportações de `Downloads\Telegram Desktop` aparecem; "Importar" funciona.
8. DevTools → Rede: nenhuma requisição para fora de 127.0.0.1.
