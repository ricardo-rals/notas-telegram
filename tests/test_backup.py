"""006: backup diário do banco e atalho de inicialização."""

import subprocess
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


def test_backup_restauravel_com_as_notas(sessao, config_teste, tmp_path):
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    from conftest import recriar_banco
    for i in range(3):
        salvar_ao_vivo(sessao, nota(i))
    destino = backup.fazer_backup(config_teste.database_url, tmp_path / "bk", manter=7, agora=AGORA,
                                  pg_bin=config_teste.pg_bin)
    assert destino.name == "notas-20261108-153000.dump"
    u = make_url(config_teste.database_url)
    alvo = u.set(database=u.database.removesuffix("_test") + "_restaurado_test").render_as_string(hide_password=False)
    recriar_banco(alvo)
    args, env = backup.conexao_pg(alvo)
    r = subprocess.run([backup._pg("pg_restore", config_teste.pg_bin), *args, "-d", make_url(alvo).database,
                        str(destino)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    eng = create_engine(alvo)
    with eng.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM nota")) == 3
        assert c.scalar(text("SELECT count(*) FROM nota WHERE busca @@ to_tsquery('notas', 'nota')")) == 3
    eng.dispose()


def test_senha_nao_vai_na_linha_de_comando():
    args, env = backup.conexao_pg("postgresql+psycopg://postgres:segredo@127.0.0.1:5432/x")
    assert "segredo" not in " ".join(args) and env["PGPASSWORD"] == "segredo"


def test_pg_dump_ausente_vira_erro_visivel(config_teste, tmp_path):
    with pytest.raises(Exception):
        backup.fazer_backup(config_teste.database_url, tmp_path / "bk", 7, AGORA, pg_bin=tmp_path / "nada")
    assert backup.verificar(config_teste.database_url, tmp_path / "bk2", 7, AGORA, pg_bin=tmp_path / "nada") is None
    assert backup.ULTIMO_ERRO["mensagem"]
    backup.ULTIMO_ERRO["mensagem"] = None


def test_poda_mantem_os_mais_recentes_e_nao_toca_em_outros(config_teste, engine, tmp_path):
    pasta = tmp_path / "bk"
    pasta.mkdir()
    for d in range(8):
        (pasta / f"notas-202611{d + 1:02d}-000000.dump").write_bytes(b"x")
    (pasta / "leia-me.txt").write_text("meu")
    (pasta / "notas-copia-manual.dump").write_bytes(b"y")
    backup.fazer_backup(config_teste.database_url, pasta, manter=3, agora=AGORA, pg_bin=config_teste.pg_bin)
    nomes = sorted(p.name for p in pasta.iterdir())
    assert nomes == ["leia-me.txt", "notas-20261107-000000.dump", "notas-20261108-000000.dump",
                     "notas-20261108-153000.dump", "notas-copia-manual.dump"]


def test_precisa_backup(tmp_path):
    pasta = tmp_path / "bk"
    assert backup.precisa_backup(pasta, AGORA) and backup.ultimo_backup(pasta) is None
    pasta.mkdir()
    (pasta / "notas-20261108-123000.dump").write_bytes(b"x")  # 3 h atrás
    assert backup.ultimo_backup(pasta) == datetime(2026, 11, 8, 12, 30)
    assert not backup.precisa_backup(pasta, AGORA)
    assert backup.precisa_backup(pasta, AGORA + timedelta(hours=22))  # 25 h depois do backup
    (pasta / "notas-20301231-000000.dump").write_bytes(b"x")  # "do futuro" (relógio voltou)
    assert backup.precisa_backup(pasta, AGORA + timedelta(hours=22))


def test_rodar_uma_vez_registra_erro_sem_levantar(config_teste, engine, tmp_path):
    pasta = tmp_path / "bk"
    pg = config_teste.pg_bin
    assert backup.verificar(config_teste.database_url, pasta, 7, agora=AGORA, pg_bin=pg) is not None
    assert backup.ULTIMO_ERRO["mensagem"] is None
    assert backup.verificar(config_teste.database_url, pasta, 7, agora=AGORA, pg_bin=pg) is None  # em dia
    arquivo = tmp_path / "arquivo_no_lugar_da_pasta"
    arquivo.write_text("x")
    assert backup.verificar(config_teste.database_url, arquivo, 7, agora=AGORA, pg_bin=pg) is None
    assert backup.ULTIMO_ERRO["mensagem"]
    backup.ULTIMO_ERRO["mensagem"] = None


def test_main_imprime_o_caminho(config_teste, engine, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(backup, "carregar", lambda: config_teste)
    backup.main()
    saida = capsys.readouterr().out
    assert "Backup feito:" in saida and "notas-" in saida
    assert list(config_teste.backup_dir.glob("notas-*.dump"))


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
                      "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1/telegram", "BACKUP_MANTER": valor})


def test_backup_dir_padrao_e_fora_do_repo(tmp_path):
    from notas.config import RAIZ_REPO, ErroConfig, carregar
    env = {"ALLOWED_CHAT_ID": "-1001234567890", "ALLOWED_USER_ID": "1", "LOCALAPPDATA": str(tmp_path),
           "DATABASE_URL": "postgresql+psycopg://u:p@127.0.0.1/telegram"}
    c = carregar(env=env)
    assert c.backup_dir == tmp_path / "notas-telegram" / "backups" and c.backup_manter == 7
    with pytest.raises(ErroConfig, match="BACKUP_DIR"):
        carregar(env={**env, "BACKUP_DIR": str(RAIZ_REPO / "data" / "backups")})
