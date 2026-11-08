from pathlib import Path

import pytest

from notas.config import RAIZ_REPO, ErroConfig, carregar

BASE = {"ALLOWED_CHAT_ID": "-1001234567890", "ALLOWED_USER_ID": "111"}


def test_obrigatoria_ausente_cita_o_nome():
    with pytest.raises(ErroConfig, match="ALLOWED_USER_ID"):
        carregar(env={"ALLOWED_CHAT_ID": "-1001234567890"})


def test_token_exigido_so_quando_pedido(tmp_path):
    env = {**BASE, "DATABASE_PATH": str(tmp_path / "n.db")}
    assert carregar(env=env).token is None
    with pytest.raises(ErroConfig, match="TELEGRAM_BOT_TOKEN"):
        carregar(exigir_token=True, env=env)
    assert carregar(exigir_token=True, env={**env, "TELEGRAM_BOT_TOKEN": "x"}).token == "x"


def test_banco_dentro_do_repo_e_recusado():
    with pytest.raises(ErroConfig, match="fora do repositório"):
        carregar(env={**BASE, "DATABASE_PATH": str(RAIZ_REPO / "notas.db")})


def test_midia_dentro_do_repo_fora_de_data_e_recusada(tmp_path):
    env = {**BASE, "DATABASE_PATH": str(tmp_path / "n.db"), "MEDIA_DIR": "src/midia"}
    with pytest.raises(ErroConfig, match="MEDIA_DIR"):
        carregar(env=env)


def test_padroes(tmp_path):
    cfg = carregar(env={**BASE, "LOCALAPPDATA": str(tmp_path)})
    assert cfg.database_path == tmp_path / "notas-telegram" / "notas.db"
    assert cfg.media_dir == RAIZ_REPO / "data" / "media"
    assert cfg.painel_port == 8000
    assert cfg.chat_id == -1001234567890 and cfg.user_id == 111


def test_id_nao_numerico(tmp_path):
    with pytest.raises(ErroConfig, match="ALLOWED_CHAT_ID"):
        carregar(env={**BASE, "ALLOWED_CHAT_ID": "abc", "DATABASE_PATH": str(tmp_path / "n.db")})


def test_vazio_conta_como_ausente(tmp_path):
    cfg = carregar(env={**BASE, "DATABASE_PATH": "", "MEDIA_DIR": "", "LOCALAPPDATA": str(tmp_path)})
    assert cfg.database_path.parent == tmp_path / "notas-telegram"
    assert cfg.media_dir == RAIZ_REPO / "data" / "media"
    assert isinstance(cfg.database_path, Path)


# --- 003: PREVIAS_LINKS ---------------------------------------------------------------
@pytest.mark.parametrize("valor, esperado", [(None, True), ("0", False), ("1", True)])
def test_previas_links(tmp_path, valor, esperado):
    env = {**BASE, "DATABASE_PATH": str(tmp_path / "n.db")} | ({"PREVIAS_LINKS": valor} if valor else {})
    assert carregar(env=env).previas_links is esperado


def test_previas_links_invalido(tmp_path):
    with pytest.raises(ErroConfig, match="PREVIAS_LINKS"):
        carregar(env={**BASE, "DATABASE_PATH": str(tmp_path / "n.db"), "PREVIAS_LINKS": "sim"})
