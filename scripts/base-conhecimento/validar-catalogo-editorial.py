#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Validador do Catálogo Editorial da
Base de Conhecimento.

Contrato Editorial V1.
"""

from __future__ import annotations

import argparse
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unicodedata


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


DEFAULT_CATALOG = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
)

DEFAULT_ARTICLES_DIR = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)

DEFAULT_INDEX = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

DEFAULT_CATEGORIES = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

sys.path.insert(
    0,
    str(SCRIPT_DIR),
)

from taxonomia import (  # noqa: E402
    TaxonomyError,
    load_taxonomy,
    resolve_category,
)


CATALOG_VERSION = 1


TOP_LEVEL_FIELDS = {
    "version",
    "articles",
}


ARTICLE_FIELDS = {
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


VALID_STATUSES = {
    "planned",
    "draft",
    "review",
    "ready",
    "published",
}


VALID_PRIORITIES = {
    "high",
    "normal",
    "low",
}


ARTICLE_ID_RE = re.compile(
    r"^DD-KB-[0-9]{6}$"
)

SLUG_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)


class CatalogValidationError(
    Exception
):
    pass


def duplicate_key_guard(
    pairs,
):
    result = {}

    for key, value in pairs:

        if key in result:
            raise CatalogValidationError(
                "chave JSON duplicada: "
                f"{key!r}"
            )

        result[key] = value

    return result


def read_json(
    path: Path,
):
    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except FileNotFoundError as exc:
        raise CatalogValidationError(
            f"arquivo inexistente: {path}"
        ) from exc

    except UnicodeDecodeError as exc:
        raise CatalogValidationError(
            f"arquivo não é UTF-8 válido: {path}"
        ) from exc

    except OSError as exc:
        raise CatalogValidationError(
            f"não foi possível ler {path}: "
            f"{exc}"
        ) from exc

    try:
        return json.loads(
            text,
            object_pairs_hook=
                duplicate_key_guard,
        )

    except json.JSONDecodeError as exc:
        raise CatalogValidationError(
            f"JSON inválido em {path}: "
            f"linha {exc.lineno}, "
            f"coluna {exc.colno}: "
            f"{exc.msg}"
        ) from exc


def require_exact_fields(
    value,
    expected: set[str],
    label: str,
) -> None:

    if not isinstance(
        value,
        dict,
    ):
        raise CatalogValidationError(
            f"{label} deve ser objeto JSON."
        )

    actual = set(
        value.keys()
    )

    missing = sorted(
        expected - actual
    )

    extra = sorted(
        actual - expected
    )

    messages = []

    if missing:
        messages.append(
            "ausentes="
            + ", ".join(missing)
        )

    if extra:
        messages.append(
            "desconhecidos="
            + ", ".join(extra)
        )

    if messages:
        raise CatalogValidationError(
            f"{label}: campos inválidos: "
            + "; ".join(messages)
        )


def collapse_whitespace(
    value: str,
) -> str:

    return " ".join(
        value.split()
    )


def require_canonical_text(
    value,
    field: str,
    *,
    allow_empty: bool = False,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise CatalogValidationError(
            f"{field} deve ser string."
        )

    normalized = collapse_whitespace(
        value
    )

    if (
        not allow_empty
        and not normalized
    ):
        raise CatalogValidationError(
            f"{field} não pode ser vazio."
        )

    if (
        not allow_empty
        and value != normalized
    ):
        raise CatalogValidationError(
            f"{field} contém espaços "
            "não canônicos."
        )

    return value


def canonical_title(
    value: str,
) -> str:

    return collapse_whitespace(
        unicodedata.normalize(
            "NFKC",
            value,
        )
    ).casefold()


def parse_iso_date(
    value,
    field: str,
    *,
    nullable: bool,
):
    if value is None:

        if nullable:
            return None

        raise CatalogValidationError(
            f"{field} não pode ser null."
        )

    if not isinstance(
        value,
        str,
    ):
        raise CatalogValidationError(
            f"{field} deve ser data "
            "ISO YYYY-MM-DD ou null."
        )

    try:
        parsed = date.fromisoformat(
            value
        )

    except ValueError as exc:
        raise CatalogValidationError(
            f"{field} possui data inválida: "
            f"{value!r}"
        ) from exc

    if parsed.isoformat() != value:
        raise CatalogValidationError(
            f"{field} deve usar "
            "YYYY-MM-DD canônico."
        )

    return parsed


class ArticleHeadParser(
    HTMLParser
):
    def __init__(
        self,
    ) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.in_title = False
        self.title_parts = []
        self.categories = []


    def handle_starttag(
        self,
        tag,
        attrs,
    ) -> None:

        tag = tag.lower()

        if tag == "title":
            self.in_title = True
            return

        if tag != "meta":
            return

        attributes = {
            str(key).lower():
                value
            for key, value
            in attrs
        }

        name = attributes.get(
            "name"
        )

        content = attributes.get(
            "content"
        )

        if (
            isinstance(name, str)
            and
            name.lower()
            == "kb-category"
            and
            isinstance(
                content,
                str,
            )
        ):
            self.categories.append(
                content
            )


    def handle_endtag(
        self,
        tag,
    ) -> None:

        if tag.lower() == "title":
            self.in_title = False


    def handle_data(
        self,
        data,
    ) -> None:

        if self.in_title:
            self.title_parts.append(
                data
            )


def read_article_identity(
    path: Path,
):

    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except FileNotFoundError as exc:
        raise CatalogValidationError(
            f"artigo publicado ausente: "
            f"{path}"
        ) from exc

    except UnicodeDecodeError as exc:
        raise CatalogValidationError(
            f"artigo não é UTF-8 válido: "
            f"{path}"
        ) from exc

    parser = ArticleHeadParser()

    parser.feed(
        text
    )

    title = collapse_whitespace(
        "".join(
            parser.title_parts
        )
    )

    if not title:
        raise CatalogValidationError(
            f"title HTML ausente em {path}"
        )

    if len(
        parser.categories
    ) != 1:
        raise CatalogValidationError(
            "artigo deve possuir exatamente "
            "um meta kb-category: "
            f"{path}"
        )

    category_id = (
        parser.categories[0]
    )

    return {
        "title": title,
        "category_id": category_id,
    }


def load_index_entries(
    path: Path,
):

    data = read_json(
        path
    )

    if not isinstance(
        data,
        list,
    ):
        raise CatalogValidationError(
            "indice.json deve possuir "
            "array JSON na raiz."
        )

    entries = []

    for number, item in enumerate(
        data,
        1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            raise CatalogValidationError(
                "entrada inválida no índice: "
                f"posição {number}"
            )

        entries.append(
            item
        )

    return entries


def validate_published(
    article,
    *,
    articles_dir: Path,
    index_entries,
) -> None:

    slug = article["slug"]

    article_path = (
        articles_dir
        / f"{slug}.html"
    )

    identity = (
        read_article_identity(
            article_path
        )
    )

    if (
        identity["title"]
        != article["title"]
    ):
        raise CatalogValidationError(
            f"{article['id']}: title diverge "
            "entre catálogo e HTML."
        )

    if (
        identity["category_id"]
        != article["category_id"]
    ):
        raise CatalogValidationError(
            f"{article['id']}: category_id "
            "diverge entre catálogo e HTML."
        )

    matches = [
        item
        for item in index_entries
        if item.get("slug") == slug
    ]

    if len(matches) != 1:
        raise CatalogValidationError(
            f"{article['id']}: artigo published "
            "deve existir exatamente uma vez "
            "no indice.json."
        )

    entry = matches[0]

    expected_url = (
        f"artigos/{slug}.html"
    )

    checks = (
        (
            "title",
            article["title"],
        ),
        (
            "category_id",
            article["category_id"],
        ),
        (
            "url",
            expected_url,
        ),
    )

    for field, expected in checks:

        if (
            entry.get(field)
            != expected
        ):
            raise CatalogValidationError(
                f"{article['id']}: "
                f"{field} diverge entre "
                "catálogo e indice.json."
            )


def validate_not_published(
    article,
    *,
    articles_dir: Path,
    index_entries,
) -> None:

    slug = article["slug"]

    article_path = (
        articles_dir
        / f"{slug}.html"
    )

    if article_path.exists():
        raise CatalogValidationError(
            f"{article['id']}: status "
            f"{article['status']!r}, mas "
            "HTML público existe."
        )

    matches = [
        item
        for item in index_entries
        if item.get("slug") == slug
    ]

    if matches:
        raise CatalogValidationError(
            f"{article['id']}: status "
            f"{article['status']!r}, mas "
            "artigo existe no indice.json."
        )


def validate_article_record(
    article,
    number: int,
    *,
    taxonomy,
    articles_dir: Path,
    index_entries,
):
    label = (
        f"articles[{number}]"
    )

    require_exact_fields(
        article,
        ARTICLE_FIELDS,
        label,
    )

    article_id = (
        require_canonical_text(
            article["id"],
            f"{label}.id",
        )
    )

    if not ARTICLE_ID_RE.fullmatch(
        article_id
    ):
        raise CatalogValidationError(
            f"{label}.id inválido: "
            f"{article_id!r}"
        )

    title = (
        require_canonical_text(
            article["title"],
            f"{label}.title",
        )
    )

    slug = (
        require_canonical_text(
            article["slug"],
            f"{label}.slug",
        )
    )

    if not SLUG_RE.fullmatch(
        slug
    ):
        raise CatalogValidationError(
            f"{label}.slug inválido: "
            f"{slug!r}"
        )

    category_id = (
        require_canonical_text(
            article["category_id"],
            f"{label}.category_id",
        )
    )

    try:
        resolve_category(
            taxonomy,
            category_id,
        )

    except TaxonomyError as exc:
        raise CatalogValidationError(
            f"{article_id}: category_id "
            f"inválido: {category_id!r}"
        ) from exc

    status = (
        require_canonical_text(
            article["status"],
            f"{label}.status",
        )
    )

    if status not in VALID_STATUSES:
        raise CatalogValidationError(
            f"{article_id}: status "
            f"desconhecido: {status!r}"
        )

    priority = (
        require_canonical_text(
            article["priority"],
            f"{label}.priority",
        )
    )

    if priority not in VALID_PRIORITIES:
        raise CatalogValidationError(
            f"{article_id}: prioridade "
            f"desconhecida: {priority!r}"
        )

    parse_iso_date(
        article["created_on"],
        f"{label}.created_on",
        nullable=False,
    )

    published_on = (
        parse_iso_date(
            article["published_on"],
            f"{label}.published_on",
            nullable=True,
        )
    )

    parse_iso_date(
        article["review_due"],
        f"{label}.review_due",
        nullable=True,
    )

    if (
        status == "published"
        and published_on is None
    ):
        raise CatalogValidationError(
            f"{article_id}: published exige "
            "published_on."
        )

    if (
        status != "published"
        and published_on is not None
    ):
        raise CatalogValidationError(
            f"{article_id}: status "
            f"{status!r} exige "
            "published_on=null."
        )

    if not isinstance(
        article["notes"],
        str,
    ):
        raise CatalogValidationError(
            f"{label}.notes deve ser string."
        )

    if status == "published":

        validate_published(
            article,
            articles_dir=
                articles_dir,
            index_entries=
                index_entries,
        )

    else:

        validate_not_published(
            article,
            articles_dir=
                articles_dir,
            index_entries=
                index_entries,
        )

    return {
        "id": article_id,
        "title": title,
        "slug": slug,
        "status": status,
    }


def validate_catalog(
    *,
    catalog_path: Path,
    articles_dir: Path,
    index_path: Path,
    categories_path: Path,
):
    data = read_json(
        catalog_path
    )

    require_exact_fields(
        data,
        TOP_LEVEL_FIELDS,
        "catálogo",
    )

    version = data["version"]

    if (
        type(version) is not int
        or version != CATALOG_VERSION
    ):
        raise CatalogValidationError(
            "version inválida: "
            f"esperado={CATALOG_VERSION}; "
            f"encontrado={version!r}"
        )

    articles = data["articles"]

    if not isinstance(
        articles,
        list,
    ):
        raise CatalogValidationError(
            "articles deve ser array JSON."
        )

    try:
        taxonomy = load_taxonomy(
            categories_path
        )

    except TaxonomyError as exc:
        raise CatalogValidationError(
            "taxonomia inválida: "
            f"{exc}"
        ) from exc

    index_entries = (
        load_index_entries(
            index_path
        )
    )

    validated = []

    ids = set()
    slugs = set()
    titles = set()

    for number, article in enumerate(
        articles,
        1,
    ):

        result = (
            validate_article_record(
                article,
                number,
                taxonomy=taxonomy,
                articles_dir=
                    articles_dir,
                index_entries=
                    index_entries,
            )
        )

        article_id = result["id"]

        if article_id in ids:
            raise CatalogValidationError(
                f"id duplicado: {article_id}"
            )

        ids.add(
            article_id
        )

        slug = result["slug"]

        if slug in slugs:
            raise CatalogValidationError(
                f"slug duplicado: {slug}"
            )

        slugs.add(
            slug
        )

        title_key = canonical_title(
            result["title"]
        )

        if title_key in titles:
            raise CatalogValidationError(
                "title duplicado "
                "canonicamente: "
                f"{result['title']!r}"
            )

        titles.add(
            title_key
        )

        validated.append(
            result
        )

    published_slugs = {
        item["slug"]
        for item in validated
        if item["status"] == "published"
    }

    public_html_slugs = {
        path.stem
        for path in articles_dir.glob(
            "*.html"
        )
        if not path.name.startswith("_")
    }

    if (
        public_html_slugs
        != published_slugs
    ):
        not_cataloged = sorted(
            public_html_slugs
            - published_slugs
        )

        missing_html = sorted(
            published_slugs
            - public_html_slugs
        )

        details = []

        if not_cataloged:
            details.append(
                "HTML público sem catálogo="
                + ", ".join(
                    not_cataloged
                )
            )

        if missing_html:
            details.append(
                "published sem HTML="
                + ", ".join(
                    missing_html
                )
            )

        raise CatalogValidationError(
            "catálogo e artigos públicos "
            "divergem: "
            + "; ".join(
                details
            )
        )

    index_slugs = []

    for number, entry in enumerate(
        index_entries,
        1,
    ):
        slug = entry.get(
            "slug"
        )

        if (
            not isinstance(
                slug,
                str,
            )
            or
            not SLUG_RE.fullmatch(
                slug
            )
        ):
            raise CatalogValidationError(
                "indice.json contém slug "
                "inválido na posição "
                f"{number}: {slug!r}"
            )

        index_slugs.append(
            slug
        )

    if (
        len(index_slugs)
        != len(set(index_slugs))
    ):
        raise CatalogValidationError(
            "indice.json contém "
            "slug duplicado."
        )

    indexed_slugs = set(
        index_slugs
    )

    if indexed_slugs != published_slugs:
        not_cataloged = sorted(
            indexed_slugs
            - published_slugs
        )

        missing_index = sorted(
            published_slugs
            - indexed_slugs
        )

        details = []

        if not_cataloged:
            details.append(
                "índice sem catálogo="
                + ", ".join(
                    not_cataloged
                )
            )

        if missing_index:
            details.append(
                "published sem índice="
                + ", ".join(
                    missing_index
                )
            )

        raise CatalogValidationError(
            "catálogo e indice.json "
            "divergem: "
            + "; ".join(
                details
            )
        )

    ordered_ids = [
        item["id"]
        for item in validated
    ]

    if ordered_ids != sorted(
        ordered_ids
    ):
        raise CatalogValidationError(
            "articles deve estar ordenado "
            "por id em ordem crescente."
        )

    return validated


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Valida o Catálogo Editorial V1 "
            "da Base de Conhecimento DATADARK."
        )
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help=(
            "Arquivo catalogo.json."
        ),
    )

    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=DEFAULT_ARTICLES_DIR,
        help=(
            "Diretório dos artigos públicos."
        ),
    )

    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
        help=(
            "Arquivo indice.json."
        ),
    )

    parser.add_argument(
        "--categories",
        type=Path,
        default=DEFAULT_CATEGORIES,
        help=(
            "Arquivo categorias.json."
        ),
    )

    return parser.parse_args()


def main() -> int:

    args = parse_args()

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Validador do Catálogo Editorial V1.0"
    )

    print(
        "=========================================="
    )

    print(
        f"Catálogo: {args.catalog.resolve()}"
    )

    print(
        f"Artigos:  {args.articles_dir.resolve()}"
    )

    print(
        f"Índice:   {args.index.resolve()}"
    )

    print(
        f"Taxonomia:{args.categories.resolve()}"
    )

    print()

    try:
        articles = validate_catalog(
            catalog_path=args.catalog,
            articles_dir=
                args.articles_dir,
            index_path=args.index,
            categories_path=
                args.categories,
        )

    except CatalogValidationError as exc:

        print(
            f"[ERRO] {exc}"
        )

        print()

        print(
            "RESULTADO: CATÁLOGO EDITORIAL INVÁLIDO"
        )

        print(
            "CATALOGO_EDITORIAL=1"
        )

        return 1

    published = sum(
        item["status"] == "published"
        for item in articles
    )

    for item in articles:

        print(
            f"[OK] {item['id']} | "
            f"{item['status']} | "
            f"{item['slug']}"
        )

    print(
        "------------------------------------------"
    )

    print(
        f"Artigos no catálogo: {len(articles)}"
    )

    print(
        f"Artigos publicados: {published}"
    )

    print(
        "Erros: 0"
    )

    print()

    print(
        "RESULTADO: CATÁLOGO EDITORIAL OK"
    )

    print(
        "CATALOGO_EDITORIAL=0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
