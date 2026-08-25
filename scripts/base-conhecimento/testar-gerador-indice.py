#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 5 — Testes do Gerador de Índice V1.0

Todos os testes utilizam diretórios temporários.
Nenhum arquivo oficial da Base é modificado.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path


GENERATOR = (
    Path(__file__)
    .resolve()
    .with_name(
        "gerar-indice.py"
    )
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


def sha256(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                65536
            )

            if not chunk:

                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def run_generator(
    articles: Path,
    output: Path,
    *extra_args: str,
    cwd: Path | None = None,
):

    command = [
        sys.executable,
        str(GENERATOR),
        "--articles-dir",
        str(articles),
        "--output",
        str(output),
        *extra_args,
    ]


    return subprocess.run(
        command,
        cwd=(
            str(cwd)
            if cwd is not None
            else None
        ),
        text=True,
        capture_output=True,
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
            "===== STDOUT ====="
        )
        print(
            result.stdout
        )

        print(
            "===== STDERR ====="
        )
        print(
            result.stderr
        )

        raise AssertionError(
            f"{description}: "
            f"esperado exit {expected}, "
            f"obtido {result.returncode}"
        )


def write_article(
    path: Path,
    head: str,
) -> None:

    path.write_text(
        f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
{head}
</head>
<body>
<main>Conteúdo técnico de teste.</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def clean_articles(
    directory: Path,
) -> None:

    for child in (
        directory.iterdir()
    ):

        if child.is_dir():

            shutil.rmtree(
                child
            )

        else:

            child.unlink()


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do Gerador de Índice V1.0"
    )

    print(
        "=" * 46
    )

    print()


    if not GENERATOR.is_file():

        print(
            "FALHA: gerar-indice.py "
            "não foi encontrado."
        )

        return 1


    try:

        with tempfile.TemporaryDirectory(
            prefix="datadark-kb-index-"
        ) as temp_name:

            root = Path(
                temp_name
            )

            articles = (
                root
                / "artigos"
            )

            output = (
                root
                / "indice.json"
            )

            articles.mkdir(
                parents=True
            )


            # ==========================================
            # TESTE 1 — BASE VAZIA
            # ==========================================

            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "base vazia",
            )

            assert_true(
                output.read_text(
                    encoding="utf-8"
                )
                == "[]\n",
                "base vazia gera exatamente []",
            )


            # ==========================================
            # TESTE 2 — ARTIGO MÍNIMO
            # ==========================================

            minimum = (
                articles
                / "computador-nao-liga.html"
            )

            write_article(
                minimum,
                """
<title>Computador não liga</title>

<meta
  name="kb-category"
  content="hardware">
""",
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "artigo mínimo",
            )


            data = json.loads(
                output.read_text(
                    encoding="utf-8"
                )
            )


            assert_true(
                len(data) == 1,
                "artigo mínimo foi indexado",
            )


            expected_minimum = {
                "slug":
                    "computador-nao-liga",

                "title":
                    "Computador não liga",

                "description":
                    "",

                "url":
                    "artigos/computador-nao-liga.html",

                "category_id":
                    "hardware",

                "category":
                    "Hardware",

                "keywords":
                    [],

                "aliases":
                    [],
            }


            assert_true(
                data[0]
                == expected_minimum,
                "fallbacks opcionais do artigo mínimo estão corretos",
            )


            # ==========================================
            # TESTE 3 — ARTIGO ENRIQUECIDO
            # ==========================================

            enriched = (
                articles
                / "audio-sem-som.html"
            )


            write_article(
                enriched,
                """
<title>Áudio sem som</title>

<meta
  name="description"
  content="Diagnóstico para equipamento sem saída de áudio.">

<meta
  name="keywords"
  content="Windows, áudio, WINDOWS, audio, driver">

<meta
  name="kb-aliases"
  content="PC sem som, pc sem som, som não funciona">

<meta
  name="kb-category"
  content="audio">
""",
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "artigo enriquecido",
            )


            data = json.loads(
                output.read_text(
                    encoding="utf-8"
                )
            )


            assert_true(
                [
                    item["slug"]
                    for item in data
                ]
                == [
                    "audio-sem-som",
                    "computador-nao-liga",
                ],
                "índice é ordenado deterministicamente por slug",
            )


            audio = data[0]


            assert_true(
                audio["description"]
                ==
                "Diagnóstico para equipamento sem saída de áudio.",
                "description foi extraída",
            )


            assert_true(
                audio["category_id"]
                == "audio",
                "category_id foi extraído",
            )


            assert_true(
                audio["category"]
                == "Áudio",
                "label da categoria foi resolvida",
            )


            assert_true(
                audio["keywords"]
                == [
                    "Windows",
                    "áudio",
                    "driver",
                ],
                "keywords foram deduplicadas preservando primeira ocorrência",
            )


            assert_true(
                audio["aliases"]
                == [
                    "PC sem som",
                    "som não funciona",
                ],
                "aliases foram deduplicados preservando primeira ocorrência",
            )


            # ==========================================
            # TESTE 4 — RASCUNHO IGNORADO
            # ==========================================

            draft = (
                articles
                / "_teste-layout.html"
            )

            draft.write_text(
                "<html>arquivo propositalmente inválido</html>",
                encoding="utf-8",
            )


            before_draft = sha256(
                output
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "rascunho ignorado",
            )


            assert_true(
                "Rascunhos ignorados: 1"
                in result.stdout,
                "_*.html é contabilizado como rascunho ignorado",
            )


            assert_true(
                sha256(output)
                == before_draft,
                "rascunho não altera conteúdo do índice",
            )


            # ==========================================
            # TESTE 5 — --check ATUALIZADO
            # ==========================================

            result = run_generator(
                articles,
                output,
                "--check",
                cwd=root,
            )

            require_code(
                result,
                0,
                "--check atualizado",
            )


            assert_true(
                "ÍNDICE ATUALIZADO"
                in result.stdout,
                "--check reconhece índice atualizado",
            )


            # ==========================================
            # TESTE 6 — DETERMINISMO
            # ==========================================

            hash_one = sha256(
                output
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "segunda geração determinística",
            )


            hash_two = sha256(
                output
            )


            assert_true(
                hash_one == hash_two,
                "duas gerações idênticas produzem o mesmo SHA-256",
            )


            # ==========================================
            # TESTE 7 — --check DESATUALIZADO
            # ==========================================

            original_minimum = (
                minimum.read_text(
                    encoding="utf-8"
                )
            )


            minimum.write_text(
                original_minimum.replace(
                    "Computador não liga</title>",
                    "Computador não liga mais</title>",
                ),
                encoding="utf-8",
            )


            hash_before_check = sha256(
                output
            )


            result = run_generator(
                articles,
                output,
                "--check",
                cwd=root,
            )

            require_code(
                result,
                1,
                "--check desatualizado",
            )


            assert_true(
                "ÍNDICE DESATUALIZADO"
                in result.stdout,
                "--check detecta alteração não regenerada",
            )


            assert_true(
                sha256(output)
                == hash_before_check,
                "--check nunca modifica o índice",
            )


            minimum.write_text(
                original_minimum,
                encoding="utf-8",
            )


            result = run_generator(
                articles,
                output,
                "--check",
                cwd=root,
            )

            require_code(
                result,
                0,
                "--check após restauração",
            )


            # ==========================================
            # TESTE 8 — ATOMICIDADE / NOME INVÁLIDO
            # ==========================================

            invalid_name = (
                articles
                / "Áudio Novo.html"
            )


            write_article(
                invalid_name,
                """
<title>Áudio Novo</title>
""",
            )


            stable_hash = sha256(
                output
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                1,
                "nome inválido",
            )


            assert_true(
                sha256(output)
                == stable_hash,
                "falha por nome inválido preserva índice existente",
            )


            invalid_name.unlink()


            # ==========================================
            # TESTE 9 — TITLE AUSENTE
            # ==========================================

            no_title = (
                articles
                / "sem-titulo.html"
            )


            write_article(
                no_title,
                """
<meta
  name="description"
  content="Artigo sem título.">
""",
            )


            stable_hash = sha256(
                output
            )


            result = run_generator(
                articles,
                output,
                cwd=root,
            )

            require_code(
                result,
                1,
                "title ausente",
            )


            assert_true(
                sha256(output)
                == stable_hash,
                "falha por title ausente preserva índice existente",
            )


            no_title.unlink()


            # ==========================================
            # TESTE 10 — CAMINHOS CUSTOMIZADOS /
            # INDEPENDÊNCIA DO CWD
            # ==========================================

            alternate_root = (
                root
                / "outro-local"
            )

            alternate_articles = (
                alternate_root
                / "html"
            )

            alternate_output = (
                alternate_root
                / "dados"
                / "catalogo.json"
            )

            alternate_articles.mkdir(
                parents=True
            )


            write_article(
                alternate_articles
                / "laudo-tecnico.html",
                """
<title>Laudo Técnico</title>

<meta
  name="kb-category"
  content="documentos">
""",
            )


            result = run_generator(
                alternate_articles,
                alternate_output,
                cwd=root,
            )

            require_code(
                result,
                0,
                "caminhos customizados",
            )


            alternate_data = json.loads(
                alternate_output.read_text(
                    encoding="utf-8"
                )
            )


            assert_true(
                alternate_data[0]["url"]
                ==
                "artigos/laudo-tecnico.html",
                "URL pública permanece padronizada com diretório customizado",
            )


            assert_true(
                alternate_output.is_file(),
                "arquivo customizado foi criado fora do repositório",
            )


            # ==========================================
            # TESTE 11 — CATEGORIA CANÔNICA /
            # category_id + LABEL
            # ==========================================

            category_root = (
                root
                / "contrato-categorias"
            )

            category_root.mkdir()


            valid_articles = (
                category_root
                / "valida"
                / "artigos"
            )

            valid_output = (
                category_root
                / "valida"
                / "indice.json"
            )

            valid_articles.mkdir(
                parents=True
            )


            write_article(
                valid_articles
                / "wifi-sem-internet.html",
                """
<title>Wi-Fi sem internet</title>

<meta
  name="kb-category"
  content="wifi">
""",
            )


            result = run_generator(
                valid_articles,
                valid_output,
                cwd=root,
            )


            require_code(
                result,
                0,
                (
                    "categoria canônica "
                    "é aceita"
                ),
            )


            valid_data = json.loads(
                valid_output.read_text(
                    encoding="utf-8"
                )
            )


            assert_true(
                len(valid_data) == 1,
                (
                    "artigo com categoria "
                    "canônica foi indexado"
                ),
            )


            assert_true(
                valid_data[0][
                    "category_id"
                ]
                == "wifi",
                (
                    "category_id canônico "
                    "foi preservado"
                ),
            )


            assert_true(
                valid_data[0][
                    "category"
                ]
                == "Wi-Fi",
                (
                    "label da categoria "
                    "foi resolvida pela taxonomia"
                ),
            )


            # ==========================================
            # TESTE 12 — CATEGORIAS INVÁLIDAS /
            # FAIL-CLOSED / ATOMICIDADE
            # ==========================================

            invalid_category_cases = (
                (
                    "ausente",
                    "",
                    (
                        "meta kb-category "
                        "ausente ou vazia"
                    ),
                ),
                (
                    "vazia",
                    """
<meta
  name="kb-category"
  content="">
""",
                    (
                        "meta kb-category "
                        "ausente ou vazia"
                    ),
                ),
                (
                    "label",
                    """
<meta
  name="kb-category"
  content="Wi-Fi">
""",
                    (
                        "categoria desconhecida: "
                        "Wi-Fi"
                    ),
                ),
                (
                    "espacos",
                    """
<meta
  name="kb-category"
  content=" wifi ">
""",
                    (
                        "categoria desconhecida: "
                        " wifi "
                    ),
                ),
                (
                    "desconhecida",
                    """
<meta
  name="kb-category"
  content="internet">
""",
                    (
                        "categoria desconhecida: "
                        "internet"
                    ),
                ),
                (
                    "multipla",
                    """
<meta
  name="kb-category"
  content="rede,wifi">
""",
                    (
                        "categoria desconhecida: "
                        "rede,wifi"
                    ),
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
                    (
                        "meta kb-category "
                        "duplicada"
                    ),
                ),
            )


            for (
                case_name,
                category_meta,
                expected_message,
            ) in invalid_category_cases:

                case_root = (
                    category_root
                    / case_name
                )

                case_articles = (
                    case_root
                    / "artigos"
                )

                case_output = (
                    case_root
                    / "indice.json"
                )

                case_articles.mkdir(
                    parents=True
                )


                write_article(
                    case_articles
                    / "teste-categoria.html",
                    (
                        "\n"
                        "<title>"
                        "Teste controlado "
                        "de categoria"
                        "</title>\n"
                        + category_meta
                    ),
                )


                case_output.write_text(
                    "INDICE-PRESERVADO\n",
                    encoding="utf-8",
                )

                hash_before = sha256(
                    case_output
                )


                result = run_generator(
                    case_articles,
                    case_output,
                    cwd=root,
                )


                require_code(
                    result,
                    1,
                    (
                        "categoria inválida / "
                        f"{case_name}"
                    ),
                )


                assert_true(
                    expected_message
                    in result.stdout,
                    (
                        "erro esperado foi "
                        "reportado / "
                        f"{case_name}"
                    ),
                )


                assert_true(
                    sha256(
                        case_output
                    )
                    == hash_before,
                    (
                        "categoria inválida "
                        "preserva índice / "
                        f"{case_name}"
                    ),
                )


            # ==========================================
            # TESTE 13 — TAXONOMIA INEXISTENTE /
            # ERRO OPERACIONAL / ATOMICIDADE
            # ==========================================

            missing_root = (
                category_root
                / "taxonomia-ausente"
            )

            missing_articles = (
                missing_root
                / "artigos"
            )

            missing_output = (
                missing_root
                / "indice.json"
            )

            missing_articles.mkdir(
                parents=True
            )

            missing_output.write_text(
                "INDICE-PRESERVADO\n",
                encoding="utf-8",
            )

            missing_hash_before = sha256(
                missing_output
            )


            result = run_generator(
                missing_articles,
                missing_output,
                "--categories",
                str(
                    missing_root
                    / "nao-existe.json"
                ),
                cwd=root,
            )


            require_code(
                result,
                2,
                (
                    "taxonomia inexistente "
                    "retorna erro operacional"
                ),
            )


            assert_true(
                (
                    "arquivo de taxonomia "
                    "não encontrado"
                )
                in result.stdout,
                (
                    "taxonomia inexistente "
                    "é reportada"
                ),
            )


            assert_true(
                sha256(
                    missing_output
                )
                == missing_hash_before,
                (
                    "taxonomia inexistente "
                    "preserva índice"
                ),
            )


            # ==========================================
            # TESTE 14 — TAXONOMIA JSON INVÁLIDA /
            # ERRO OPERACIONAL / ATOMICIDADE
            # ==========================================

            invalid_taxonomy_root = (
                category_root
                / "taxonomia-invalida"
            )

            invalid_taxonomy_articles = (
                invalid_taxonomy_root
                / "artigos"
            )

            invalid_taxonomy_output = (
                invalid_taxonomy_root
                / "indice.json"
            )

            invalid_taxonomy_file = (
                invalid_taxonomy_root
                / "categorias.json"
            )

            invalid_taxonomy_articles.mkdir(
                parents=True
            )

            invalid_taxonomy_output.write_text(
                "INDICE-PRESERVADO\n",
                encoding="utf-8",
            )

            invalid_taxonomy_file.write_text(
                "{ isto nao e json\n",
                encoding="utf-8",
            )

            invalid_taxonomy_hash_before = (
                sha256(
                    invalid_taxonomy_output
                )
            )


            result = run_generator(
                invalid_taxonomy_articles,
                invalid_taxonomy_output,
                "--categories",
                str(
                    invalid_taxonomy_file
                ),
                cwd=root,
            )


            require_code(
                result,
                2,
                (
                    "taxonomia JSON inválida "
                    "retorna erro operacional"
                ),
            )


            assert_true(
                "JSON inválido"
                in result.stdout,
                (
                    "JSON inválido da taxonomia "
                    "é reportado"
                ),
            )


            assert_true(
                sha256(
                    invalid_taxonomy_output
                )
                == invalid_taxonomy_hash_before,
                (
                    "taxonomia inválida "
                    "preserva índice"
                ),
            )


            # ==========================================
            # RESULTADO
            # ==========================================

            print()
            print(
                "=" * 46
            )

            print(
                "RESULTADO: "
                "TODOS OS TESTES PASSARAM"
            )

            print(
                "Gerador de Índice "
                "DATADARK V1.0"
            )

            print(
                "=" * 46
            )


            return 0


    except Exception as exc:

        print()

        print(
            "RESULTADO: FALHA"
        )

        print(
            str(exc)
        )

        return 1


if __name__ == "__main__":

    sys.exit(
        main()
    )
