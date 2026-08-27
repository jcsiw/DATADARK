#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Testes do Sincronizador Editorial V1.
ETAPA 8.7.2B.

Todos os cenários são executados em diretórios temporários.
Nenhum artefato editorial oficial deve ser modificado.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SCRIPT_PATH = Path(__file__).resolve()

SCRIPTS_DIR = SCRIPT_PATH.parent

ROOT = SCRIPT_PATH.parents[2]

SYNC = (
    SCRIPTS_DIR
    / "sincronizar-artigos.py"
)

OFFICIAL_ARTICLES = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)

OFFICIAL_CATEGORIES = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

OFFICIAL_INDEX = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

OFFICIAL_RELATED = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "relacionados.json"
)

OFFICIAL_CATALOG = (
    SCRIPTS_DIR
    / "editorial"
    / "catalogo.json"
)

OFFICIAL_TEMPLATE = (
    SCRIPTS_DIR
    / "templates"
    / "artigo-v1.html"
)


def assert_true(
    condition: bool,
    message: str,
) -> None:

    if not condition:

        raise AssertionError(
            message
        )

    print(
        f"[OK] {message}"
    )


def git_status() -> str:

    return subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def copy_fixture(
    root: Path,
) -> dict[str, Path]:

    articles = (
        root
        / "artigos"
    )

    shutil.copytree(
        OFFICIAL_ARTICLES,
        articles,
    )

    paths = {
        "articles":
            articles,
        "categories":
            root / "categorias.json",
        "index":
            root / "indice.json",
        "related":
            root / "relacionados.json",
        "catalog":
            root / "catalogo.json",
        "template":
            root / "artigo-v1.html",
    }

    shutil.copy2(
        OFFICIAL_CATEGORIES,
        paths["categories"],
    )

    shutil.copy2(
        OFFICIAL_INDEX,
        paths["index"],
    )

    shutil.copy2(
        OFFICIAL_RELATED,
        paths["related"],
    )

    shutil.copy2(
        OFFICIAL_CATALOG,
        paths["catalog"],
    )

    shutil.copy2(
        OFFICIAL_TEMPLATE,
        paths["template"],
    )

    return paths


def run_sync(
    fixture: dict[str, Path],
    publication_date: str | None = None,
    *,
    write: bool = False,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:

    command = [
        sys.executable,
        str(SYNC),
        "--articles-dir",
        str(fixture["articles"]),
        "--catalog",
        str(fixture["catalog"]),
        "--index",
        str(fixture["index"]),
        "--related",
        str(fixture["related"]),
        "--categories",
        str(fixture["categories"]),
        "--template",
        str(fixture["template"]),
    ]

    if publication_date is not None:

        command.extend(
            [
                "--publication-date",
                publication_date,
            ]
        )

    if write:

        command.append(
            "--write"
        )

    if check:

        command.append(
            "--check"
        )

    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def load_index(
    fixture: dict[str, Path],
) -> list[dict]:

    return json.loads(
        fixture["index"].read_text(
            encoding="utf-8"
        )
    )


def load_catalog(
    fixture: dict[str, Path],
) -> dict:

    return json.loads(
        fixture["catalog"].read_text(
            encoding="utf-8"
        )
    )


def next_id(
    fixture: dict[str, Path],
) -> str:

    catalog = load_catalog(
        fixture
    )

    numbers = [
        int(
            article["id"]
            .removeprefix(
                "DD-KB-"
            )
        )
        for article
        in catalog["articles"]
    ]

    number = (
        max(
            numbers,
            default=0,
        )
        + 1
    )

    return (
        f"DD-KB-{number:06d}"
    )


def clone_public_article(
    fixture: dict[str, Path],
    *,
    source_slug: str,
    target_slug: str,
    new_title: str,
) -> Path:

    index = load_index(
        fixture
    )

    source_entry = next(
        entry
        for entry in index
        if entry["slug"]
            == source_slug
    )

    old_title = (
        source_entry["title"]
    )

    source = (
        fixture["articles"]
        / f"{source_slug}.html"
    )

    target = (
        fixture["articles"]
        / f"{target_slug}.html"
    )

    text = source.read_text(
        encoding="utf-8"
    )

    if old_title not in text:

        raise RuntimeError(
            "título original não "
            "encontrado no HTML fixture."
        )

    text = text.replace(
        old_title,
        new_title,
    )

    text = text.replace(
        source_slug,
        target_slug,
    )

    target.write_text(
        text,
        encoding="utf-8",
    )

    return target


def remove_aliases(
    path: Path,
) -> None:

    text = path.read_text(
        encoding="utf-8"
    )

    pattern = re.compile(
        r'('
        r'<meta\b'
        r'(?=[^>]*\bname="kb-aliases")'
        r'[^>]*\bcontent="'
        r')'
        r'[^"]*'
        r'(")',
        re.IGNORECASE,
    )

    new_text, count = (
        pattern.subn(
            r'\1\2',
            text,
            count=1,
        )
    )

    if count != 1:

        raise RuntimeError(
            "meta kb-aliases não "
            "localizada de forma única."
        )

    path.write_text(
        new_text,
        encoding="utf-8",
    )


def set_meta_content(
    path: Path,
    name: str,
    value: str,
) -> None:

    text = path.read_text(
        encoding="utf-8"
    )

    pattern = re.compile(
        r'('
        r'<meta\b'
        r'(?=[^>]*\bname="'
        + re.escape(name)
        + r'")'
        r'[^>]*\bcontent="'
        r')'
        r'[^"]*'
        r'(")',
        re.IGNORECASE,
    )

    new_text, count = (
        pattern.subn(
            lambda match:
                (
                    match.group(1)
                    + value
                    + match.group(2)
                ),
            text,
            count=1,
        )
    )

    if count != 1:

        raise RuntimeError(
            f"meta {name} não localizada "
            "de forma única."
        )

    path.write_text(
        new_text,
        encoding="utf-8",
    )


def tree_digest(
    root: Path,
) -> str:

    digest = hashlib.sha256()

    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
        ),
        key=lambda path:
            (
                path
                .relative_to(root)
                .as_posix()
                .casefold()
            ),
    )

    for path in files:

        relative = (
            path
            .relative_to(root)
            .as_posix()
        )

        digest.update(
            relative.encode("utf-8")
        )

        digest.update(b"\0")

        digest.update(
            path.read_bytes()
        )

        digest.update(b"\0")

    return digest.hexdigest()


def tree_state(
    root: Path,
) -> dict[
    str,
    tuple[
        bytes,
        int,
    ],
]:

    state = {}

    for path in sorted(
        (
            item
            for item in root.rglob("*")
            if item.is_file()
        ),
        key=lambda item:
            (
                item
                .relative_to(root)
                .as_posix()
                .casefold()
            ),
    ):

        relative = (
            path
            .relative_to(root)
            .as_posix()
        )

        state[relative] = (
            path.read_bytes(),
            (
                path.stat().st_mode
                & 0o7777
            ),
        )

    return state


def test_baseline() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-baseline-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 0,
            "baseline sincronizado é aceito",
        )

        assert_true(
            "NOVOS=0"
            in result.stdout,
            "baseline não cria novos IDs",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=NO"
            in result.stdout,
            "baseline não exige sincronização",
        )

        assert_true(
            "REPOSITORY_MODIFIED=NO"
            in result.stdout,
            "dry-run não grava estado",
        )


def test_one_new_article() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-new-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        expected_id = next_id(
            fixture
        )

        slug = (
            "teste-controlado-"
            "sincronizador-editorial"
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=slug,
            new_title=(
                "Teste controlado do "
                "sincronizador editorial"
            ),
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 0,
            "artigo novo válido é aceito",
        )

        assert_true(
            "NOVOS=1"
            in result.stdout,
            "um artigo novo é detectado",
        )

        assert_true(
            f"NOVO={expected_id}|{slug}"
            in result.stdout,
            "próximo DD-KB é alocado",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=YES"
            in result.stdout,
            "novo artigo exige sincronização",
        )


def test_draft_ignored() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-draft-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        source = (
            fixture["articles"]
            / "windows-inicia-muito-lento.html"
        )

        shutil.copy2(
            source,
            fixture["articles"]
            / "_rascunho-sincronizador.html",
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 0,
            "rascunho prefixado por _ é aceito",
        )

        assert_true(
            "NOVOS=0"
            in result.stdout,
            "rascunho não recebe DD-KB",
        )

        assert_true(
            "RASCUNHOS_IGNORADOS=1"
            in result.stdout,
            "rascunho é contabilizado",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=NO"
            in result.stdout,
            "rascunho isolado não exige sync",
        )


def test_publication_date_required() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-date-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-data-obrigatoria",
            new_title=
                "Teste de data editorial obrigatória",
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 1,
            "novo artigo sem data é rejeitado",
        )

        assert_true(
            "--publication-date"
            in result.stderr,
            "erro informa data obrigatória",
        )


def test_aliases_required() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-alias-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        target = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-alias-obrigatorio",
            new_title=
                "Teste de alias editorial obrigatório",
        )

        remove_aliases(
            target
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 1,
            "novo artigo sem aliases é rejeitado",
        )

        assert_true(
            "kb-aliases"
            in result.stderr,
            "erro identifica kb-aliases",
        )


def test_existing_identity_is_protected() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-identity-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        path = (
            fixture["articles"]
            / "windows-inicia-muito-lento.html"
        )

        index = load_index(
            fixture
        )

        old_title = next(
            entry["title"]
            for entry in index
            if entry["slug"]
                == "windows-inicia-muito-lento"
        )

        text = path.read_text(
            encoding="utf-8"
        )

        text = text.replace(
            old_title,
            "Título adulterado para teste",
        )

        path.write_text(
            text,
            encoding="utf-8",
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 1,
            "mudança de identidade existente "
            "é rejeitada",
        )

        assert_true(
            "identidade title"
            in result.stderr,
            "erro identifica identidade title",
        )


def test_batch_is_deterministic() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-batch-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        first_id = next_id(
            fixture
        )

        first_number = int(
            first_id.removeprefix(
                "DD-KB-"
            )
        )

        second_id = (
            f"DD-KB-{first_number + 1:06d}"
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "aaa-teste-lote-editorial",
            new_title=
                "AAA teste de lote editorial",
        )

        clone_public_article(
            fixture,
            source_slug=
                "computador-esta-sem-som",
            target_slug=
                "zzz-teste-lote-editorial",
            new_title=
                "ZZZ teste de lote editorial",
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 0,
            "lote com dois artigos é aceito",
        )

        first_line = (
            f"NOVO={first_id}|"
            "aaa-teste-lote-editorial"
        )

        second_line = (
            f"NOVO={second_id}|"
            "zzz-teste-lote-editorial"
        )

        assert_true(
            first_line
            in result.stdout,
            "primeiro slug ordenado recebe "
            "primeiro ID",
        )

        assert_true(
            second_line
            in result.stdout,
            "segundo slug recebe ID seguinte",
        )

        assert_true(
            result.stdout.index(
                first_line
            )
            < result.stdout.index(
                second_line
            ),
            "relatório do lote é determinístico",
        )


def test_keywords_required() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-keywords-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        target = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-keywords-obrigatorias",
            new_title=
                "Teste de keywords obrigatórias",
        )

        set_meta_content(
            target,
            "keywords",
            "",
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 1,
            "novo artigo sem keywords "
            "é rejeitado",
        )

        assert_true(
            "meta keywords"
            in result.stderr,
            "erro identifica keywords",
        )


def test_invalid_publication_date() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-bad-date-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-data-invalida",
            new_title=
                "Teste de data editorial inválida",
        )

        result = run_sync(
            fixture,
            "2026-02-30",
        )

        assert_true(
            result.returncode == 1,
            "data editorial inválida "
            "é rejeitada",
        )

        assert_true(
            "--publication-date inválida"
            in result.stderr,
            "erro identifica data inválida",
        )


def test_duplicate_title_rejected() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-title-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        index = load_index(
            fixture
        )

        source_slug = (
            "windows-inicia-muito-lento"
        )

        source_title = next(
            entry["title"]
            for entry in index
            if entry["slug"]
                == source_slug
        )

        clone_public_article(
            fixture,
            source_slug=source_slug,
            target_slug=
                "teste-title-duplicado",
            new_title=source_title,
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 1,
            "title editorial duplicado "
            "é rejeitado",
        )

        assert_true(
            "title duplicado"
            in result.stderr,
            "erro identifica title duplicado",
        )


def test_invalid_category_rejected() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-category-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        target = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-categoria-invalida",
            new_title=
                "Teste de categoria inválida",
        )

        set_meta_content(
            target,
            "kb-category",
            "categoria-inexistente",
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 1,
            "categoria não canônica "
            "é rejeitada",
        )

        assert_true(
            "validação dos artigos de entrada"
            in result.stderr,
            "falha ocorre na validação "
            "estrutural de entrada",
        )


def test_case_collision_rejected() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-case-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        source = (
            fixture["articles"]
            / "windows-inicia-muito-lento.html"
        )

        target = (
            fixture["articles"]
            / "WINDOWS-INICIA-MUITO-LENTO.html"
        )

        shutil.copy2(
            source,
            target,
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        assert_true(
            result.returncode == 1,
            "colisão case-insensitive "
            "de filename é rejeitada",
        )

        assert_true(
            "colisão de nome"
            in result.stderr,
            "erro identifica colisão "
            "de filename",
        )


def test_broken_draft_is_ignored() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-broken-draft-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        draft = (
            fixture["articles"]
            / "_rascunho-invalido.html"
        )

        draft.write_text(
            "<html><body>"
            "<script>alert(1)</script>"
            "</body></html>",
            encoding="utf-8",
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 0,
            "HTML inválido prefixado por _ "
            "é realmente ignorado",
        )

        assert_true(
            "RASCUNHOS_IGNORADOS=1"
            in result.stdout,
            "rascunho inválido é contabilizado",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=NO"
            in result.stdout,
            "rascunho inválido não interfere "
            "no estado público",
        )


def test_nonpublished_public_rejected() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-status-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        catalog = load_catalog(
            fixture
        )

        target = next(
            article
            for article
            in catalog["articles"]
            if article["slug"]
                == "windows-inicia-muito-lento"
        )

        target["status"] = "draft"

        target["published_on"] = None

        fixture["catalog"].write_text(
            json.dumps(
                catalog,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_sync(
            fixture
        )

        assert_true(
            result.returncode == 1,
            "HTML público com estado "
            "não-published é rejeitado",
        )

        assert_true(
            "não está published"
            in result.stderr,
            "erro identifica conflito "
            "de estado editorial",
        )


def test_dry_run_fixture_is_immutable() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-immutable-"
    ) as temp:

        fixture_root = Path(temp)

        fixture = copy_fixture(
            fixture_root
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-imutabilidade-dry-run",
            new_title=
                "Teste de imutabilidade do dry-run",
        )

        before = tree_digest(
            fixture_root
        )

        result = run_sync(
            fixture,
            "2026-08-26",
        )

        after = tree_digest(
            fixture_root
        )

        assert_true(
            result.returncode == 0,
            "dry-run de artigo novo "
            "é concluído",
        )

        assert_true(
            before == after,
            "dry-run preserva byte a byte "
            "todo o laboratório de entrada",
        )



def test_write_success_and_idempotency() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-write-"
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        expected_id = next_id(
            fixture
        )

        slug = (
            "teste-write-"
            "transacional"
        )

        source = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                slug,
            new_title=
                "Teste de write transacional",
        )

        source_mode_before = (
            source.stat().st_mode
            & 0o7777
        )

        result = run_sync(
            fixture,
            "2026-08-26",
            write=True,
        )

        assert_true(
            result.returncode == 0,
            "write em fixture é concluído",
        )

        assert_true(
            "MODO=WRITE"
            in result.stdout,
            "relatório identifica modo WRITE",
        )

        assert_true(
            "WRITE_TRANSACTION=OK"
            in result.stdout,
            "transação de escrita é confirmada",
        )

        assert_true(
            "REPOSITORY_MODIFIED=YES"
            in result.stdout,
            "primeiro write modifica fixture",
        )

        assert_true(
            "RESULTADO=ESTADO_SINCRONIZADO"
            in result.stdout,
            "write termina sincronizado",
        )

        catalog = load_catalog(
            fixture
        )

        created = next(
            (
                article
                for article
                in catalog["articles"]
                if article["slug"] == slug
            ),
            None,
        )

        assert_true(
            created is not None,
            "novo artigo entra no catálogo",
        )

        assert_true(
            created["id"] == expected_id,
            "write persiste o DD-KB previsto",
        )

        assert_true(
            created["status"]
            == "published",
            "write persiste status published",
        )

        assert_true(
            created["published_on"]
            == "2026-08-26",
            "write persiste data editorial",
        )

        index = load_index(
            fixture
        )

        assert_true(
            any(
                entry["slug"] == slug
                for entry in index
            ),
            "novo artigo entra no índice",
        )

        related = json.loads(
            fixture["related"].read_text(
                encoding="utf-8"
            )
        )

        assert_true(
            slug
            in related["articles"],
            "novo artigo entra em relacionados",
        )

        assert_true(
            (
                source.stat().st_mode
                & 0o7777
            )
            == source_mode_before,
            "modo físico do HTML é preservado",
        )

        state_after_first = tree_state(
            fixture_root
        )

        second = run_sync(
            fixture,
            write=True,
        )

        state_after_second = tree_state(
            fixture_root
        )

        assert_true(
            second.returncode == 0,
            "segunda execução WRITE é aceita",
        )

        assert_true(
            "WRITE_TRANSACTION=NOOP"
            in second.stdout,
            "segunda execução vira NOOP",
        )

        assert_true(
            "FILES_PROMOTED=0"
            in second.stdout,
            "NOOP não promove arquivos",
        )

        assert_true(
            "REPOSITORY_MODIFIED=NO"
            in second.stdout,
            "NOOP não modifica fixture",
        )

        assert_true(
            "RESULTADO=ESTADO_JA_SINCRONIZADO"
            in second.stdout,
            "segunda execução reconhece "
            "estado sincronizado",
        )

        assert_true(
            state_after_second
            == state_after_first,
            "segunda execução é idempotente "
            "byte a byte e em modos",
        )


def test_write_rollback_after_promotion() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-rollback-"
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        slug = (
            "teste-rollback-"
            "transacional"
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                slug,
            new_title=
                "Teste de rollback transacional",
        )

        state_before = tree_state(
            fixture_root
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                "datadark_sync_under_test",
                SYNC,
            )
        )

        assert_true(
            spec is not None
            and spec.loader is not None,
            "módulo do sincronizador "
            "é carregável para teste",
        )

        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(
            module
        )

        args = module.parse_args()

        args.articles_dir = (
            fixture["articles"]
        )

        args.catalog = (
            fixture["catalog"]
        )

        args.index = (
            fixture["index"]
        )

        args.related = (
            fixture["related"]
        )

        args.categories = (
            fixture["categories"]
        )

        args.template = (
            fixture["template"]
        )

        args.publication_date = (
            "2026-08-26"
        )

        args.write = True

        candidate = (
            module.run_dry_run(
                args
            )
        )

        assert_true(
            candidate[
                "synchronization_needed"
            ],
            "fixture de rollback exige "
            "promoção real",
        )

        original_validator = (
            module.validate_written_state
        )

        def forced_failure(_args):

            raise module.SynchronizationError(
                "falha pós-promoção "
                "induzida pela suíte"
            )

        module.validate_written_state = (
            forced_failure
        )

        failure_seen = False

        try:

            module.persist_candidate(
                args=args,
                result=candidate,
            )

        except module.SynchronizationError as exc:

            failure_seen = (
                "falha pós-promoção "
                "induzida pela suíte"
                in str(exc)
            )

        finally:

            module.validate_written_state = (
                original_validator
            )

        assert_true(
            failure_seen,
            "falha pós-promoção "
            "foi efetivamente induzida",
        )

        state_after = tree_state(
            fixture_root
        )

        assert_true(
            state_after == state_before,
            "rollback restaura todos os "
            "bytes e modos da fixture",
        )

        remaining = list(
            fixture_root.rglob(
                ".*.sync.*.tmp"
            )
        )

        assert_true(
            not remaining,
            "rollback não deixa staged files",
        )


def test_write_partial_promotion_rollback() -> None:

    with tempfile.TemporaryDirectory(
        prefix=(
            "datadark-sync-test-"
            "partial-promotion-"
        )
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        slug = (
            "teste-falha-"
            "promocao-parcial"
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=slug,
            new_title=(
                "Teste de falha "
                "durante promoção parcial"
            ),
        )

        state_before = tree_state(
            fixture_root
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                "datadark_sync_partial",
                SYNC,
            )
        )

        assert_true(
            spec is not None
            and spec.loader is not None,
            "módulo é carregável para "
            "falha de promoção parcial",
        )

        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(
            module
        )

        args = module.argparse.Namespace(
            articles_dir=
                fixture["articles"],
            catalog=
                fixture["catalog"],
            index=
                fixture["index"],
            related=
                fixture["related"],
            categories=
                fixture["categories"],
            template=
                fixture["template"],
            publication_date=
                "2026-08-26",
            write=True,
        )

        candidate = (
            module.run_dry_run(
                args
            )
        )

        targets = (
            module.build_write_targets(
                args=args,
                result=candidate,
            )
        )

        assert_true(
            len(targets) >= 2,
            "fixture possui pelo menos "
            "dois alvos transacionais",
        )

        original_replace = (
            module.os.replace
        )

        sync_promotions = 0

        def failing_replace(
            source,
            destination,
        ):

            nonlocal sync_promotions

            source_path = Path(
                source
            )

            if ".sync." in source_path.name:

                sync_promotions += 1

                if sync_promotions == 2:

                    raise OSError(
                        "falha intermediária "
                        "induzida pela suíte"
                    )

            return original_replace(
                source,
                destination,
            )

        module.os.replace = (
            failing_replace
        )

        failure_seen = False

        try:

            module.persist_candidate(
                args=args,
                result=candidate,
            )

        except OSError as exc:

            failure_seen = (
                "falha intermediária "
                "induzida pela suíte"
                in str(exc)
            )

        finally:

            module.os.replace = (
                original_replace
            )

        assert_true(
            failure_seen,
            "falha na segunda promoção "
            "foi efetivamente induzida",
        )

        assert_true(
            sync_promotions >= 2,
            "a transação alcançou "
            "promoção intermediária",
        )

        state_after = tree_state(
            fixture_root
        )

        assert_true(
            state_after == state_before,
            "rollback parcial restaura "
            "todos os bytes e modos",
        )

        residues = list(
            fixture_root.rglob(
                ".*.sync.*.tmp"
            )
        )

        residues += list(
            fixture_root.rglob(
                ".*.restore.*.tmp"
            )
        )

        assert_true(
            not residues,
            "falha intermediária não "
            "deixa staged files",
        )


def test_write_concurrent_fingerprint_rejected() -> None:

    with tempfile.TemporaryDirectory(
        prefix=(
            "datadark-sync-test-"
            "fingerprint-race-"
        )
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-race-fingerprint",
            new_title=
                "Teste de concorrência "
                "do fingerprint",
        )

        state_before = tree_state(
            fixture_root
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                "datadark_sync_race",
                SYNC,
            )
        )

        assert_true(
            spec is not None
            and spec.loader is not None,
            "módulo é carregável para "
            "teste de fingerprint",
        )

        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )

        spec.loader.exec_module(
            module
        )

        args = module.argparse.Namespace(
            articles_dir=
                fixture["articles"],
            catalog=
                fixture["catalog"],
            index=
                fixture["index"],
            related=
                fixture["related"],
            categories=
                fixture["categories"],
            template=
                fixture["template"],
            publication_date=
                "2026-08-26",
            write=True,
        )

        candidate = (
            module.run_dry_run(
                args
            )
        )

        original_fingerprint = (
            module.official_state_fingerprint
        )

        calls = 0

        def racing_fingerprint(
            **kwargs,
        ):

            nonlocal calls

            calls += 1

            value = (
                original_fingerprint(
                    **kwargs
                )
            )

            if calls >= 2:

                return (
                    "0" * 64
                )

            return value

        module.official_state_fingerprint = (
            racing_fingerprint
        )

        failure_seen = False

        try:

            module.persist_candidate(
                args=args,
                result=candidate,
            )

        except module.SynchronizationError as exc:

            failure_seen = (
                "estado oficial mudou durante "
                "a preparação da transação"
                in str(exc)
            )

        finally:

            module.official_state_fingerprint = (
                original_fingerprint
            )

        assert_true(
            failure_seen,
            "mudança concorrente de "
            "fingerprint é rejeitada",
        )

        assert_true(
            calls >= 2,
            "segundo fingerprint "
            "foi efetivamente executado",
        )

        state_after = tree_state(
            fixture_root
        )

        assert_true(
            state_after == state_before,
            "rejeição concorrente não "
            "altera bytes nem modos",
        )

        residues = list(
            fixture_root.rglob(
                ".*.sync.*.tmp"
            )
        )

        assert_true(
            not residues,
            "rejeição concorrente remove "
            "todos os staged files",
        )


def test_write_preserves_all_existing_modes() -> None:

    with tempfile.TemporaryDirectory(
        prefix=(
            "datadark-sync-test-"
            "modes-"
        )
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        new_article = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-preservacao-modos",
            new_title=
                "Teste de preservação "
                "de modos físicos",
        )

        fixture["catalog"].chmod(
            0o640
        )

        fixture["index"].chmod(
            0o600
        )

        fixture["related"].chmod(
            0o644
        )

        new_article.chmod(
            0o660
        )

        tracked_paths = [
            fixture["catalog"],
            fixture["index"],
            fixture["related"],
        ]

        tracked_paths.extend(
            sorted(
                fixture[
                    "articles"
                ].glob("*.html"),
                key=lambda item:
                    item.name.casefold(),
            )
        )

        modes_before = {
            str(path):
                (
                    path.stat().st_mode
                    & 0o7777
                )
            for path in tracked_paths
        }

        result = run_sync(
            fixture,
            "2026-08-26",
            write=True,
        )

        assert_true(
            result.returncode == 0,
            "write com modos heterogêneos "
            "é concluído",
        )

        modes_after = {
            str(path):
                (
                    path.stat().st_mode
                    & 0o7777
                )
            for path in tracked_paths
        }

        assert_true(
            modes_after == modes_before,
            "todos os modos físicos "
            "existentes são preservados",
        )


def test_check_baseline() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-check-baseline-"
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        before = tree_state(
            fixture_root
        )

        result = run_sync(
            fixture,
            check=True,
        )

        after = tree_state(
            fixture_root
        )

        assert_true(
            result.returncode == 0,
            "CHECK sincronizado retorna 0",
        )

        assert_true(
            "MODO=CHECK"
            in result.stdout,
            "relatório identifica modo CHECK",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=NO"
            in result.stdout,
            "CHECK reconhece baseline sincronizado",
        )

        assert_true(
            "RESULTADO=ESTADO_SINCRONIZADO"
            in result.stdout,
            "CHECK informa estado sincronizado",
        )

        assert_true(
            before == after,
            "CHECK não modifica bytes nem modos",
        )


def test_check_new_article_without_date() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-check-new-"
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        expected_id = next_id(
            fixture
        )

        slug = (
            "teste-check-"
            "novo-artigo"
        )

        clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=slug,
            new_title=
                "Teste CHECK de novo artigo",
        )

        before = tree_state(
            fixture_root
        )

        result = run_sync(
            fixture,
            check=True,
        )

        after = tree_state(
            fixture_root
        )

        assert_true(
            result.returncode == 1,
            "CHECK divergente retorna 1",
        )

        assert_true(
            "NOVOS=1"
            in result.stdout,
            "CHECK detecta artigo novo",
        )

        assert_true(
            (
                f"NOVO={expected_id}|{slug}"
                in result.stdout
            ),
            "CHECK calcula o próximo DD-KB",
        )

        assert_true(
            "SINCRONIZACAO_NECESSARIA=YES"
            in result.stdout,
            "CHECK informa sincronização necessária",
        )

        assert_true(
            "RESULTADO=ESTADO_DIVERGENTE"
            in result.stdout,
            "CHECK informa estado divergente",
        )

        assert_true(
            before == after,
            "CHECK com artigo novo "
            "não modifica a fixture",
        )


def test_check_derived_divergence() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-check-derived-"
    ) as temp:

        fixture_root = Path(
            temp
        )

        fixture = copy_fixture(
            fixture_root
        )

        index = load_index(
            fixture
        )

        index[0]["description"] = (
            "Descrição adulterada "
            "exclusivamente para teste CHECK."
        )

        fixture["index"].write_text(
            json.dumps(
                index,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        before = tree_state(
            fixture_root
        )

        result = run_sync(
            fixture,
            check=True,
        )

        after = tree_state(
            fixture_root
        )

        assert_true(
            result.returncode == 1,
            "CHECK detecta artefato "
            "derivado divergente",
        )

        assert_true(
            "INDICE_DIVERGENTE=YES"
            in result.stdout,
            "CHECK identifica indice.json "
            "divergente",
        )

        assert_true(
            before == after,
            "CHECK de artefato divergente "
            "permanece somente leitura",
        )


def test_check_structural_error_returns_2() -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-sync-test-check-error-"
    ) as temp:

        fixture = copy_fixture(
            Path(temp)
        )

        target = clone_public_article(
            fixture,
            source_slug=
                "windows-inicia-muito-lento",
            target_slug=
                "teste-check-categoria-invalida",
            new_title=
                "Teste CHECK de categoria inválida",
        )

        set_meta_content(
            target,
            "kb-category",
            "categoria-inexistente",
        )

        result = run_sync(
            fixture,
            check=True,
        )

        assert_true(
            result.returncode == 2,
            "CHECK usa status 2 "
            "para erro estrutural",
        )

        assert_true(
            "ERRO:"
            in result.stderr,
            "CHECK reporta erro estrutural",
        )


def test_check_and_write_are_exclusive() -> None:

    result = subprocess.run(
        [
            sys.executable,
            str(SYNC),
            "--check",
            "--write",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert_true(
        result.returncode == 2,
        "--check e --write "
        "são mutuamente exclusivos",
    )

    assert_true(
        (
            "not allowed with argument"
            in result.stderr
            or "not allowed"
            in result.stderr
        ),
        "argparse informa conflito "
        "entre CHECK e WRITE",
    )


def main() -> int:

    status_before = git_status()

    assert_true(
        SYNC.is_file(),
        "sincronizador existe",
    )

    assert_true(
        bool(
            SYNC.stat().st_mode
            & 0o111
        ),
        "sincronizador é executável",
    )

    test_baseline()

    test_one_new_article()

    test_draft_ignored()

    test_publication_date_required()

    test_aliases_required()

    test_existing_identity_is_protected()

    test_batch_is_deterministic()

    test_keywords_required()

    test_invalid_publication_date()

    test_duplicate_title_rejected()

    test_invalid_category_rejected()

    test_case_collision_rejected()

    test_broken_draft_is_ignored()

    test_nonpublished_public_rejected()

    test_dry_run_fixture_is_immutable()

    test_write_success_and_idempotency()

    test_write_rollback_after_promotion()

    test_write_partial_promotion_rollback()

    test_write_concurrent_fingerprint_rejected()

    test_write_preserves_all_existing_modes()

    test_check_baseline()

    test_check_new_article_without_date()

    test_check_derived_divergence()

    test_check_structural_error_returns_2()

    test_check_and_write_are_exclusive()

    status_after = git_status()

    assert_true(
        status_after
        == status_before,
        "testes não modificaram o "
        "estado Git oficial",
    )

    print()
    print(
        "=============================================="
    )
    print(
        "RESULTADO: TODOS OS TESTES DO "
        "SINCRONIZADOR PASSARAM"
    )
    print(
        "SINCRONIZADOR_TESTES=0"
    )
    print(
        "=============================================="
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
