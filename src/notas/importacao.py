"""Importa a exportação JSON do Telegram Desktop: `python -m notas.importacao <pasta>`."""

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy.orm import Session

from notas.config import Config, ErroConfig, carregar
from notas.db import Importacao, agora, criar_engine, exigir_revisao_atual
from notas.regras import (
    LIMITE_DOWNLOAD,
    chat_id_exportacao,
    classificar,
    deve_baixar,
    link_mensagem,
    normalizar_exportacao,
)
from notas.repositorio import (
    ImportacaoEmAndamento,
    concluir_importacao,
    iniciar_importacao,
    nota_existe,
    salvar_importada,
)

__all__ = ["ErroImportacao", "ImportacaoEmAndamento", "executar", "importar", "main"]


class ErroImportacao(Exception):
    pass


def ler_exportacao(pasta: Path, cfg: Config) -> tuple[int, list]:
    arquivo = pasta / "result.json"
    if not arquivo.is_file():
        raise ErroImportacao(f"{pasta} não tem result.json (exporte em formato JSON)")
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        chat_id = chat_id_exportacao(int(dados["id"]))
        mensagens = dados["messages"]
        if not isinstance(mensagens, list):
            raise TypeError("messages")
    except (ValueError, KeyError, TypeError) as e:
        raise ErroImportacao(f"result.json inválido ou incompleto ({type(e).__name__})") from None
    if chat_id != cfg.chat_id:
        raise ErroImportacao(f"a exportação é do chat {chat_id}, não do grupo configurado {cfg.chat_id}")
    return chat_id, mensagens


def _processar_item(item: dict, pasta: Path, chat_id: int, sessao: Session, cfg: Config) -> str:
    """Uma mensagem da exportação → contagem. Mesmas regras da captura ao vivo (FR-018)."""
    if item.get("from_id") != f"user{cfg.user_id}":
        return "ignoradas"
    try:
        mid = int(item["id"])
    except (KeyError, TypeError, ValueError):
        return "falhas"
    if nota_existe(sessao, chat_id, mid):
        return "existentes"

    base = {
        "chat_id": chat_id, "message_id": mid, "link": link_mensagem(chat_id, mid),
        "bruto": json.dumps(item, ensure_ascii=False),
    }
    copiado: Path | None = None
    try:
        m = normalizar_exportacao(item, chat_id)
        c = classificar(m)
        dados = base | {
            "enviada_em": m.enviada_em, "editada_em": m.editada_em, "tipo": c.tipo, "texto": c.texto,
            "arquivo_caminho": None, "arquivo_nome": m.midia_nome, "arquivo_tamanho": m.midia_tamanho,
            "situacao": "ok", "erro": None,
        }
        baixa = deve_baixar(m)
        if baixa is False:
            dados["situacao"] = "grande_demais"
        elif baixa:
            origem = (pasta / m.midia_ref).resolve() if m.midia_ref else None
            # O caminho vem do JSON: só vale arquivo dentro da própria pasta da exportação.
            if origem is None or not origem.is_relative_to(pasta.resolve()) or not origem.is_file():
                dados["situacao"] = "sem_arquivo"
            elif origem.stat().st_size > LIMITE_DOWNLOAD:
                dados["situacao"] = "grande_demais"
            else:
                cfg.media_dir.mkdir(parents=True, exist_ok=True)
                copiado = cfg.media_dir / f"{mid}_{origem.name}"
                shutil.copyfile(origem, copiado)
                dados.update(arquivo_caminho=copiado.name, arquivo_tamanho=origem.stat().st_size)
    except Exception as e:
        if copiado:
            copiado.unlink(missing_ok=True)
            copiado = None
        dados = base | {
            "enviada_em": agora(), "editada_em": None, "tipo": "outro", "texto": "",
            "arquivo_caminho": None, "arquivo_nome": None, "arquivo_tamanho": None,
            "situacao": "falha", "erro": f"{type(e).__name__}: {e}",
        }

    if not salvar_importada(sessao, dados):  # outra via criou no meio tempo
        if copiado:
            copiado.unlink(missing_ok=True)
        return "existentes"
    return "falhas" if dados["situacao"] == "falha" else "criadas"


def executar(imp_id: int, pasta: Path, sessao: Session, cfg: Config) -> Importacao:
    """Roda uma importação já registrada; cada mensagem é gravada na sua própria transação."""
    contagens: Counter = Counter()
    try:
        chat_id, mensagens = ler_exportacao(pasta, cfg)
        for item in mensagens:
            if isinstance(item, dict) and item.get("type") == "message":
                contagens[_processar_item(item, pasta, chat_id, sessao, cfg)] += 1
    except Exception as e:
        sessao.rollback()
        concluir_importacao(sessao, imp_id, "falha", contagens, erro=str(e) or type(e).__name__)
        raise
    return concluir_importacao(sessao, imp_id, "concluida", contagens)


def importar(pasta: Path, via: str, sessao: Session, cfg: Config) -> Importacao:
    pasta = Path(pasta)
    return executar(iniciar_importacao(sessao, str(pasta), via), pasta, sessao, cfg)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("uso: python -m notas.importacao <pasta da exportação>")
    try:
        cfg = carregar()
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    engine = criar_engine(cfg.database_path)
    exigir_revisao_atual(engine)
    with Session(engine) as sessao:
        try:
            r = importar(Path(sys.argv[1]), "terminal", sessao, cfg)
        except ErroImportacao as e:
            print(f"Importação recusada: {e}", file=sys.stderr)
            sys.exit(1)
        except ImportacaoEmAndamento as e:
            print(f"Importação recusada: {e}", file=sys.stderr)
            sys.exit(2)
        print(f"criadas: {r.criadas}  já existentes: {r.existentes}  ignoradas: {r.ignoradas}  falhas: {r.falhas}")


if __name__ == "__main__":
    main()
