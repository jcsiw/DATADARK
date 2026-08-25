#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 7 — Testes da Taxonomia V1.0

Responsabilidades:
- validar o contrato estrutural da taxonomia;
- validar resolução estrita de category_id;
- validar comportamento fail-closed;
- validar integração da taxonomia com validar-artigos.py.

Todos os testes utilizam arquivos temporários.
Nenhum arquivo oficial da Base é modificado.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile

from pathlib import Path

from taxonomia import (
    TaxonomyError,
    load_taxonomy,
)


SCRIPT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

REPOSITORY_ROOT = (
    SCRIPT_DIR
    .parents[1]
)

OFFICIAL_TAXONOMY = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

VALIDATOR = (
    SCRIPT_DIR
    / "validar-artigos.py"
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


def expect_taxonomy_error(
    callback,
    description: str,
) -> None:

    try:

        callback()

    except TaxonomyError:

        print(
            f"[OK] {description}"
        )

        return

    raise AssertionError(
        f"{description}: "
        "TaxonomyError não foi gerado"
    )


def write_article(
    path: Path,
    category_meta: str,
) -> None:

    path.write_text(
        f"""<!DOCTYPE html>
<html lang="pt-BR">

<head>

<meta charset="utf-8">

<title>
Teste controlado de taxonomia
</title>

<meta
  name="description"
  content="Teste controlado da taxonomia DATADARK.">

<meta
  name="keywords"
  content="teste, taxonomia">

<meta
  name="kb-aliases"
  content="teste de categoria">

{category_meta}

</head>

<body>

<main>
Conteúdo técnico temporário.
</main>

</body>

</html>
""",
        encoding="utf-8",
    )


def run_validator(
    articles: Path,
    categories: Path = OFFICIAL_TAXONOMY,
):

    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--directory",
            str(articles),
            "--categories",
            str(categories),
        ],
        cwd=REPOSITORY_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def require_code(
    result,
    expected: int,
    description: str,
) -> None:

    if result.returncode != expected:

        print()
        print(
            "===== SAÍDA DO PROCESSO ====="
        )

        print(
            result.stdout
        )

        raise AssertionError(
            f"{description}: "
            f"esperado exit {expected}, "
            f"obtido {result.returncode}"
        )

    print(
        f"[OK] {description}"
    )


def require_output(
    result,
    expected: str,
    description: str,
) -> None:

    if expected not in result.stdout:

        print()
        print(
            "===== SAÍDA DO PROCESSO ====="
        )

        print(
            result.stdout
        )

        raise AssertionError(
            f"{description}: "
            f"texto não encontrado: "
            f"{expected!r}"
        )

    print(
        f"[OK] {description}"
    )


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes da Taxonomia V1.0"
    )

    print(
        "=" * 46
    )

    print()


    # ========================================================
    # TESTE 1 — TAXONOMIA OFICIAL
    # ========================================================

    taxonomy = load_taxonomy(
        OFFICIAL_TAXONOMY
    )

    assert_true(
        taxonomy.version == 1,
        "versão oficial da taxonomia é 1",
    )

    assert_true(
        len(taxonomy.categories) == 12,
        "taxonomia oficial possui 12 categorias",
    )

    assert_true(
        len(taxonomy.groups) == 6,
        "taxonomia oficial possui 6 grupos",
    )

    wifi = taxonomy.resolve_category(
        "wifi"
    )

    assert_true(
        wifi.label == "Wi-Fi",
        "categoria wifi resolve para Wi-Fi",
    )

    audio = taxonomy.resolve_category(
        "audio"
    )

    assert_true(
        audio.label == "Áudio",
        "categoria audio resolve para Áudio",
    )


    # ========================================================
    # TESTE 2 — RESOLUÇÃO ESTRITA
    # ========================================================

    invalid_values = (
        "Wi-Fi",
        "Áudio",
        "internet",
        "rede,wifi",
        " wifi ",
    )

    for value in invalid_values:

        expect_taxonomy_error(
            lambda value=value:
                taxonomy.resolve_category(
                    value
                ),
            (
                "category_id inválido rejeitado: "
                + repr(value)
            ),
        )


    # ========================================================
    # TESTE 3 — ARQUIVO INEXISTENTE
    # ========================================================

    with tempfile.TemporaryDirectory(
        prefix="datadark-taxonomia-missing-"
    ) as temp_name:

        missing = (
            Path(temp_name)
            / "nao-existe.json"
        )

        expect_taxonomy_error(
            lambda:
                load_taxonomy(
                    missing
                ),
            "taxonomia inexistente é rejeitada",
        )


    # ========================================================
    # TESTE 4 — JSON INVÁLIDO
    # ========================================================

    with tempfile.TemporaryDirectory(
        prefix="datadark-taxonomia-json-"
    ) as temp_name:

        invalid_json = (
            Path(temp_name)
            / "categorias.json"
        )

        invalid_json.write_text(
            "{ isto nao e json\n",
            encoding="utf-8",
        )

        expect_taxonomy_error(
            lambda:
                load_taxonomy(
                    invalid_json
                ),
            "JSON inválido é rejeitado",
        )


    # ========================================================
    # TESTE 5 — COLISÃO ENTRE CATEGORIAS
    # ========================================================

    with tempfile.TemporaryDirectory(
        prefix="datadark-taxonomia-collision-"
    ) as temp_name:

        collision_file = (
            Path(temp_name)
            / "categorias.json"
        )

        data = json.loads(
            OFFICIAL_TAXONOMY.read_text(
                encoding="utf-8"
            )
        )

        hardware = next(
            category
            for category
            in data["categories"]
            if category["id"] == "hardware"
        )

        hardware[
            "search_terms"
        ].append(
            "wifi"
        )

        collision_file.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        expect_taxonomy_error(
            lambda:
                load_taxonomy(
                    collision_file
                ),
            (
                "search_term duplicado entre "
                "categorias é rejeitado"
            ),
        )


    # ========================================================
    # TESTES DO VALIDADOR
    # ========================================================

    with tempfile.TemporaryDirectory(
        prefix="datadark-taxonomia-validator-"
    ) as temp_name:

        root = Path(
            temp_name
        )


        cases = (
            (
                "valido",
                """
<meta
  name="kb-category"
  content="wifi">
""",
                0,
                "[OK] teste.html",
            ),
            (
                "ausente",
                "",
                1,
                "meta kb-category ausente ou vazia",
            ),
            (
                "label",
                """
<meta
  name="kb-category"
  content="Wi-Fi">
""",
                1,
                "categoria desconhecida: Wi-Fi",
            ),
            (
                "espacos",
                """
<meta
  name="kb-category"
  content=" wifi ">
""",
                1,
                "categoria desconhecida:  wifi ",
            ),
            (
                "multipla",
                """
<meta
  name="kb-category"
  content="rede,wifi">
""",
                1,
                "categoria desconhecida: rede,wifi",
            ),
            (
                "duplicada",
                """
<meta
  name="kb-category"
  content="wifi">

<meta
  name="kb-category"
  content="rede">
""",
                1,
                "meta kb-category duplicada",
            ),
        )


        for (
            name,
            category_meta,
            expected_code,
            expected_text,
        ) in cases:

            articles = (
                root
                / name
            )

            articles.mkdir()

            write_article(
                articles
                / "teste.html",
                category_meta,
            )

            result = run_validator(
                articles
            )

            require_code(
                result,
                expected_code,
                (
                    "validador / "
                    f"{name}"
                ),
            )

            require_output(
                result,
                expected_text,
                (
                    "mensagem do validador / "
                    f"{name}"
                ),
            )


        # ====================================================
        # TAXONOMIA INEXISTENTE NO VALIDADOR
        # ====================================================

        articles = (
            root
            / "taxonomia-ausente"
        )

        articles.mkdir()

        result = run_validator(
            articles,
            root
            / "nao-existe.json",
        )

        require_code(
            result,
            2,
            (
                "validador retorna exit 2 "
                "para taxonomia inexistente"
            ),
        )

        require_output(
            result,
            "arquivo de taxonomia não encontrado",
            (
                "validador reporta taxonomia "
                "inexistente"
            ),
        )


        # ====================================================
        # JSON INVÁLIDO NO VALIDADOR
        # ====================================================

        invalid_taxonomy = (
            root
            / "taxonomia-invalida.json"
        )

        invalid_taxonomy.write_text(
            "{ json invalido\n",
            encoding="utf-8",
        )

        result = run_validator(
            articles,
            invalid_taxonomy,
        )

        require_code(
            result,
            2,
            (
                "validador retorna exit 2 "
                "para taxonomia inválida"
            ),
        )

        require_output(
            result,
            "JSON inválido",
            (
                "validador reporta JSON "
                "de taxonomia inválido"
            ),
        )


    print()

    print(
        "=" * 46
    )

    print(
        "RESULTADO: TODOS OS TESTES "
        "DA TAXONOMIA PASSARAM"
    )

    print(
        "Taxonomia DATADARK V1.0"
    )

    print(
        "=" * 46
    )

    return 0


if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except (
        AssertionError,
        OSError,
        TaxonomyError,
    ) as exc:

        print()

        print(
            "FALHA:"
        )

        print(
            str(exc)
        )

        sys.exit(1)
