#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Testes do Catálogo Editorial V1.
"""

from __future__ import annotations

import copy
import json
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


VALIDATOR = (
    SCRIPT_DIR
    / "validar-catalogo-editorial.py"
)

OFFICIAL_CATALOG = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
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

OFFICIAL_ARTICLES = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)


def load_catalog():
    return json.loads(
        OFFICIAL_CATALOG.read_text(
            encoding="utf-8"
        )
    )


def run_validator(
    catalog: Path,
    articles_dir: Path,
    index: Path,
    categories: Path,
):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--catalog",
            str(catalog),
            "--articles-dir",
            str(articles_dir),
            "--index",
            str(index),
            "--categories",
            str(categories),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={
            **__import__("os").environ,
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        check=False,
    )


def make_environment(
    root: Path,
):
    articles_dir = (
        root
        / "artigos"
    )

    articles_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for source in (
        OFFICIAL_ARTICLES
        .glob("*.html")
    ):
        shutil.copy2(
            source,
            articles_dir
            / source.name,
        )

    categories = (
        root
        / "categorias.json"
    )

    shutil.copy2(
        OFFICIAL_CATEGORIES,
        categories,
    )

    index = (
        root
        / "indice.json"
    )

    shutil.copy2(
        OFFICIAL_INDEX,
        index,
    )

    catalog = (
        root
        / "catalogo.json"
    )

    return (
        catalog,
        articles_dir,
        index,
        categories,
    )


def write_catalog(
    path: Path,
    data,
):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def expect_valid(
    label: str,
    *,
    catalog,
    articles_dir,
    index,
    categories,
):
    result = run_validator(
        catalog,
        articles_dir,
        index,
        categories,
    )

    if result.returncode != 0:
        raise AssertionError(
            f"{label}: deveria ser válido.\n"
            f"{result.stdout}"
        )

    if (
        "CATALOGO_EDITORIAL=0"
        not in result.stdout
    ):
        raise AssertionError(
            f"{label}: marcador de sucesso ausente."
        )

    print(
        f"[OK] {label}"
    )


def expect_invalid(
    label: str,
    *,
    catalog,
    articles_dir,
    index,
    categories,
):
    result = run_validator(
        catalog,
        articles_dir,
        index,
        categories,
    )

    if result.returncode == 0:
        raise AssertionError(
            f"{label}: deveria ser inválido."
        )

    if (
        "CATALOGO_EDITORIAL=1"
        not in result.stdout
    ):
        raise AssertionError(
            f"{label}: marcador de erro ausente.\n"
            f"{result.stdout}"
        )

    print(
        f"[OK] rejeitado: {label}"
    )


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do Catálogo Editorial V1.0"
    )

    print(
        "=============================================="
    )

    with tempfile.TemporaryDirectory(
        prefix="datadark-catalogo-editorial-"
    ) as temp_name:

        temp = Path(
            temp_name
        )

        (
            catalog,
            articles_dir,
            index,
            categories,
        ) = make_environment(
            temp
        )

        base = load_catalog()

        write_catalog(
            catalog,
            base,
        )

        expect_valid(
            (
                "catálogo oficial válido "
                "com slug público histórico"
            ),
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"] = []

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "HTML público sem catálogo",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        write_catalog(
            catalog,
            base,
        )

        index_data = json.loads(
            index.read_text(
                encoding="utf-8"
            )
        )

        orphan = copy.deepcopy(
            index_data[0]
        )

        orphan["slug"] = (
            "artigo-editorial-orfao"
        )

        orphan["title"] = (
            "Artigo editorial órfão"
        )

        orphan["url"] = (
            "artigos/"
            "artigo-editorial-orfao.html"
        )

        index_data.append(
            orphan
        )

        index.write_text(
            json.dumps(
                index_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        expect_invalid(
            "índice com artigo não catalogado",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        shutil.copy2(
            OFFICIAL_INDEX,
            index,
        )

        data = copy.deepcopy(
            base
        )

        data["version"] = 2

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "version diferente de 1",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["unexpected"] = True

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "campo raiz desconhecido",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        del data["articles"][0][
            "priority"
        ]

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "campo obrigatório ausente",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        catalog.write_text(
            """{
  "version": 1,
  "version": 1,
  "articles": []
}
""",
            encoding="utf-8",
        )

        expect_invalid(
            "chave JSON duplicada",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "id"
        ] = "KB-1"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "id inválido",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        second = copy.deepcopy(
            data["articles"][0]
        )

        second["id"] = (
            "DD-KB-000002"
        )

        data["articles"].append(
            second
        )

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "slug ou title duplicado",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "category_id"
        ] = "Wi-Fi"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "category_id não canônico",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "status"
        ] = "online"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "status desconhecido",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "priority"
        ] = "urgent"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "prioridade desconhecida",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "created_on"
        ] = "25/08/2026"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "data não ISO",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "published_on"
        ] = None

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "published sem published_on",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "status"
        ] = "ready"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "não-published com published_on",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "slug"
        ] = "Slug_incorreto"

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "slug sintaticamente inválido",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        write_catalog(
            catalog,
            base,
        )

        pilot = (
            articles_dir
            / (
                "wifi-conecta-mas-fica-"
                "sem-internet.html"
            )
        )

        pilot.unlink()

        expect_invalid(
            "published sem HTML",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        shutil.copy2(
            OFFICIAL_ARTICLES
            / pilot.name,
            pilot,
        )

        index.write_text(
            "[]\n",
            encoding="utf-8",
        )

        expect_invalid(
            "published ausente do índice",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        shutil.copy2(
            OFFICIAL_INDEX,
            index,
        )

        html = pilot.read_text(
            encoding="utf-8"
        )

        if (
            'content="wifi"'
            not in html
        ):
            raise AssertionError(
                "fixture: kb-category wifi "
                "não localizado."
            )

        pilot.write_text(
            html.replace(
                'content="wifi"',
                'content="rede"',
                1,
            ),
            encoding="utf-8",
        )

        expect_invalid(
            "category_id divergente no HTML",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        shutil.copy2(
            OFFICIAL_ARTICLES
            / pilot.name,
            pilot,
        )

        index_data = json.loads(
            index.read_text(
                encoding="utf-8"
            )
        )

        index_data[0]["title"] = (
            "Título divergente"
        )

        index.write_text(
            json.dumps(
                index_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        expect_invalid(
            "title divergente no índice",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

        shutil.copy2(
            OFFICIAL_INDEX,
            index,
        )

        data = copy.deepcopy(
            base
        )

        data["articles"][0][
            "status"
        ] = "planned"

        data["articles"][0][
            "published_on"
        ] = None

        write_catalog(
            catalog,
            data,
        )

        expect_invalid(
            "planned com HTML público",
            catalog=catalog,
            articles_dir=articles_dir,
            index=index,
            categories=categories,
        )

    print()

    print(
        "=============================================="
    )

    print(
        "RESULTADO: TODOS OS TESTES DO "
        "CATÁLOGO EDITORIAL PASSARAM"
    )

    print(
        "CATALOGO_EDITORIAL_TESTES=0"
    )

    print(
        "=============================================="
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
