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

## Resultados (2026-11-08)

Cópia do banco real (7 notas, 10 links), painel na porta 8766, Edge headless:

- §1: `uv run pytest` → 246 passed (inclui os `lento`).
- §2.1: barra lateral com Todas, Texto, Link, Foto, Documento e Localização, cada um com a
  contagem certa; tipos sem notas não aparecem.
- §2.2: a 1440 px, 4 colunas; nenhuma faixa vazia dos lados. O Edge headless não desce de 492 px
  de largura: nessa largura, `scrollWidth == innerWidth` (sem rolagem horizontal) e as categorias
  viram a faixa rolável. Os 360 px reais ficam para conferir no navegador.
- §2.5: nota gravada na cópia → `/novas` passou de vazio para "1 nota nova · mostrar".
- §2.7: `/importar` sem exportações em Downloads mostra a instrução e o campo manual.
  Corrigido na validação: a caixa de status aparecia vazia (`#status:has(p)`).
- §2.8: nenhum `<script>`, `<link>` ou `<img>` aponta para fora; fonte servida localmente.
- Pendentes de olho humano: foto ampliada com `Esc` e foco de volta, atalho `/`, tema claro.
