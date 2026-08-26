#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Gerador de Artigos Relacionados V1.

Fontes oficiais:
- base-conhecimento/data/categorias.json
- base-conhecimento/data/indice.json
- scripts/base-conhecimento/editorial/catalogo.json

Artefato derivado:
- base-conhecimento/data/relacionados.json

Contrato V1:
- máximo de 3 relacionados;
- score mínimo de 40;
- somente artigos published;
- nenhuma relação manual;
- nenhum auto-relacionamento;
- resultado determinístico;
- grupos derivados exclusivamente da taxonomia oficial;
- fuzzy matching desabilitado.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from taxonomia import (
    canonical_key,
    load_taxonomy,
)


sys.dont_write_bytecode = True


SCRIPT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


ROOT = Path(
    __file__
).resolve().parents[2]

DEFAULT_TAXONOMY = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

DEFAULT_INDEX = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

DEFAULT_CATALOG = (
    ROOT
    / "scripts"
    / "base-conhecimento"
    / "editorial"
    / "catalogo.json"
)

DEFAULT_ARTICLES_DIR = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)

CATALOG_VALIDATOR = (
    SCRIPT_DIR
    / "validar-catalogo-editorial.py"
)

DEFAULT_OUTPUT = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "relacionados.json"
)


VERSION = 1

MAX_RELATED = 3
MIN_SCORE = 40

SAME_CATEGORY_SCORE = 100
SAME_GROUP_SCORE = 40

SHARED_KEYWORD_SCORE = 20
MAX_KEYWORD_SCORE = 60

SHARED_ALIAS_SCORE = 15
MAX_ALIAS_SCORE = 30

SHARED_TITLE_TOKEN_SCORE = 5
MAX_TITLE_SCORE = 20


CATALOG_FIELDS = {
    "id",
    "title",
    "slug",
    "category_id",
    "status",
    "priority",
    "created_on",
    "published_on",
    "review_due",
    "notes",
}

INDEX_FIELDS = {
    "slug",
    "title",
    "description",
    "url",
    "category_id",
    "category",
    "keywords",
    "aliases",
}


ARTICLE_ID_PATTERN = re.compile(
    r"^DD-KB-[0-9]{6}$"
)

SLUG_PATTERN = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)


STOPWORDS = frozenset(
    {
        "a",
        "as",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "sem",
        "um",
        "uma",
    }
)


class RelatedError(
    RuntimeError
):
    """Erro estrutural do Gerador de Relacionados."""


def load_catalog_validator() -> Any:
    if not CATALOG_VALIDATOR.is_file():
        raise RelatedError(
            "validador editorial oficial "
            "inexistente: "
            f"{CATALOG_VALIDATOR}"
        )

    spec = (
        importlib.util.spec_from_file_location(
            "datadark_catalog_validator",
            CATALOG_VALIDATOR,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RelatedError(
            "não foi possível carregar "
            "o validador editorial oficial"
        )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    try:

        spec.loader.exec_module(
            module
        )

    except Exception as exc:
        raise RelatedError(
            "falha ao carregar "
            "validador editorial oficial: "
            f"{exc}"
        ) from exc

    if (
        not hasattr(
            module,
            "validate_catalog",
        )
        or not hasattr(
            module,
            "CatalogValidationError",
        )
    ):
        raise RelatedError(
            "API do validador editorial "
            "oficial é incompatível"
        )

    return module


def validate_official_editorial_state(
    *,
    catalog_path: Path,
    articles_dir: Path,
    index_path: Path,
    categories_path: Path,
) -> None:
    validator = (
        load_catalog_validator()
    )

    try:

        validator.validate_catalog(
            catalog_path=catalog_path,
            articles_dir=articles_dir,
            index_path=index_path,
            categories_path=(
                categories_path
            ),
        )

    except validator.CatalogValidationError as exc:
        raise RelatedError(
            "validação editorial oficial "
            f"falhou: {exc}"
        ) from exc

    except Exception as exc:
        raise RelatedError(
            "falha inesperada na validação "
            f"editorial oficial: {exc}"
        ) from exc


@dataclass(
    frozen=True
)
class Article:
    editorial_id: str
    slug: str
    title: str
    category_id: str
    keyword_keys: frozenset[str]
    alias_keys: frozenset[str]
    title_tokens: frozenset[str]


@dataclass(
    frozen=True
)
class ScoreBreakdown:
    same_category: bool
    shared_groups: tuple[str, ...]
    shared_keywords: tuple[str, ...]
    shared_aliases: tuple[str, ...]
    shared_title_tokens: tuple[str, ...]
    category_score: int
    group_score: int
    keyword_score: int
    alias_score: int
    title_score: int
    total: int


def duplicate_key_guard(
    pairs: list[
        tuple[
            str,
            Any,
        ]
    ],
) -> dict[
    str,
    Any,
]:
    result = {}

    for key, value in pairs:

        if key in result:
            raise RelatedError(
                "chave JSON duplicada: "
                f"{key!r}"
            )

        result[key] = value

    return result


def read_json(
    path: Path,
) -> Any:
    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as stream:

            return json.load(
                stream,
                object_pairs_hook=(
                    duplicate_key_guard
                ),
            )

    except RelatedError:
        raise

    except FileNotFoundError as exc:
        raise RelatedError(
            f"arquivo inexistente: {path}"
        ) from exc

    except PermissionError as exc:
        raise RelatedError(
            f"sem permissão para ler: {path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise RelatedError(
            "JSON inválido em "
            f"{path}: {exc}"
        ) from exc

    except OSError as exc:
        raise RelatedError(
            f"falha ao ler {path}: {exc}"
        ) from exc


def require_text(
    value: Any,
    label: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise RelatedError(
            f"{label} deve ser texto"
        )

    if not value:
        raise RelatedError(
            f"{label} não pode ser vazio"
        )

    if value != value.strip():
        raise RelatedError(
            f"{label} contém espaços "
            "externos"
        )

    return value


def normalized_values(
    values: Any,
    label: str,
) -> frozenset[str]:
    if not isinstance(
        values,
        list,
    ):
        raise RelatedError(
            f"{label} deve ser lista"
        )

    normalized = set()

    for position, value in enumerate(
        values
    ):

        text = require_text(
            value,
            f"{label}[{position}]",
        )

        key = canonical_key(
            text
        )

        if not key:
            raise RelatedError(
                f"{label}[{position}] "
                "normaliza para vazio"
            )

        if key in normalized:
            raise RelatedError(
                f"{label} contém valor "
                f"duplicado: {text!r}"
            )

        normalized.add(
            key
        )

    return frozenset(
        normalized
    )


def significant_title_tokens(
    title: str,
) -> frozenset[str]:
    normalized = canonical_key(
        title
    )

    tokens = {
        token
        for token in normalized.split()
        if (
            len(token) >= 3
            and token not in STOPWORDS
        )
    }

    return frozenset(
        tokens
    )


def validate_catalog(
    raw: Any,
    taxonomy: Any,
) -> dict[
    str,
    dict[
        str,
        Any,
    ],
]:
    if not isinstance(
        raw,
        dict,
    ):
        raise RelatedError(
            "catalogo.json deve possuir "
            "objeto raiz"
        )

    if set(
        raw
    ) != {
        "version",
        "articles",
    }:
        raise RelatedError(
            "campos raiz inválidos em "
            "catalogo.json"
        )

    if raw["version"] != 1:
        raise RelatedError(
            "version inválida em "
            "catalogo.json"
        )

    articles = raw[
        "articles"
    ]

    if not isinstance(
        articles,
        list,
    ):
        raise RelatedError(
            "catalogo.json.articles "
            "deve ser lista"
        )

    ids = set()
    slugs = set()

    published = {}

    for position, record in enumerate(
        articles
    ):

        label = (
            "catalogo.json.articles"
            f"[{position}]"
        )

        if not isinstance(
            record,
            dict,
        ):
            raise RelatedError(
                f"{label} deve ser objeto"
            )

        if set(
            record
        ) != CATALOG_FIELDS:
            raise RelatedError(
                f"{label} possui campos "
                "divergentes do contrato V1"
            )

        article_id = require_text(
            record["id"],
            f"{label}.id",
        )

        if not ARTICLE_ID_PATTERN.fullmatch(
            article_id
        ):
            raise RelatedError(
                f"{label}.id inválido: "
                f"{article_id!r}"
            )

        if article_id in ids:
            raise RelatedError(
                "id editorial duplicado: "
                f"{article_id}"
            )

        ids.add(
            article_id
        )

        slug = require_text(
            record["slug"],
            f"{label}.slug",
        )

        if not SLUG_PATTERN.fullmatch(
            slug
        ):
            raise RelatedError(
                f"{label}.slug inválido: "
                f"{slug!r}"
            )

        if slug in slugs:
            raise RelatedError(
                "slug duplicado no catálogo: "
                f"{slug}"
            )

        slugs.add(
            slug
        )

        title = require_text(
            record["title"],
            f"{label}.title",
        )

        category_id = require_text(
            record["category_id"],
            f"{label}.category_id",
        )

        try:

            taxonomy.resolve_category(
                category_id
            )

        except Exception as exc:
            raise RelatedError(
                f"{article_id}: "
                "category_id inválido: "
                f"{category_id!r}"
            ) from exc

        status = require_text(
            record["status"],
            f"{label}.status",
        )

        if status == "published":

            published[
                slug
            ] = {
                "id":
                    article_id,
                "slug":
                    slug,
                "title":
                    title,
                "category_id":
                    category_id,
            }

    return published


def validate_index(
    raw: Any,
    published: dict[
        str,
        dict[
            str,
            Any,
        ],
    ],
    taxonomy: Any,
) -> tuple[
    Article,
    ...,
]:
    if not isinstance(
        raw,
        list,
    ):
        raise RelatedError(
            "indice.json deve possuir "
            "uma lista na raiz"
        )

    by_slug = {}

    for position, entry in enumerate(
        raw
    ):

        label = (
            f"indice.json[{position}]"
        )

        if not isinstance(
            entry,
            dict,
        ):
            raise RelatedError(
                f"{label} deve ser objeto"
            )

        if set(
            entry
        ) != INDEX_FIELDS:
            raise RelatedError(
                f"{label} possui campos "
                "divergentes do contrato V1"
            )

        slug = require_text(
            entry["slug"],
            f"{label}.slug",
        )

        if not SLUG_PATTERN.fullmatch(
            slug
        ):
            raise RelatedError(
                f"{label}.slug inválido: "
                f"{slug!r}"
            )

        if slug in by_slug:
            raise RelatedError(
                "slug duplicado no índice: "
                f"{slug}"
            )

        title = require_text(
            entry["title"],
            f"{label}.title",
        )

        category_id = require_text(
            entry["category_id"],
            f"{label}.category_id",
        )

        try:

            category = (
                taxonomy.resolve_category(
                    category_id
                )
            )

        except Exception as exc:
            raise RelatedError(
                f"{slug}: category_id "
                f"inválido: {category_id!r}"
            ) from exc

        category_label = require_text(
            entry["category"],
            f"{label}.category",
        )

        if (
            category_label
            != category.label
        ):
            raise RelatedError(
                f"{slug}: label de categoria "
                "divergente da taxonomia"
            )

        expected_url = (
            f"artigos/{slug}.html"
        )

        if (
            entry["url"]
            != expected_url
        ):
            raise RelatedError(
                f"{slug}: URL divergente: "
                f"{entry['url']!r}"
            )

        keywords = normalized_values(
            entry["keywords"],
            f"{label}.keywords",
        )

        aliases = normalized_values(
            entry["aliases"],
            f"{label}.aliases",
        )

        catalog_record = (
            published.get(
                slug
            )
        )

        if catalog_record is None:
            raise RelatedError(
                f"{slug}: índice contém "
                "artigo não published"
            )

        by_slug[
            slug
        ] = Article(
            editorial_id=(
                catalog_record["id"]
            ),
            slug=slug,
            title=title,
            category_id=category_id,
            keyword_keys=keywords,
            alias_keys=aliases,
            title_tokens=(
                significant_title_tokens(
                    title
                )
            ),
        )

    published_slugs = set(
        published
    )

    index_slugs = set(
        by_slug
    )

    if (
        published_slugs
        != index_slugs
    ):
        missing = sorted(
            published_slugs
            - index_slugs
        )

        extra = sorted(
            index_slugs
            - published_slugs
        )

        raise RelatedError(
            "catálogo published e índice "
            "divergem; "
            f"ausentes={missing}; "
            f"extras={extra}"
        )

    for slug in sorted(
        published
    ):

        catalog_record = (
            published[
                slug
            ]
        )

        index_record = (
            by_slug[
                slug
            ]
        )

        if (
            catalog_record["title"]
            != index_record.title
        ):
            raise RelatedError(
                f"{slug}: title diverge "
                "entre catálogo e índice"
            )

        if (
            catalog_record["category_id"]
            != index_record.category_id
        ):
            raise RelatedError(
                f"{slug}: category_id diverge "
                "entre catálogo e índice"
            )

    return tuple(
        by_slug[
            slug
        ]
        for slug in sorted(
            by_slug
        )
    )


def build_group_map(
    taxonomy: Any,
) -> dict[
    str,
    frozenset[str],
]:
    mapping: dict[
        str,
        set[str],
    ] = {}

    for group in taxonomy.groups:

        for category_id in (
            group.category_ids
        ):

            mapping.setdefault(
                category_id,
                set(),
            ).add(
                group.id
            )

    return {
        category_id:
            frozenset(
                group_ids
            )
        for category_id, group_ids
        in mapping.items()
    }


def score_candidate(
    source: Article,
    candidate: Article,
    group_map: dict[
        str,
        frozenset[str],
    ],
) -> ScoreBreakdown:
    same_category = (
        source.category_id
        == candidate.category_id
    )

    source_groups = (
        group_map.get(
            source.category_id,
            frozenset(),
        )
    )

    candidate_groups = (
        group_map.get(
            candidate.category_id,
            frozenset(),
        )
    )

    shared_groups = tuple(
        sorted(
            source_groups
            & candidate_groups
        )
    )

    shared_keywords = tuple(
        sorted(
            source.keyword_keys
            & candidate.keyword_keys
        )
    )

    shared_aliases = tuple(
        sorted(
            source.alias_keys
            & candidate.alias_keys
        )
    )

    shared_title_tokens = tuple(
        sorted(
            source.title_tokens
            & candidate.title_tokens
        )
    )

    category_score = (
        SAME_CATEGORY_SCORE
        if same_category
        else 0
    )

    group_score = (
        SAME_GROUP_SCORE
        if shared_groups
        else 0
    )

    keyword_score = min(
        len(
            shared_keywords
        )
        * SHARED_KEYWORD_SCORE,
        MAX_KEYWORD_SCORE,
    )

    alias_score = min(
        len(
            shared_aliases
        )
        * SHARED_ALIAS_SCORE,
        MAX_ALIAS_SCORE,
    )

    title_score = min(
        len(
            shared_title_tokens
        )
        * SHARED_TITLE_TOKEN_SCORE,
        MAX_TITLE_SCORE,
    )

    total = (
        category_score
        + group_score
        + keyword_score
        + alias_score
        + title_score
    )

    return ScoreBreakdown(
        same_category=same_category,
        shared_groups=shared_groups,
        shared_keywords=shared_keywords,
        shared_aliases=shared_aliases,
        shared_title_tokens=(
            shared_title_tokens
        ),
        category_score=category_score,
        group_score=group_score,
        keyword_score=keyword_score,
        alias_score=alias_score,
        title_score=title_score,
        total=total,
    )


def rank_candidates(
    source: Article,
    articles: tuple[
        Article,
        ...,
    ],
    group_map: dict[
        str,
        frozenset[str],
    ],
) -> list[
    tuple[
        Article,
        ScoreBreakdown,
    ]
]:
    ranked = []

    for candidate in articles:

        if (
            candidate.slug
            == source.slug
            or
            candidate.editorial_id
            == source.editorial_id
        ):
            continue

        breakdown = (
            score_candidate(
                source,
                candidate,
                group_map,
            )
        )

        ranked.append(
            (
                candidate,
                breakdown,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[1].total,
            canonical_key(
                item[0].title
            ),
            item[0].slug,
        )
    )

    return ranked


def build_relations(
    articles: tuple[
        Article,
        ...,
    ],
    group_map: dict[
        str,
        frozenset[str],
    ],
) -> dict[
    str,
    list[str],
]:
    result = {}

    for source in sorted(
        articles,
        key=lambda item: item.slug,
    ):

        ranked = rank_candidates(
            source,
            articles,
            group_map,
        )

        eligible = [
            candidate.slug
            for candidate, breakdown
            in ranked
            if (
                breakdown.total
                >= MIN_SCORE
            )
        ]

        result[
            source.slug
        ] = eligible[
            :MAX_RELATED
        ]

    return result


def validate_relations(
    relations: dict[
        str,
        list[str],
    ],
    articles: tuple[
        Article,
        ...,
    ],
) -> None:
    published = {
        article.slug
        for article in articles
    }

    if set(
        relations
    ) != published:
        raise RelatedError(
            "artefato relacionado não cobre "
            "todos os artigos published"
        )

    for source, targets in (
        relations.items()
    ):

        if not isinstance(
            targets,
            list,
        ):
            raise RelatedError(
                f"{source}: relacionados "
                "deve ser lista"
            )

        if (
            len(targets)
            > MAX_RELATED
        ):
            raise RelatedError(
                f"{source}: mais de "
                f"{MAX_RELATED} relacionados"
            )

        if (
            len(targets)
            != len(
                set(
                    targets
                )
            )
        ):
            raise RelatedError(
                f"{source}: relacionado "
                "duplicado"
            )

        for target in targets:

            if target == source:
                raise RelatedError(
                    f"{source}: "
                    "auto-relacionamento"
                )

            if target not in published:
                raise RelatedError(
                    f"{source}: destino "
                    "não publicado: "
                    f"{target}"
                )


def serialize_relations(
    relations: dict[
        str,
        list[str],
    ],
) -> str:
    payload = {
        "version":
            VERSION,
        "articles":
            relations,
    }

    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def output_mode(
    output: Path,
    fallback: Path,
) -> int:
    if output.exists():

        return stat.S_IMODE(
            output.stat().st_mode
        )

    if fallback.exists():

        return stat.S_IMODE(
            fallback.stat().st_mode
        )

    return 0o644


def write_atomic(
    output: Path,
    content: str,
    fallback_mode_path: Path,
) -> None:
    parent = output.parent

    if not parent.is_dir():
        raise RelatedError(
            "diretório de saída "
            f"inexistente: {parent}"
        )

    mode = output_mode(
        output,
        fallback_mode_path,
    )

    descriptor = None
    temporary_name = None

    try:

        descriptor, temporary_name = (
            tempfile.mkstemp(
                prefix=(
                    f".{output.name}."
                ),
                suffix=".tmp",
                dir=str(
                    parent
                ),
            )
        )

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as stream:

            descriptor = None

            stream.write(
                content
            )

            stream.flush()

            os.fsync(
                stream.fileno()
            )

        os.chmod(
            temporary_name,
            mode,
        )

        os.replace(
            temporary_name,
            output,
        )

        temporary_name = None

    except OSError as exc:
        raise RelatedError(
            "falha ao persistir "
            f"{output}: {exc}"
        ) from exc

    finally:

        if descriptor is not None:

            try:
                os.close(
                    descriptor
                )
            except OSError:
                pass

        if temporary_name is not None:

            try:
                Path(
                    temporary_name
                ).unlink()
            except FileNotFoundError:
                pass


def print_explain(
    source_slug: str,
    articles: tuple[
        Article,
        ...,
    ],
    group_map: dict[
        str,
        frozenset[str],
    ],
) -> None:
    by_slug = {
        article.slug:
            article
        for article in articles
    }

    source = by_slug.get(
        source_slug
    )

    if source is None:
        raise RelatedError(
            "slug não publicado para "
            f"--explain: {source_slug}"
        )

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Explicação do Relacionamento V1"
    )

    print(
        "=============================================="
    )

    print(
        f"ORIGEM: {source.slug}"
    )

    print(
        f"TITULO: {source.title}"
    )

    print()

    ranked = rank_candidates(
        source,
        articles,
        group_map,
    )

    for position, (
        candidate,
        breakdown,
    ) in enumerate(
        ranked,
        start=1,
    ):

        eligible = (
            "SIM"
            if (
                breakdown.total
                >= MIN_SCORE
            )
            else "NAO"
        )

        print(
            f"{position:02d}. "
            f"{candidate.slug}"
        )

        print(
            f"    score="
            f"{breakdown.total}"
        )

        print(
            "    same_category="
            f"{breakdown.category_score}"
        )

        print(
            "    same_group="
            f"{breakdown.group_score}"
        )

        print(
            "    keywords="
            f"{breakdown.keyword_score} "
            f"{list(breakdown.shared_keywords)}"
        )

        print(
            "    aliases="
            f"{breakdown.alias_score} "
            f"{list(breakdown.shared_aliases)}"
        )

        print(
            "    title="
            f"{breakdown.title_score} "
            f"{list(breakdown.shared_title_tokens)}"
        )

        print(
            f"    elegivel={eligible}"
        )

        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera o grafo determinístico "
            "de artigos relacionados da "
            "Base de Conhecimento DATADARK."
        )
    )

    mode = (
        parser.add_mutually_exclusive_group()
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verifica se relacionados.json "
            "está atualizado sem escrever."
        ),
    )

    mode.add_argument(
        "--explain",
        metavar="SLUG",
        help=(
            "Explica o score dos candidatos "
            "para um artigo publicado."
        ),
    )

    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=DEFAULT_TAXONOMY,
    )

    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
    )

    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=DEFAULT_ARTICLES_DIR,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:

        validate_official_editorial_state(
            catalog_path=args.catalog,
            articles_dir=args.articles_dir,
            index_path=args.index,
            categories_path=args.taxonomy,
        )

        taxonomy = load_taxonomy(
            args.taxonomy
        )

        catalog = read_json(
            args.catalog
        )

        published = (
            validate_catalog(
                catalog,
                taxonomy,
            )
        )

        index = read_json(
            args.index
        )

        articles = validate_index(
            index,
            published,
            taxonomy,
        )

        group_map = (
            build_group_map(
                taxonomy
            )
        )

        relations = (
            build_relations(
                articles,
                group_map,
            )
        )

        validate_relations(
            relations,
            articles,
        )

        content = (
            serialize_relations(
                relations
            )
        )

        if args.explain:

            print_explain(
                args.explain,
                articles,
                group_map,
            )

            return 0

        if args.check:

            try:

                current = (
                    args.output.read_text(
                        encoding="utf-8"
                    )
                )

            except FileNotFoundError:

                print(
                    "RESULTADO: "
                    "RELACIONADOS DESATUALIZADOS"
                )

                print(
                    "Motivo: arquivo de saída "
                    "não existe."
                )

                return 1

            except OSError as exc:
                raise RelatedError(
                    "falha ao ler saída "
                    f"{args.output}: {exc}"
                ) from exc

            if current != content:

                print(
                    "RESULTADO: "
                    "RELACIONADOS DESATUALIZADOS"
                )

                return 1

            print(
                "RESULTADO: "
                "RELACIONADOS OK"
            )

            print(
                "RELACIONADOS=0"
            )

            return 0

        write_atomic(
            args.output,
            content,
            args.index,
        )

        total_relations = sum(
            len(
                targets
            )
            for targets in (
                relations.values()
            )
        )

        without_relations = sum(
            1
            for targets in (
                relations.values()
            )
            if not targets
        )

        print(
            "Base de Conhecimento DATADARK"
        )

        print(
            "Gerador de Artigos "
            "Relacionados V1"
        )

        print(
            "=============================================="
        )

        print(
            "Artigos publicados: "
            f"{len(articles)}"
        )

        print(
            "Relacionamentos: "
            f"{total_relations}"
        )

        print(
            "Artigos sem relacionados: "
            f"{without_relations}"
        )

        print(
            f"Saída: {args.output}"
        )

        print()

        print(
            "RESULTADO: "
            "RELACIONADOS ATUALIZADOS"
        )

        print(
            "RELACIONADOS=0"
        )

        return 0

    except RelatedError as exc:

        print(
            f"ERRO: {exc}"
        )

        print(
            "RELACIONADOS=2"
        )

        return 2

    except Exception as exc:

        print(
            "ERRO ESTRUTURAL NÃO TRATADO: "
            f"{exc}"
        )

        print(
            "RELACIONADOS=2"
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
