#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Testes do Gerador Oficial de Artigos V1.0 — dry-run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent

ROOT = SCRIPT_DIR.parents[1]

CREATOR = (
    SCRIPT_DIR
    / "criar-artigo.py"
)

MONITORED = (
    ROOT
    / "base-conhecimento"
    / "artigos"
    / "wifi-conecta-mas-fica-sem-internet.html",

    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json",

    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json",

    SCRIPT_DIR
    / "templates"
    / "artigo-v1.html",
)


def sha256(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def snapshot() -> dict[str, str]:

    return {
        str(path):
            sha256(path)
        for path in MONITORED
    }


def run_creator(
    payload: dict,
) -> subprocess.CompletedProcess:

    with tempfile.TemporaryDirectory(
        prefix="datadark-kb-test-input-"
    ) as temporary:

        input_path = (
            Path(temporary)
            / "artigo.json"
        )

        input_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


        environment = os.environ.copy()

        environment[
            "PYTHONDONTWRITEBYTECODE"
        ] = "1"


        return subprocess.run(
            [
                sys.executable,
                str(CREATOR),
                "--input",
                str(input_path),
            ],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )


def load_creator_module():

    spec = (
        importlib.util
        .spec_from_file_location(
            "_datadark_criar_artigo",
            CREATOR,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            "não foi possível carregar criar-artigo.py"
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


BASE_PAYLOAD = {
    "title":
        "Teste Seguro de Rede Wi-Fi",

    "category_id":
        "wifi",

    "description":
        "Artigo técnico temporário para validar o gerador.",

    "keywords": [
        "wifi",
        "rede sem fio",
        "teste seguro",
    ],

    "aliases": [
        "teste de wifi",
        "validação de rede sem fio",
    ],

    "overview":
        "Visão geral técnica do problema.",

    "diagnosis":
        "Diagnóstico técnico antes de qualquer alteração.",

    "procedure_steps": [
        "Confirme o estado inicial.",
        "Execute o teste técnico.",
        "Registre o resultado.",
    ],

    "validation":
        "Confirme o funcionamento após o procedimento.",

    "notes":
        "Não altere configurações sem diagnóstico prévio.",
}


before = snapshot()


result = run_creator(
    BASE_PAYLOAD
)


if result.returncode != 0:
    print(
        result.stdout
    )

    print(
        result.stderr,
        file=sys.stderr,
    )

    raise SystemExit(
        "ERRO: dry-run válido foi rejeitado."
    )


required_output = (
    "MODO=DRY_RUN",
    "SLUG=teste-seguro-de-rede-wi-fi",
    "CATEGORY_ID=wifi",
    "CATEGORY=Wi-Fi",
    "VALIDATOR=OK",
    "INDEX_GENERATOR=OK",
    "INDEX_CHECK=OK",
    "REPOSITORY_MODIFIED=NO",
    "RESULTADO=PRONTO_PARA_GRAVACAO",
)


for expected in required_output:

    if expected not in result.stdout:
        raise SystemExit(
            "ERRO: saída esperada ausente: "
            f"{expected}"
        )


print(
    "[OK] dry-run válido"
)


invalid_category = dict(
    BASE_PAYLOAD
)

invalid_category[
    "title"
] = "Teste Categoria Inválida"

invalid_category[
    "category_id"
] = "Wi-Fi"


result = run_creator(
    invalid_category
)


if result.returncode != 1:
    raise SystemExit(
        "ERRO: category_id não canônico "
        "não foi rejeitado."
    )


print(
    "[OK] category_id não canônico rejeitado"
)


duplicate = dict(
    BASE_PAYLOAD
)

duplicate[
    "title"
] = "Wi-Fi conecta, mas fica sem internet"


result = run_creator(
    duplicate
)


if result.returncode != 1:
    raise SystemExit(
        "ERRO: colisão com artigo existente "
        "não foi rejeitada."
    )


print(
    "[OK] colisão de slug rejeitada"
)


extra = dict(
    BASE_PAYLOAD
)

extra[
    "campo_extra"
] = "não permitido"


result = run_creator(
    extra
)


if result.returncode != 1:
    raise SystemExit(
        "ERRO: campo JSON extra "
        "não foi rejeitado."
    )


print(
    "[OK] campo JSON extra rejeitado"
)


comma = dict(
    BASE_PAYLOAD
)

comma[
    "title"
] = "Teste Vírgula em Palavra Chave"

comma[
    "keywords"
] = [
    "wifi, rede",
]


result = run_creator(
    comma
)


if result.returncode != 1:
    raise SystemExit(
        "ERRO: vírgula em keyword "
        "não foi rejeitada."
    )


print(
    "[OK] vírgula em keyword rejeitada"
)


placeholder = dict(
    BASE_PAYLOAD
)

placeholder[
    "title"
] = "Teste Placeholder"

placeholder[
    "notes"
] = "@@TITLE@@"


result = run_creator(
    placeholder
)


if result.returncode != 1:
    raise SystemExit(
        "ERRO: placeholder editorial "
        "não foi rejeitado."
    )


print(
    "[OK] marcador reservado rejeitado"
)


module = load_creator_module()


malicious = dict(
    BASE_PAYLOAD
)

malicious[
    "title"
] = "Teste <Seguro> & HTML"

malicious[
    "description"
] = (
    'Descrição com "aspas" e '
    "<script>alert(1)</script>."
)

malicious[
    "procedure_steps"
] = [
    '<img src=x onerror="alert(1)">',
]


taxonomy = (
    module.load_taxonomy(
        module.CATEGORIES_PATH
    )
)

category = (
    taxonomy.resolve_category(
        malicious["category_id"]
    )
)


rendered = module.render_article(
    malicious,
    category.label,
)


if "<script>" in rendered:
    raise SystemExit(
        "ERRO: script editorial não foi escapado."
    )


if "<img src=" in rendered:
    raise SystemExit(
        "ERRO: HTML editorial não foi escapado."
    )


if "&lt;script&gt;" not in rendered:
    raise SystemExit(
        "ERRO: escape de script não confirmado."
    )


if "&lt;img src=x onerror=" not in rendered:
    raise SystemExit(
        "ERRO: escape do item de procedimento "
        "não confirmado."
    )


print(
    "[OK] conteúdo HTML editorial escapado"
)


filename = module.slug_for_title(
    "Áudio Novo"
)


if filename != "audio-novo.html":
    raise SystemExit(
        "ERRO: algoritmo oficial de slug "
        f"retornou {filename!r}."
    )


print(
    "[OK] algoritmo oficial de slug reutilizado"
)


after = snapshot()


if before != after:
    raise SystemExit(
        "ERRO: testes modificaram artefatos "
        "oficiais da Base."
    )


print(
    "[OK] artefatos oficiais permaneceram imutáveis"
)


print()
print(
    "=============================================="
)

print(
    "RESULTADO: TESTES DO GERADOR DRY-RUN PASSARAM"
)

print(
    "GERADOR_ARTIGO_DRY_RUN=0"
)

print(
    "=============================================="
)
