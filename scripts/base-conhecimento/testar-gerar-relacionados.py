#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Testes permanentes do
Gerador de Artigos Relacionados V1.
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
from typing import Any


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

GENERATOR_PATH = (
    SCRIPT_DIR
    / "gerar-relacionados.py"
)

TAXONOMY_PATH = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

INDEX_PATH = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

CATALOG_PATH = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
)

ARTICLES_DIR = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)


class TestFailure(
    RuntimeError
):
    pass


def load_generator() -> Any:
    spec = (
        importlib.util.spec_from_file_location(
            "datadark_related_generator_test",
            GENERATOR_PATH,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise TestFailure(
            "não foi possível carregar "
            "gerar-relacionados.py"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    try:

        spec.loader.exec_module(
            module
        )

    except Exception as exc:
        raise TestFailure(
            "falha ao importar gerador: "
            f"{exc}"
        ) from exc

    return module


GENERATOR = load_generator()


def check(
    condition: bool,
    label: str,
) -> None:
    if not condition:
        raise TestFailure(
            label
        )

    print(
        f"[OK] {label}"
    )


def normalized_set(
    values,
):
    return frozenset(
        GENERATOR.canonical_key(
            value
        )
        for value in values
    )


def article(
    *,
    editorial_id: str,
    slug: str,
    title: str,
    category_id: str,
    keywords=(),
    aliases=(),
):
    return GENERATOR.Article(
        editorial_id=editorial_id,
        slug=slug,
        title=title,
        category_id=category_id,
        keyword_keys=(
            normalized_set(
                keywords
            )
        ),
        alias_keys=(
            normalized_set(
                aliases
            )
        ),
        title_tokens=(
            GENERATOR.significant_title_tokens(
                title
            )
        ),
    )


def sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as stream:

        while True:

            block = stream.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def official_fingerprint():
    paths = [
        TAXONOMY_PATH,
        INDEX_PATH,
        CATALOG_PATH,
    ]

    paths.extend(
        sorted(
            path
            for path in (
                ARTICLES_DIR.glob(
                    "*.html"
                )
            )
            if (
                path.is_file()
                and
                not path.name.startswith(
                    "_"
                )
            )
        )
    )

    return {
        str(
            path.relative_to(
                ROOT
            )
        ):
            sha256(
                path
            )
        for path in paths
    }


def run_generator(
    *arguments: str,
):
    environment = (
        os.environ.copy()
    )

    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"

    return subprocess.run(
        [
            sys.executable,
            str(
                GENERATOR_PATH
            ),
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_constants():
    check(
        GENERATOR.VERSION == 1,
        "version do relacionamento é 1",
    )

    check(
        GENERATOR.MAX_RELATED == 3,
        "MAX_RELATED=3",
    )

    check(
        GENERATOR.MIN_SCORE == 40,
        "MIN_SCORE=40",
    )

    check(
        (
            GENERATOR.SAME_CATEGORY_SCORE
            == 100
        ),
        "mesma categoria vale 100",
    )

    check(
        GENERATOR.SAME_GROUP_SCORE == 40,
        "mesmo grupo vale 40",
    )

    check(
        (
            GENERATOR.SHARED_KEYWORD_SCORE
            == 20
        ),
        "keyword compartilhada vale 20",
    )

    check(
        (
            GENERATOR.SHARED_ALIAS_SCORE
            == 15
        ),
        "alias compartilhado vale 15",
    )

    check(
        (
            GENERATOR.SHARED_TITLE_TOKEN_SCORE
            == 5
        ),
        "token de título vale 5",
    )


def test_score_contract():
    source = article(
        editorial_id="DD-KB-900001",
        slug="origem-score",
        title=(
            "Alpha Bravo Charlie "
            "Delta Echo"
        ),
        category_id="categoria-a",
        keywords=(
            "um",
            "dois",
            "tres",
            "quatro",
        ),
        aliases=(
            "alias um",
            "alias dois",
            "alias tres",
        ),
    )

    candidate = article(
        editorial_id="DD-KB-900002",
        slug="candidato-score",
        title=(
            "Alpha Bravo Charlie "
            "Delta Echo"
        ),
        category_id="categoria-b",
        keywords=(
            "um",
            "dois",
            "tres",
            "quatro",
        ),
        aliases=(
            "alias um",
            "alias dois",
            "alias tres",
        ),
    )

    breakdown = (
        GENERATOR.score_candidate(
            source,
            candidate,
            {},
        )
    )

    check(
        breakdown.keyword_score == 60,
        "score de keywords respeita teto 60",
    )

    check(
        breakdown.alias_score == 30,
        "score de aliases respeita teto 30",
    )

    check(
        breakdown.title_score == 20,
        "score de título respeita teto 20",
    )

    check(
        breakdown.total == 110,
        "soma dos scores textuais é determinística",
    )

    same_category = article(
        editorial_id="DD-KB-900003",
        slug="mesma-categoria",
        title="Titulo distinto",
        category_id="categoria-a",
    )

    category_breakdown = (
        GENERATOR.score_candidate(
            source,
            same_category,
            {},
        )
    )

    check(
        category_breakdown.category_score
        == 100,
        "score de mesma categoria aplicado",
    )

    group_candidate = article(
        editorial_id="DD-KB-900004",
        slug="mesmo-grupo",
        title="Outro titulo",
        category_id="categoria-b",
    )

    group_breakdown = (
        GENERATOR.score_candidate(
            source,
            group_candidate,
            {
                "categoria-a":
                    frozenset(
                        {
                            "grupo-1"
                        }
                    ),
                "categoria-b":
                    frozenset(
                        {
                            "grupo-1"
                        }
                    ),
            },
        )
    )

    check(
        group_breakdown.group_score
        == 40,
        "score de mesmo grupo aplicado",
    )


def test_minimum_score():
    source = article(
        editorial_id="DD-KB-910001",
        slug="origem-minimo",
        title="Origem",
        category_id="rede",
    )

    group_candidate = article(
        editorial_id="DD-KB-910002",
        slug="candidato-grupo",
        title="Destino Grupo",
        category_id="wifi",
    )

    weak_candidate = article(
        editorial_id="DD-KB-910003",
        slug="candidato-fraco",
        title="Destino Fraco",
        category_id="hardware",
        keywords=(
            "dns",
        ),
    )

    source_with_keyword = article(
        editorial_id="DD-KB-910004",
        slug="origem-keyword",
        title="Origem Keyword",
        category_id="memoria",
        keywords=(
            "dns",
        ),
    )

    relations = (
        GENERATOR.build_relations(
            (
                source,
                group_candidate,
            ),
            {
                "rede":
                    frozenset(
                        {
                            "area-rede"
                        }
                    ),
                "wifi":
                    frozenset(
                        {
                            "area-rede"
                        }
                    ),
            },
        )
    )

    check(
        relations[
            source.slug
        ] == [
            group_candidate.slug
        ],
        "score 40 é elegível",
    )

    weak_breakdown = (
        GENERATOR.score_candidate(
            source_with_keyword,
            weak_candidate,
            {},
        )
    )

    check(
        weak_breakdown.total == 20,
        "uma keyword isolada vale 20",
    )

    check(
        (
            weak_breakdown.total
            < GENERATOR.MIN_SCORE
        ),
        "score 20 fica abaixo do limiar",
    )


def test_maximum_and_tiebreak():
    source = article(
        editorial_id="DD-KB-920001",
        slug="origem-ranking",
        title="Origem",
        category_id="hardware",
    )

    alpha = article(
        editorial_id="DD-KB-920002",
        slug="artigo-alpha",
        title="Alpha",
        category_id="hardware",
    )

    bravo = article(
        editorial_id="DD-KB-920003",
        slug="artigo-bravo",
        title="Bravo",
        category_id="hardware",
    )

    charlie = article(
        editorial_id="DD-KB-920004",
        slug="artigo-charlie",
        title="Charlie",
        category_id="hardware",
    )

    delta = article(
        editorial_id="DD-KB-920005",
        slug="artigo-delta",
        title="Delta",
        category_id="hardware",
    )

    relations = (
        GENERATOR.build_relations(
            (
                delta,
                source,
                charlie,
                alpha,
                bravo,
            ),
            {},
        )
    )

    check(
        relations[
            source.slug
        ] == [
            alpha.slug,
            bravo.slug,
            charlie.slug,
        ],
        (
            "desempate é title normalizado "
            "e limita em três"
        ),
    )

    check(
        len(
            relations[
                source.slug
            ]
        )
        == GENERATOR.MAX_RELATED,
        "MAX_RELATED aplicado",
    )


def test_zero_relations():
    first = article(
        editorial_id="DD-KB-930001",
        slug="artigo-memoria",
        title="Memoria RAM",
        category_id="memoria",
    )

    second = article(
        editorial_id="DD-KB-930002",
        slug="artigo-notebook",
        title="Notebook Energia",
        category_id="notebook",
    )

    relations = (
        GENERATOR.build_relations(
            (
                first,
                second,
            ),
            {},
        )
    )

    check(
        relations[
            first.slug
        ] == [],
        "zero relacionados é válido / origem",
    )

    check(
        relations[
            second.slug
        ] == [],
        "zero relacionados é válido / destino",
    )


def test_self_reference():
    source = article(
        editorial_id="DD-KB-940001",
        slug="origem-self",
        title="Origem",
        category_id="hardware",
    )

    same_slug = article(
        editorial_id="DD-KB-940002",
        slug="origem-self",
        title="Mesmo Slug",
        category_id="hardware",
    )

    same_id = article(
        editorial_id="DD-KB-940001",
        slug="outro-slug",
        title="Mesmo ID",
        category_id="hardware",
    )

    legitimate = article(
        editorial_id="DD-KB-940003",
        slug="destino-legitimo",
        title="Destino",
        category_id="hardware",
    )

    ranked = (
        GENERATOR.rank_candidates(
            source,
            (
                source,
                same_slug,
                same_id,
                legitimate,
            ),
            {},
        )
    )

    slugs = [
        candidate.slug
        for candidate, _
        in ranked
    ]

    check(
        slugs == [
            legitimate.slug
        ],
        (
            "auto-relacionamento bloqueado "
            "por slug e ID editorial"
        ),
    )


def test_serialization():
    relations = {
        "artigo-a": [
            "artigo-b"
        ],
        "artigo-b": [],
    }

    first = (
        GENERATOR.serialize_relations(
            relations
        )
    )

    second = (
        GENERATOR.serialize_relations(
            relations
        )
    )

    check(
        first == second,
        "serialização determinística",
    )

    parsed = json.loads(
        first
    )

    check(
        parsed == {
            "version":
                1,
            "articles":
                relations,
        },
        "schema do artefato V1",
    )


def load_official_relations():
    GENERATOR.validate_official_editorial_state(
        catalog_path=CATALOG_PATH,
        articles_dir=ARTICLES_DIR,
        index_path=INDEX_PATH,
        categories_path=TAXONOMY_PATH,
    )

    taxonomy = (
        GENERATOR.load_taxonomy(
            TAXONOMY_PATH
        )
    )

    catalog = (
        GENERATOR.read_json(
            CATALOG_PATH
        )
    )

    published = (
        GENERATOR.validate_catalog(
            catalog,
            taxonomy,
        )
    )

    index = (
        GENERATOR.read_json(
            INDEX_PATH
        )
    )

    articles = (
        GENERATOR.validate_index(
            index,
            published,
            taxonomy,
        )
    )

    group_map = (
        GENERATOR.build_group_map(
            taxonomy
        )
    )

    relations = (
        GENERATOR.build_relations(
            articles,
            group_map,
        )
    )

    GENERATOR.validate_relations(
        relations,
        articles,
    )

    return (
        articles,
        relations,
    )


def test_official_integration():
    articles, relations = (
        load_official_relations()
    )

    published = {
        item.slug
        for item in articles
    }

    check(
        bool(
            articles
        ),
        "base oficial possui artigos publicados",
    )

    check(
        set(
            relations
        )
        == published,
        (
            "artefato cobre exatamente "
            "os published"
        ),
    )

    for source, targets in (
        relations.items()
    ):

        check(
            len(targets)
            <= GENERATOR.MAX_RELATED,
            f"{source}: máximo de três",
        )

        check(
            source not in targets,
            f"{source}: sem self-reference",
        )

        check(
            all(
                target in published
                for target in targets
            ),
            f"{source}: destinos published",
        )


def test_cli():
    _, expected_relations = (
        load_official_relations()
    )

    expected_text = (
        GENERATOR.serialize_relations(
            expected_relations
        )
    )

    with tempfile.TemporaryDirectory(
        prefix="datadark-related-test-"
    ) as temporary:

        temporary_path = Path(
            temporary
        )

        output = (
            temporary_path
            / "relacionados.json"
        )

        result = run_generator(
            "--output",
            str(
                output
            ),
        )

        check(
            result.returncode == 0,
            "CLI gera artefato temporário",
        )

        if result.returncode != 0:
            raise TestFailure(
                result.stdout
                + result.stderr
            )

        check(
            output.is_file(),
            "CLI criou saída",
        )

        check(
            output.read_text(
                encoding="utf-8"
            )
            == expected_text,
            (
                "CLI produz exatamente "
                "o resultado do núcleo"
            ),
        )

        original = output.read_bytes()

        check_result = run_generator(
            "--check",
            "--output",
            str(
                output
            ),
        )

        check(
            check_result.returncode == 0,
            "--check aceita artefato atualizado",
        )

        output.write_bytes(
            original
            + b"\n"
        )

        divergent_before = (
            output.read_bytes()
        )

        divergent_result = (
            run_generator(
                "--check",
                "--output",
                str(
                    output
                ),
            )
        )

        check(
            divergent_result.returncode == 1,
            "--check detecta divergência",
        )

        check(
            output.read_bytes()
            == divergent_before,
            "--check nunca modifica a saída",
        )

        missing_output = (
            temporary_path
            / "ausente.json"
        )

        missing_result = (
            run_generator(
                "--check",
                "--output",
                str(
                    missing_output
                ),
            )
        )

        check(
            missing_result.returncode == 1,
            "--check detecta saída ausente",
        )

        check(
            not missing_output.exists(),
            (
                "--check não cria "
                "arquivo ausente"
            ),
        )


def test_fail_closed():
    with tempfile.TemporaryDirectory(
        prefix="datadark-related-fail-"
    ) as temporary:

        temporary_path = Path(
            temporary
        )

        copied_articles = (
            temporary_path
            / "artigos"
        )

        copied_articles.mkdir()

        public_articles = sorted(
            path
            for path in (
                ARTICLES_DIR.glob(
                    "*.html"
                )
            )
            if (
                path.is_file()
                and
                not path.name.startswith(
                    "_"
                )
            )
        )

        check(
            bool(
                public_articles
            ),
            (
                "fixture fail-closed possui "
                "artigo público"
            ),
        )

        for source in public_articles:

            shutil.copy2(
                source,
                copied_articles
                / source.name,
            )

        removed = (
            copied_articles
            / public_articles[0].name
        )

        removed.unlink()

        output = (
            temporary_path
            / "relacionados.json"
        )

        result = run_generator(
            "--articles-dir",
            str(
                copied_articles
            ),
            "--output",
            str(
                output
            ),
        )

        check(
            result.returncode == 2,
            (
                "estado editorial inválido "
                "retorna exit 2"
            ),
        )

        check(
            "validação editorial oficial"
            in result.stdout,
            (
                "fail-closed passa pelo "
                "validador oficial"
            ),
        )

        check(
            not output.exists(),
            (
                "fail-closed não cria "
                "artefato parcial"
            ),
        )


def test_explain():
    articles, _ = (
        load_official_relations()
    )

    source = articles[0]

    valid = run_generator(
        "--explain",
        source.slug,
    )

    check(
        valid.returncode == 0,
        "--explain aceita slug published",
    )

    check(
        (
            f"ORIGEM: {source.slug}"
            in valid.stdout
        ),
        "--explain identifica origem",
    )

    invalid = run_generator(
        "--explain",
        "slug-inexistente-de-teste",
    )

    check(
        invalid.returncode == 2,
        "--explain rejeita slug inexistente",
    )


def main() -> int:
    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do Gerador de "
        "Artigos Relacionados V1"
    )

    print(
        "=============================================="
    )

    print()

    before = (
        official_fingerprint()
    )

    try:

        test_constants()
        test_score_contract()
        test_minimum_score()
        test_maximum_and_tiebreak()
        test_zero_relations()
        test_self_reference()
        test_serialization()
        test_official_integration()
        test_cli()
        test_fail_closed()
        test_explain()

        after = (
            official_fingerprint()
        )

        check(
            before == after,
            (
                "artefatos editoriais oficiais "
                "permaneceram imutáveis"
            ),
        )

    except (
        TestFailure,
        GENERATOR.RelatedError,
    ) as exc:

        print()
        print(
            f"[ERRO] {exc}"
        )

        print()
        print(
            "=============================================="
        )

        print(
            "RESULTADO: TESTES DOS "
            "RELACIONADOS FALHARAM"
        )

        print(
            "RELACIONADOS_TESTES=1"
        )

        print(
            "=============================================="
        )

        return 1

    except Exception as exc:

        print()
        print(
            "ERRO ESTRUTURAL NÃO TRATADO: "
            f"{exc}"
        )

        print()
        print(
            "RELACIONADOS_TESTES=1"
        )

        return 1

    print()

    print(
        "=============================================="
    )

    print(
        "RESULTADO: TODOS OS TESTES DO "
        "GERADOR DE RELACIONADOS PASSARAM"
    )

    print(
        "RELACIONADOS_TESTES=0"
    )

    print(
        "=============================================="
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
