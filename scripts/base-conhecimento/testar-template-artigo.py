#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 7.5 — Testes do Template Oficial de Artigo V1.0

Responsabilidades:
- validar o contrato estrutural do template;
- materializar um artigo exclusivamente em diretório temporário;
- executar o validador oficial;
- executar o gerador oficial;
- conferir a entrada de índice resultante;
- nunca modificar artigos ou índice oficiais.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

TEMPLATE = (
    ROOT
    / "scripts"
    / "base-conhecimento"
    / "templates"
    / "artigo-v1.html"
)

VALIDATOR = (
    ROOT
    / "scripts"
    / "base-conhecimento"
    / "validar-artigos.py"
)

GENERATOR = (
    ROOT
    / "scripts"
    / "base-conhecimento"
    / "gerar-indice.py"
)

TAXONOMY = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)


PLACEHOLDER_COUNTS = {
    "@@TITLE@@": 2,
    "@@TITLE_ATTRIBUTE@@": 2,
    "@@DESCRIPTION@@": 1,
    "@@DESCRIPTION_ATTRIBUTE@@": 3,
    "@@KEYWORDS@@": 1,
    "@@ALIASES@@": 1,
    "@@CATEGORY_ID@@": 1,
    "@@CATEGORY_LABEL@@": 2,
    "@@CANONICAL_URL@@": 2,
    "@@SEO_JSON_LD@@": 1,
    "@@OVERVIEW@@": 1,
    "@@DIAGNOSIS@@": 1,
    "@@PROCEDURE_STEPS@@": 1,
    "@@VALIDATION@@": 1,
    "@@NOTES@@": 1,
}


REPLACEMENTS = {
    "@@TITLE@@":
        "Computador não liga e não emite nenhum sinal",

    "@@TITLE_ATTRIBUTE@@":
        "Computador não liga e não emite nenhum sinal",

    "@@DESCRIPTION@@":
        (
            "Procedimento técnico para diagnóstico inicial "
            "de computador que não apresenta sinais de energia."
        ),

    "@@DESCRIPTION_ATTRIBUTE@@":
        (
            "Procedimento técnico para diagnóstico inicial "
            "de computador que não apresenta sinais de energia."
        ),

    "@@KEYWORDS@@":
        (
            "computador não liga, energia, fonte, "
            "placa mãe, hardware"
        ),

    "@@ALIASES@@":
        (
            "pc não liga, computador sem sinal, "
            "computador sem energia"
        ),

    "@@CATEGORY_ID@@":
        "hardware",

    "@@CANONICAL_URL@@":
        'https://datadark.com.br/base-conhecimento/artigos/computador-nao-liga-e-nao-emite-nenhum-sinal.html',

    "@@SEO_JSON_LD@@":
        '{"@context":"https://schema.org","@type":"TechArticle","headline":"Computador não liga e não emite nenhum sinal","description":"Procedimento técnico para diagnóstico inicial de computador que não apresenta sinais de energia.","inLanguage":"pt-BR","url":"https://datadark.com.br/base-conhecimento/artigos/computador-nao-liga-e-nao-emite-nenhum-sinal.html","mainEntityOfPage":{"@type":"WebPage","@id":"https://datadark.com.br/base-conhecimento/artigos/computador-nao-liga-e-nao-emite-nenhum-sinal.html"},"publisher":{"@type":"Organization","name":"DATADARK Tecnologia","url":"https://datadark.com.br/"}}',

    "@@CATEGORY_LABEL@@":
        "Hardware",

    "@@OVERVIEW@@":
        (
            "Sequência inicial para identificar falhas de "
            "alimentação e inicialização do equipamento."
        ),

    "@@DIAGNOSIS@@":
        (
            "Confirmar alimentação, conexões e sinais de "
            "acionamento antes da substituição de componentes."
        ),

    "@@PROCEDURE_STEPS@@":
        (
            "<li>Confirmar a alimentação elétrica externa.</li>\n"
            "<li>Verificar as conexões da fonte.</li>\n"
            "<li>Inspecionar o circuito de acionamento.</li>\n"
            "<li>Realizar testes controlados dos componentes.</li>"
        ),

    "@@VALIDATION@@":
        (
            "Repetir o acionamento após cada intervenção e "
            "registrar qualquer mudança de comportamento."
        ),

    "@@NOTES@@":
        (
            "Interromper o procedimento diante de sinais de "
            "curto-circuito, superaquecimento ou dano físico."
        ),
}


EXPECTED_ENTRY = {
    "slug":
        "computador-nao-liga-e-nao-emite-nenhum-sinal",

    "title":
        "Computador não liga e não emite nenhum sinal",

    "description":
        (
            "Procedimento técnico para diagnóstico inicial "
            "de computador que não apresenta sinais de energia."
        ),

    "url":
        (
            "artigos/"
            "computador-nao-liga-e-nao-emite-nenhum-sinal.html"
        ),

    "category_id":
        "hardware",

    "category":
        "Hardware",

    "keywords": [
        "computador não liga",
        "energia",
        "fonte",
        "placa mãe",
        "hardware",
    ],

    "aliases": [
        "pc não liga",
        "computador sem sinal",
        "computador sem energia",
    ],
}


def require(
    condition: bool,
    description: str,
) -> None:

    if not condition:
        raise AssertionError(
            description
        )

    print(
        f"[OK] {description}"
    )


def run(
    command: list[str],
) -> subprocess.CompletedProcess[str]:

    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do Template Oficial de Artigo V1.0"
    )

    print(
        "=" * 46
    )


    require(
        TEMPLATE.is_file(),
        "template oficial existe",
    )


    template_text = TEMPLATE.read_text(
        encoding="utf-8"
    )


    for token, expected_count in (
        PLACEHOLDER_COUNTS.items()
    ):

        actual_count = (
            template_text.count(token)
        )

        require(
            actual_count == expected_count,
            (
                f"placeholder {token}: "
                f"{expected_count} ocorrência(s)"
            ),
        )


    require(
        template_text.lower().count(
            "<script"
        ) == 1,
        "template contém exatamente um script JSON-LD",
    )

    require(
        'type="application/ld+json"'
        in template_text.lower(),
        "script do template é JSON-LD",
    )

    require(
        "<script src="
        not in template_text.lower(),
        "template não contém script executável externo",
    )

    require(
        "<iframe" not in template_text.lower(),
        "template não contém iframe",
    )

    require(
        "<form" not in template_text.lower(),
        "template não contém formulário",
    )

    require(
        'rel="stylesheet"' not in template_text.lower(),
        "template não contém stylesheet externo/local",
    )


    with tempfile.TemporaryDirectory(
        prefix="datadark-template-artigo-"
    ) as temp_name:

        temp_root = Path(temp_name)

        articles = (
            temp_root
            / "artigos"
        )

        articles.mkdir()

        article = (
            articles
            / (
                "computador-nao-liga-e-nao-"
                "emite-nenhum-sinal.html"
            )
        )

        output = (
            temp_root
            / "indice.json"
        )

        materialized = template_text


        for token, value in (
            REPLACEMENTS.items()
        ):

            materialized = (
                materialized.replace(
                    token,
                    value,
                )
            )


        require(
            "@@" not in materialized,
            "materialização não preserva placeholders",
        )


        article.write_text(
            materialized,
            encoding="utf-8",
        )


        validator_result = run(
            [
                sys.executable,
                str(VALIDATOR),
                "--directory",
                str(articles),
                "--categories",
                str(TAXONOMY),
            ]
        )


        if validator_result.returncode != 0:

            print(
                validator_result.stdout
            )


        require(
            validator_result.returncode == 0,
            "validador oficial aceita o artigo materializado",
        )

        require(
            "Avisos: 0"
            in validator_result.stdout,
            "artigo materializado não produz warnings",
        )


        generator_result = run(
            [
                sys.executable,
                str(GENERATOR),
                "--articles-dir",
                str(articles),
                "--output",
                str(output),
                "--categories",
                str(TAXONOMY),
            ]
        )


        if generator_result.returncode != 0:

            print(
                generator_result.stdout
            )


        require(
            generator_result.returncode == 0,
            "gerador oficial indexa o artigo materializado",
        )

        require(
            output.is_file(),
            "índice temporário foi criado",
        )


        data = json.loads(
            output.read_text(
                encoding="utf-8"
            )
        )


        require(
            len(data) == 1,
            "índice temporário contém exatamente um artigo",
        )


        require(
            data[0] == EXPECTED_ENTRY,
            "entrada gerada corresponde ao contrato oficial",
        )


    print()
    print(
        "=" * 46
    )

    print(
        "RESULTADO: TODOS OS TESTES DO TEMPLATE PASSARAM"
    )

    print(
        "Template Oficial de Artigo DATADARK V1.0"
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

    except Exception as exc:

        print()
        print(
            f"RESULTADO: FALHA — {exc}"
        )

        raise SystemExit(1)
