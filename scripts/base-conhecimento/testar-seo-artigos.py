#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

Testes do SEO Individual V1.

Responsabilidades:
- validar o artigo SEO oficial;
- validar comportamento fail-closed;
- não modificar arquivos oficiais;
- usar somente diretórios temporários.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile

from pathlib import Path


SCRIPT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

REPOSITORY_ROOT = (
    SCRIPT_DIR
    .parents[1]
)

VALIDATOR = (
    SCRIPT_DIR
    / "validar-artigos.py"
)

CATEGORIES = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

SOURCE = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "artigos"
    / "wifi-conecta-mas-fica-sem-internet.html"
)

CANONICAL = (
    "https://datadark.com.br/"
    "base-conhecimento/artigos/"
    "wifi-conecta-mas-fica-sem-internet.html"
)


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:

    count = text.count(old)

    if count != 1:
        raise AssertionError(
            f"{label}: ocorrências={count}, "
            "esperado=1"
        )

    return text.replace(
        old,
        new,
        1,
    )


def replace_exact_count(
    text: str,
    old: str,
    new: str,
    expected: int,
    label: str,
) -> str:

    count = text.count(old)

    if count != expected:
        raise AssertionError(
            f"{label}: ocorrências={count}, "
            f"esperado={expected}"
        )

    return text.replace(
        old,
        new,
    )


def sub_once(
    text: str,
    pattern: str,
    replacement,
    label: str,
    flags: int = 0,
) -> str:

    result, count = re.subn(
        pattern,
        replacement,
        text,
        count=1,
        flags=flags,
    )

    if count != 1:
        raise AssertionError(
            f"{label}: substituições={count}, "
            "esperado=1"
        )

    return result


def run_case(
    name: str,
    text: str,
    expected_code: int,
    expected_text: str | None = None,
) -> None:

    with tempfile.TemporaryDirectory(
        prefix="datadark-seo-artigo-"
    ) as temporary:

        directory = Path(temporary)

        article = (
            directory
            / SOURCE.name
        )

        article.write_text(
            text,
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--directory",
                str(directory),
                "--categories",
                str(CATEGORIES),
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        if (
            result.returncode
            != expected_code
        ):
            print(
                result.stdout
            )

            raise AssertionError(
                f"{name}: exit="
                f"{result.returncode}, "
                f"esperado={expected_code}"
            )

        if (
            expected_text is not None
            and expected_text
            not in result.stdout
        ):
            print(
                result.stdout
            )

            raise AssertionError(
                f"{name}: mensagem esperada "
                "não localizada: "
                f"{expected_text!r}"
            )

        print(
            f"[OK] {name}"
        )


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do SEO Individual V1"
    )

    print(
        "=" * 46
    )


    if not SOURCE.is_file():
        raise AssertionError(
            "artigo piloto oficial não existe"
        )


    original = SOURCE.read_text(
        encoding="utf-8"
    )


    canonical_count = (
        original.count(
            CANONICAL
        )
    )

    if canonical_count != 4:
        raise AssertionError(
            "artigo piloto deve conter URL "
            "canônica exatamente quatro vezes; "
            f"obtido={canonical_count}"
        )


    run_case(
        "SEO oficial válido",
        original,
        0,
    )


    wrong_canonical = (
        replace_exact_count(
            original,
            CANONICAL,
            (
                "https://datadark.com.br/"
                "base-conhecimento/artigos/"
                "url-incorreta.html"
            ),
            4,
            "canonical oficial",
        )
    )

    run_case(
        "canonical divergente rejeitada",
        wrong_canonical,
        1,
        "canonical divergente",
    )


    executable_script = (
        replace_once(
            original,
            "</head>",
            (
                '  <script>\n'
                '    alert("nao permitido");\n'
                '  </script>\n'
                '\n'
                '</head>'
            ),
            "inserção JavaScript executável",
        )
    )

    run_case(
        "JavaScript executável rejeitado",
        executable_script,
        1,
        "JavaScript não é permitido",
    )


    wrong_schema = (
        replace_once(
            original,
            '"@type":"TechArticle"',
            '"@type":"Article"',
            "tipo do Schema",
        )
    )

    run_case(
        "tipo JSON-LD divergente rejeitado",
        wrong_schema,
        1,
        "JSON-LD divergente",
    )


    canonical_match = re.search(
        (
            r'<link\s+'
            r'rel="canonical"\s+'
            r'href="[^"]+">'
        ),
        original,
        flags=re.IGNORECASE,
    )

    if not canonical_match:
        raise AssertionError(
            "link canonical não localizado"
        )


    duplicate_canonical = (
        replace_once(
            original,
            canonical_match.group(0),
            (
                canonical_match.group(0)
                + "\n"
                + canonical_match.group(0)
            ),
            "duplicação canonical",
        )
    )

    run_case(
        "canonical duplicada rejeitada",
        duplicate_canonical,
        1,
        "exatamente um",
    )


    malformed_json = sub_once(
        original,
        (
            r'(<script\s+'
            r'type="application/ld\+json"\s*>)'
            r'.*?'
            r'(</script>)'
        ),
        lambda match: (
            match.group(1)
            + '{"@context":'
            + match.group(2)
        ),
        "JSON-LD inválido",
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    run_case(
        "JSON-LD inválido rejeitado",
        malformed_json,
        1,
        "JSON-LD inválido",
    )


    json_ld_match = re.search(
        (
            r'<script\s+'
            r'type="application/ld\+json"\s*>'
            r'.*?'
            r'</script>'
        ),
        original,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    if not json_ld_match:
        raise AssertionError(
            "bloco JSON-LD não localizado"
        )


    duplicate_json_ld = (
        replace_once(
            original,
            json_ld_match.group(0),
            (
                json_ld_match.group(0)
                + "\n"
                + json_ld_match.group(0)
            ),
            "duplicação JSON-LD",
        )
    )

    run_case(
        "JSON-LD duplicado rejeitado",
        duplicate_json_ld,
        1,
        "exatamente um JSON-LD",
    )


    extra_script_attribute = (
        replace_once(
            original,
            (
                '<script '
                'type="application/ld+json">'
            ),
            (
                '<script '
                'type="application/ld+json" '
                'data-test="1">'
            ),
            "atributo extra JSON-LD",
        )
    )

    run_case(
        "JSON-LD com atributo extra rejeitado",
        extra_script_attribute,
        1,
        "JavaScript não é permitido",
    )


    missing_og_title = sub_once(
        original,
        (
            r'\s*<meta\s+'
            r'property="og:title"\s+'
            r'content="[^"]*">\s*'
        ),
        "\n",
        "remoção og:title",
        flags=re.IGNORECASE,
    )

    run_case(
        "og:title ausente rejeitado",
        missing_og_title,
        1,
        "meta property og:title ausente ou vazia",
    )


    missing_twitter_title = sub_once(
        original,
        (
            r'\s*<meta\s+'
            r'name="twitter:title"\s+'
            r'content="[^"]*">\s*'
        ),
        "\n",
        "remoção twitter:title",
        flags=re.IGNORECASE,
    )

    run_case(
        "twitter:title ausente rejeitado",
        missing_twitter_title,
        1,
        "meta twitter:title ausente ou vazia",
    )


    print()
    print(
        "=" * 46
    )

    print(
        "RESULTADO: TESTES DO SEO INDIVIDUAL PASSARAM"
    )

    print(
        "SEO_INDIVIDUAL_TESTES=0"
    )

    print(
        "=" * 46
    )

    return 0


if __name__ == "__main__":

    try:
        raise SystemExit(
            main()
        )

    except AssertionError as exc:
        print(
            f"ERRO: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)
