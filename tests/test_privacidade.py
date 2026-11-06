"""Princípio IV: nada de token, banco ou mensagem real no repositório."""

import json
import re
import shutil
import subprocess

import pytest

from conftest import FIXTURES
from notas.config import RAIZ_REPO

TOKEN = re.compile(r"\d{6,}:[A-Za-z0-9_-]{35}")
CHATS_INVENTADOS = {-1001234567890, -1009999999999, 1234567890, 9999999999}


def arquivos_de_texto():
    pastas = [RAIZ_REPO / "src", RAIZ_REPO / "tests", RAIZ_REPO / "alembic"]
    soltos = [RAIZ_REPO / ".env.example", RAIZ_REPO / "pyproject.toml", RAIZ_REPO / "alembic.ini"]
    for p in [f for pasta in pastas for f in pasta.rglob("*") if f.is_file()] + soltos:
        if p.suffix in (".py", ".json", ".html", ".toml", ".ini", ".example", ".mako", ".md") or p.name == ".env.example":
            yield p


def test_nenhum_token_no_codigo_nem_nas_fixtures():
    achados = [str(p) for p in arquivos_de_texto() if TOKEN.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert achados == []


def test_env_example_sem_valores_secretos():
    for linha in (RAIZ_REPO / ".env.example").read_text(encoding="utf-8").splitlines():
        if linha.startswith(("TELEGRAM_BOT_TOKEN", "ALLOWED_CHAT_ID", "ALLOWED_USER_ID")):
            assert linha.endswith("="), linha


def test_fixtures_usam_so_chats_inventados():
    ids = set()
    for p in FIXTURES.rglob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue  # exportacao_quebrada é inválida de propósito
        if "chat" in d:
            ids.add(d["chat"]["id"])
        elif "id" in d and "messages" in d:
            ids.add(d["id"])
    assert ids and ids <= CHATS_INVENTADOS


def test_gitignore_cobre_dados_e_segredos():
    linhas = set((RAIZ_REPO / ".gitignore").read_text(encoding="utf-8").splitlines())
    assert {".env", "data/", "*.db", "*.db-wal", "*.db-shm"} <= linhas


@pytest.mark.skipif(
    shutil.which("git") is None or not (RAIZ_REPO / ".git").exists(), reason="ainda não é um repositório Git"
)
def test_nada_sensivel_versionado():
    versionados = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ_REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    proibidos = [f for f in versionados if f == ".env" or f.startswith("data/") or f.endswith((".db", ".db-wal", ".db-shm"))]
    assert proibidos == []
