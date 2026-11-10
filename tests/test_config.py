from pathlib import Path

import pytest

from notas.config import RAIZ_REPO, ErroConfig, carregar

URL = "postgresql+psycopg://postgres:segredo@127.0.0.1:5432/telegram"
BASE = {"ALLOWED_CHAT_ID": "-1001234567890", "ALLOWED_USER_ID": "111", "DATABASE_URL": URL}


def test_obrigatoria_ausente_cita_o_nome():
    with pytest.raises(ErroConfig, match="ALLOWED_USER_ID"):
        carregar(env={"ALLOWED_CHAT_ID": "-1001234567890", "DATABASE_URL": URL})


def test_token_exigido_so_quando_pedido(tmp_path):
    env = {**BASE}
    assert carregar(env=env).token is None
    with pytest.raises(ErroConfig, match="TELEGRAM_BOT_TOKEN"):
        carregar(exigir_token=True, env=env)
    assert carregar(exigir_token=True, env={**env, "TELEGRAM_BOT_TOKEN": "x"}).token == "x"


@pytest.mark.parametrize("url,trecho", [
    (None, "DATABASE_URL"),
    ("postgresql+psycopg://postgres:segredo@10.0.0.5:5432/telegram", "127.0.0.1"),
    ("sqlite:///x.db", "PostgreSQL"),
    ("postgresql+psycopg://postgres:segredo@127.0.0.1:5432/", "nome do banco"),
    ("nada disso", "inválida"),
])
def test_database_url_validada_sem_mostrar_senha(url, trecho):
    env = {k: v for k, v in BASE.items() if k != "DATABASE_URL"} | ({"DATABASE_URL": url} if url else {})
    with pytest.raises(ErroConfig, match=trecho) as e:
        carregar(env=env)
    assert "segredo" not in str(e.value)


def test_midia_dentro_do_repo_fora_de_data_e_recusada(tmp_path):
    env = {**BASE, "MEDIA_DIR": "src/midia"}
    with pytest.raises(ErroConfig, match="MEDIA_DIR"):
        carregar(env=env)


def test_padroes(tmp_path):
    cfg = carregar(env={**BASE, "LOCALAPPDATA": str(tmp_path)})
    assert cfg.database_url == URL and cfg.sqlite_antigo == tmp_path / "notas-telegram" / "notas.db"
    assert cfg.media_dir == RAIZ_REPO / "data" / "media"
    assert cfg.painel_port == 8000
    assert cfg.chat_id == -1001234567890 and cfg.user_id == 111


def test_id_nao_numerico(tmp_path):
    with pytest.raises(ErroConfig, match="ALLOWED_CHAT_ID"):
        carregar(env={**BASE, "ALLOWED_CHAT_ID": "abc"})


def test_vazio_conta_como_ausente(tmp_path):
    cfg = carregar(env={**BASE, "DATABASE_PATH": "", "MEDIA_DIR": "", "LOCALAPPDATA": str(tmp_path)})
    assert cfg.sqlite_antigo.parent == tmp_path / "notas-telegram"
    assert cfg.media_dir == RAIZ_REPO / "data" / "media"
    assert isinstance(cfg.sqlite_antigo, Path)


# --- 003: PREVIAS_LINKS ---------------------------------------------------------------
@pytest.mark.parametrize("valor, esperado", [(None, True), ("0", False), ("1", True)])
def test_previas_links(tmp_path, valor, esperado):
    env = {**BASE} | ({"PREVIAS_LINKS": valor} if valor else {})
    assert carregar(env=env).previas_links is esperado


def test_previas_links_invalido(tmp_path):
    with pytest.raises(ErroConfig, match="PREVIAS_LINKS"):
        carregar(env={**BASE, "PREVIAS_LINKS": "sim"})


# --- 009: sincronização -------------------------------------------------------------------
def test_config_da_sincronizacao(tmp_path):
    cfg = carregar(env={**BASE, "LOCALAPPDATA": str(tmp_path)})
    assert cfg.api_id is None and cfg.api_hash is None
    assert cfg.telegram_sessao == tmp_path / "notas-telegram" / "telegram"
    cfg = carregar(env={**BASE, "TELEGRAM_API_ID": "123", "TELEGRAM_API_HASH": "abc"})
    assert (cfg.api_id, cfg.api_hash) == (123, "abc")
    with pytest.raises(ErroConfig, match="TELEGRAM_API_ID"):
        carregar(env={**BASE, "TELEGRAM_API_ID": "abc"})
    with pytest.raises(ErroConfig, match="TELEGRAM_SESSAO"):
        carregar(env={**BASE, "TELEGRAM_SESSAO": str(RAIZ_REPO / "data" / "telegram")})
