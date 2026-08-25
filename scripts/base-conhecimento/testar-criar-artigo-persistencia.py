#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Teste da persistência transacional do
Gerador Oficial de Artigos V1.0.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True


SCRIPT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

ROOT = (
    SCRIPT_DIR
    .parents[1]
)


SOURCE_FILES = (
    "criar-artigo.py",
    "validar-artigos.py",
    "gerar-indice.py",
    "taxonomia.py",
)


BASE_ARTICLE = (
    "wifi-conecta-mas-fica-sem-internet.html"
)


PAYLOAD = {
    "title":
        "Teste Transacional de Rede Wi-Fi",

    "category_id":
        "wifi",

    "description":
        "Artigo temporário para testar "
        "persistência transacional.",

    "keywords": [
        "wifi",
        "transação",
        "teste",
    ],

    "aliases": [
        "teste transacional wifi",
        "wifi transacional",
    ],

    "overview":
        "Visão geral do teste transacional.",

    "diagnosis":
        "Diagnóstico criado exclusivamente "
        "para o ambiente temporário.",

    "procedure_steps": [
        "Confirme o estado inicial.",
        "Execute o procedimento temporário.",
        "Valide o resultado.",
    ],

    "validation":
        "Confirme que o artigo foi criado "
        "e indexado corretamente.",

    "notes":
        "Conteúdo exclusivo do teste.",
}


def run(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess:

    environment = os.environ.copy()

    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"


    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


    if (
        check
        and result.returncode != 0
    ):

        print(
            result.stdout
        )

        print(
            result.stderr,
            file=sys.stderr,
        )

        raise RuntimeError(
            "comando falhou: "
            + " ".join(command)
        )


    return result


def sha256(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def create_repository(
    parent: Path,
    name: str,
) -> Path:

    repository = (
        parent
        / name
    )

    scripts = (
        repository
        / "scripts"
        / "base-conhecimento"
    )

    template_dir = (
        scripts
        / "templates"
    )

    articles = (
        repository
        / "base-conhecimento"
        / "artigos"
    )

    data = (
        repository
        / "base-conhecimento"
        / "data"
    )


    template_dir.mkdir(
        parents=True
    )

    articles.mkdir(
        parents=True
    )

    data.mkdir(
        parents=True
    )


    for filename in SOURCE_FILES:

        shutil.copy2(
            SCRIPT_DIR
            / filename,
            scripts
            / filename,
        )


    shutil.copy2(
        SCRIPT_DIR
        / "templates"
        / "artigo-v1.html",
        template_dir
        / "artigo-v1.html",
    )


    shutil.copy2(
        ROOT
        / "base-conhecimento"
        / "artigos"
        / BASE_ARTICLE,
        articles
        / BASE_ARTICLE,
    )


    shutil.copy2(
        ROOT
        / "base-conhecimento"
        / "data"
        / "categorias.json",
        data
        / "categorias.json",
    )


    shutil.copy2(
        ROOT
        / "base-conhecimento"
        / "data"
        / "indice.json",
        data
        / "indice.json",
    )


    run(
        [
            "git",
            "init",
            "-q",
        ],
        cwd=repository,
    )


    run(
        [
            "git",
            "add",
            ".",
        ],
        cwd=repository,
    )


    run(
        [
            "git",
            "-c",
            "user.name=DATADARK Test",
            "-c",
            "user.email=test@datadark.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=repository,
    )


    return repository


def write_input(
    path: Path,
) -> None:

    path.write_text(
        json.dumps(
            PAYLOAD,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_success(
    parent: Path,
) -> None:

    repository = (
        create_repository(
            parent,
            "success-repo",
        )
    )

    input_path = (
        parent
        / "success-input.json"
    )

    write_input(
        input_path
    )


    creator = (
        repository
        / "scripts"
        / "base-conhecimento"
        / "criar-artigo.py"
    )


    base_article = (
        repository
        / "base-conhecimento"
        / "artigos"
        / BASE_ARTICLE
    )

    taxonomy = (
        repository
        / "base-conhecimento"
        / "data"
        / "categorias.json"
    )

    template = (
        repository
        / "scripts"
        / "base-conhecimento"
        / "templates"
        / "artigo-v1.html"
    )


    frozen_before = {
        "article":
            sha256(
                base_article
            ),

        "taxonomy":
            sha256(
                taxonomy
            ),

        "template":
            sha256(
                template
            ),
    }


    result = run(
        [
            sys.executable,
            str(
                creator
            ),
            "--input",
            str(
                input_path
            ),
            "--write",
        ],
        cwd=repository,
    )


    expected_output = (
        "MODO=WRITE",
        (
            "SLUG="
            "teste-transacional-de-rede-wi-fi"
        ),
        "CATEGORY_ID=wifi",
        "CATEGORY=Wi-Fi",
        "VALIDATOR=OK",
        "INDEX_GENERATOR=OK",
        "INDEX_CHECK=OK",
        "WRITE_TRANSACTION=OK",
        "REPOSITORY_MODIFIED=YES",
        "RESULTADO=ARTIGO_CRIADO",
    )


    for expected in expected_output:

        if expected not in result.stdout:

            raise RuntimeError(
                "saída ausente: "
                f"{expected}"
            )


    article = (
        repository
        / "base-conhecimento"
        / "artigos"
        / (
            "teste-transacional-"
            "de-rede-wi-fi.html"
        )
    )


    if not article.is_file():

        raise RuntimeError(
            "artigo não foi persistido"
        )


    index_path = (
        repository
        / "base-conhecimento"
        / "data"
        / "indice.json"
    )


    index = json.loads(
        index_path.read_text(
            encoding="utf-8"
        )
    )


    matches = [
        entry
        for entry in index
        if entry.get("slug")
        == (
            "teste-transacional-"
            "de-rede-wi-fi"
        )
    ]


    if len(matches) != 1:

        raise RuntimeError(
            "novo artigo não aparece "
            "exatamente uma vez no índice"
        )


    frozen_after = {
        "article":
            sha256(
                base_article
            ),

        "taxonomy":
            sha256(
                taxonomy
            ),

        "template":
            sha256(
                template
            ),
    }


    if frozen_before != frozen_after:

        raise RuntimeError(
            "artefato congelado foi modificado"
        )


    article_mode = (
        article.stat().st_mode
        & 0o777
    )


    if article_mode != 0o644:

        raise RuntimeError(
            "modo do artigo inválido: "
            f"{article_mode:o}"
        )


    status = run(
        [
            "git",
            "status",
            "--short",
        ],
        cwd=repository,
    ).stdout


    expected_status = {
        (
            " M base-conhecimento/"
            "data/indice.json"
        ),
        (
            "?? base-conhecimento/artigos/"
            "teste-transacional-de-rede-wi-fi.html"
        ),
    }


    actual_status = {
        line
        for line in status.splitlines()
        if line.strip()
    }


    if actual_status != expected_status:

        raise RuntimeError(
            "estado Git inesperado após write:\n"
            + status
        )


    print(
        "[OK] persistência transacional"
    )

    print(
        "[OK] artigo criado com modo 0644"
    )

    print(
        "[OK] índice atualizado"
    )

    print(
        "[OK] congelados intactos"
    )


def load_module(
    repository: Path,
):

    scripts = (
        repository
        / "scripts"
        / "base-conhecimento"
    )

    creator = (
        scripts
        / "criar-artigo.py"
    )


    sys.path.insert(
        0,
        str(
            scripts
        ),
    )


    try:

        spec = (
            importlib.util
            .spec_from_file_location(
                "_datadark_creator_rollback",
                creator,
            )
        )


        if (
            spec is None
            or spec.loader is None
        ):

            raise RuntimeError(
                "falha ao importar gerador"
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


        return module

    finally:

        sys.path.pop(
            0
        )


def test_rollback(
    parent: Path,
) -> None:

    repository = (
        create_repository(
            parent,
            "rollback-repo",
        )
    )

    input_path = (
        parent
        / "rollback-input.json"
    )

    write_input(
        input_path
    )


    module = load_module(
        repository
    )


    data = module.load_input(
        input_path
    )


    prepared = module.dry_run(
        data
    )


    target = prepared[
        "target"
    ]

    index_path = (
        repository
        / "base-conhecimento"
        / "data"
        / "indice.json"
    )


    index_before = (
        index_path.read_bytes()
    )


    real_run_command = (
        module.run_command
    )


    def failing_run_command(
        command,
        label,
    ):

        if (
            label
            == "validador pós-gravação"
        ):

            raise module.ArticleCreationError(
                "falha pós-gravação simulada"
            )


        return real_run_command(
            command,
            label,
        )


    module.run_command = (
        failing_run_command
    )


    failure_detected = False


    try:

        module.persist_candidate(
            prepared
        )

    except module.ArticleCreationError:

        failure_detected = True

    finally:

        module.run_command = (
            real_run_command
        )


    if not failure_detected:

        raise RuntimeError(
            "falha simulada não interrompeu "
            "a transação"
        )


    if target.exists():

        raise RuntimeError(
            "rollback não removeu artigo"
        )


    if (
        index_path.read_bytes()
        != index_before
    ):

        raise RuntimeError(
            "rollback não restaurou indice.json"
        )


    status = run(
        [
            "git",
            "status",
            "--short",
        ],
        cwd=repository,
    ).stdout


    if status.strip():

        raise RuntimeError(
            "rollback não restaurou "
            "working tree:\n"
            + status
        )


    print(
        "[OK] falha pós-gravação detectada"
    )

    print(
        "[OK] rollback removeu artigo"
    )

    print(
        "[OK] rollback restaurou indice.json"
    )

    print(
        "[OK] rollback restaurou working tree"
    )


def main() -> int:

    with tempfile.TemporaryDirectory(
        prefix="datadark-kb-persistence-"
    ) as temporary:

        parent = Path(
            temporary
        )


        test_success(
            parent
        )


        test_rollback(
            parent
        )


    print()

    print(
        "=============================================="
    )

    print(
        "RESULTADO: PERSISTENCIA TRANSACIONAL OK"
    )

    print(
        "GERADOR_PERSISTENCIA=0"
    )

    print(
        "=============================================="
    )


    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
