"""006: backup diário do banco e atalho de inicialização."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from notas import backup, servico
from notas.repositorio import salvar_ao_vivo

AGORA = datetime(2026, 11, 8, 15, 30, 0)


def nota(mid):
    return {
        "chat_id": -1001234567890, "message_id": mid, "enviada_em": "2026-11-05T10:00:00+00:00",
        "editada_em": None, "tipo": "texto", "texto": f"nota {mid}", "link": "l",
        "arquivo_caminho": None, "arquivo_nome": None, "arquivo_tamanho": None,
        "situacao": "ok", "erro": None, "bruto": None,
    }


def test_backup_integro_com_as_notas(sessao, config_teste, tmp_path):
    for i in range(3):
        salvar_ao_vivo(sessao, nota(i))
    destino = backup.fazer_backup(config_teste.database_path, tmp_path / "bk", manter=7, agora=AGORA)
    assert destino.name == "notas-20261108-153000.db"
    c = sqlite3.connect(destino)
    assert c.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert c.execute("SELECT count(*) FROM nota").fetchone() == (3,)
    assert c.execute("SELECT count(*) FROM nota_fts WHERE nota_fts MATCH 'nota'").fetchone() == (3,)
    c.close()


def test_poda_mantem_os_mais_recentes_e_nao_toca_em_outros(config_teste, engine, tmp_path):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    for d in range(8):
        (pasta / f"notas-202611{d + 1:02d}-000000.db").write_bytes(b"x")
    (pasta / "leia-me.txt").write_text("meu")
    (pasta / "notas-copia-manual.db").write_bytes(b"y")
    backup.fazer_backup(config_teste.database_path, pasta, manter=3, agora=AGORA)
    nomes = sorted(p.name for p in pasta.iterdir())
    assert nomes == ["leia-me.txt", "notas-20261107-000000.db", "notas-20261108-000000.db",
                     "notas-20261108-153000.db", "notas-copia-manual.db"]


def test_precisa_backup(tmp_path):
    pasta = tmp_path / "bk"
    assert backup.precisa_backup(pasta, AGORA) and backup.ultimo_backup(pasta) is None
    pasta.mkdir()
    (pasta / "notas-20261108-123000.db").write_bytes(b"x")  # 3 h atrás
    assert backup.ultimo_backup(pasta) == datetime(2026, 11, 8, 12, 30)
    assert not backup.precisa_backup(pasta, AGORA)
    assert backup.precisa_backup(pasta, AGORA + timedelta(hours=22))  # 25 h depois do backup
    (pasta / "notas-20301231-000000.db").write_bytes(b"x")  # "do futuro" (relógio voltou)
    assert backup.precisa_backup(pasta, AGORA + timedelta(hours=22))


def test_rodar_uma_vez_registra_erro_sem_levantar(config_teste, engine, tmp_path):
    pasta = tmp_path / "bk"
    assert backup.verificar(config_teste.database_path, pasta, 7, agora=AGORA) is not None
    assert backup.ULTIMO_ERRO["mensagem"] is None
    assert backup.verificar(config_teste.database_path, pasta, 7, agora=AGORA) is None  # em dia
    arquivo = tmp_path / "arquivo_no_lugar_da_pasta"
    arquivo.write_text("x")
    assert backup.verificar(config_teste.database_path, arquivo, 7, agora=AGORA) is None
    assert backup.ULTIMO_ERRO["mensagem"]
    backup.ULTIMO_ERRO["mensagem"] = None


def test_main_imprime_o_caminho(config_teste, engine, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(backup, "carregar", lambda: config_teste)
    backup.main()
    saida = capsys.readouterr().out
    assert "Backup feito:" in saida and "notas-" in saida
    assert list(config_teste.backup_dir.glob("notas-*.db"))


# --- atalho de inicialização (US3) -----------------------------------------------------
def test_instalar_e_desinstalar(tmp_path):
    pasta = tmp_path / "Startup"
    pasta.mkdir()
    atalho = servico.instalar(pasta)
    conteudo = atalho.read_text(encoding="utf-8")
    assert atalho.name == "notas-telegram.cmd"
    assert str(servico.RAIZ_REPO / "iniciar.cmd") in conteudo
    assert servico.desinstalar(pasta) is True and not atalho.exists()
    assert servico.desinstalar(pasta) is False


def test_iniciar_cmd_sobe_os_dois_processos():
    cmd = (servico.RAIZ_REPO / "iniciar.cmd").read_text(encoding="utf-8")
    assert 'cd /d "%~dp0"' in cmd
    assert "start" in cmd and "/min" in cmd
    assert "python -m notas.bot" in cmd and "python -m notas.painel" in cmd


def test_pasta_de_inicializacao_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert servico.pasta_inicializar() == tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


@pytest.mark.parametrize("valor", ["0", "-1", "x"])
def test_backup_manter_invalido(valor, tmp_path):
    from notas.config import ErroConfig, carregar
    with pytest.raises(ErroConfig, match="BACKUP_MANTER"):
        carregar(env={"ALLOWED_CHAT_ID": "-1001234567890", "ALLOWED_USER_ID": "1",
                      "DATABASE_PATH": str(tmp_path / "n.db"), "BACKUP_MANTER": valor})


def test_backup_dir_padrao_e_fora_do_repo(tmp_path):
    from notas.config import RAIZ_REPO, ErroConfig, carregar
    env = {"ALLOWED_CHAT_ID": "-1001234567890", "ALLOWED_USER_ID": "1", "DATABASE_PATH": str(tmp_path / "n.db")}
    c = carregar(env=env)
    assert c.backup_dir == tmp_path / "backups" and c.backup_manter == 7
    with pytest.raises(ErroConfig, match="BACKUP_DIR"):
        carregar(env={**env, "BACKUP_DIR": str(RAIZ_REPO / "data" / "backups")})
