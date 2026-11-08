"""Bot em long polling: `uv run --env-file .env python -m notas.bot`."""

import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy.orm import Session

from notas.config import Config, ErroConfig, carregar
from notas.db import agora, criar_engine, exigir_revisao_atual
from notas.regras import classificar, deve_baixar, iso_utc, link_mensagem, normalizar_bot_api, itens_de_link
from notas.repositorio import registrar_falha, salvar_ao_vivo

log = logging.getLogger("notas.bot")
Baixar = Callable[[str, Path], Awaitable[None]]


def _erro(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"


async def processar_mensagem(msg: dict, sessao: Session, cfg: Config, baixar: Baixar) -> None:
    """Uma mensagem → uma nota. Qualquer falha vira nota `falha` com o original (Princípio VIII)."""
    # Dono checado no dicionário cru, antes de qualquer parsing: mensagem de terceiro nunca vira
    # nota, nem nota de falha (FR-001, SC-003).
    if (msg.get("chat") or {}).get("id") != cfg.chat_id or (msg.get("from") or {}).get("id") != cfg.user_id:
        return
    bruto = json.dumps(msg, ensure_ascii=False)
    try:
        m = normalizar_bot_api(msg)
        c = classificar(m)
        dados = {
            "chat_id": m.chat_id, "message_id": m.message_id, "enviada_em": m.enviada_em,
            "editada_em": m.editada_em, "tipo": c.tipo, "texto": c.texto,
            "link": link_mensagem(m.chat_id, m.message_id), "arquivo_caminho": None,
            "arquivo_nome": m.midia_nome, "arquivo_tamanho": m.midia_tamanho,
            "situacao": "ok", "erro": None, "bruto": bruto,
        }
        baixa = deve_baixar(m)
        if baixa is False:
            dados["situacao"] = "grande_demais"
        elif baixa:
            nome = f"{m.message_id}_{m.midia_uid}{m.midia_ext}"
            try:
                await baixar(m.midia_ref, cfg.media_dir / nome)
                dados["arquivo_caminho"] = nome
            except Exception as e:
                dados.update(situacao="falha", erro=f"download: {_erro(e)}")
        salvar_ao_vivo(sessao, dados, itens_de_link(m) if c.tipo == "link" else [])
    except Exception as e:
        sessao.rollback()
        registrar_falha(
            sessao,
            chat_id=int(msg["chat"]["id"]),
            message_id=int(msg["message_id"]),
            erro=_erro(e),
            bruto=bruto,
            enviada_em=_tentar(lambda: iso_utc(msg["date"]), agora()),
            editada_em=_tentar(lambda: iso_utc(msg["edit_date"]), None),
            link=_tentar(lambda: link_mensagem(msg["chat"]["id"], msg["message_id"]), ""),
        )


def _tentar(f, padrao):
    try:
        return f()
    except Exception:
        return padrao


def main() -> None:
    from telegram import Update
    from telegram.ext import Application, ContextTypes, MessageHandler, filters

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # o httpx loga a URL, que contém o token
    try:
        cfg = carregar(exigir_token=True)
    except ErroConfig as e:
        raise SystemExit(f"Configuração inválida: {e}") from None
    if not str(cfg.chat_id).startswith("-100"):
        raise SystemExit("ALLOWED_CHAT_ID precisa ser de um supergrupo (começa com -100).")
    engine = criar_engine(cfg.database_path)
    exigir_revisao_atual(engine)
    cfg.media_dir.mkdir(parents=True, exist_ok=True)

    app = Application.builder().token(cfg.token).build()

    async def baixar(file_id: str, destino: Path) -> None:
        arquivo = await app.bot.get_file(file_id)
        await arquivo.download_to_drive(destino)

    async def tratar(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        try:
            with Session(engine) as sessao:
                await processar_mensagem(msg.to_dict(), sessao, cfg, baixar)
        except Exception as e:
            # Nem a falha pôde ser gravada (ex.: banco inacessível). A mensagem segue no Telegram.
            log.error(
                "mensagem chat=%s id=%s não gravada (%s). Recupere pela importação: "
                "uv run --env-file .env python -m notas.importacao <pasta da exportação>",
                msg.chat_id, msg.message_id, type(e).__name__,
            )

    async def erro_global(_: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        log.error("erro no bot: %s", type(context.error).__name__)

    do_dono = filters.Chat(cfg.chat_id) & filters.User(cfg.user_id)
    app.add_handler(MessageHandler(do_dono & filters.UpdateType.MESSAGE, tratar))
    app.add_handler(MessageHandler(do_dono & filters.UpdateType.EDITED_MESSAGE, tratar))
    app.add_error_handler(erro_global)
    log.info("bot iniciado; ouvindo o grupo %s", cfg.chat_id)
    app.run_polling(allowed_updates=["message", "edited_message"])


if __name__ == "__main__":
    main()
