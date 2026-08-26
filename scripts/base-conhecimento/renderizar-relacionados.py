#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Renderizador Estático de Artigos Relacionados V1.

ETAPA 8.6.3C

Responsabilidades:
- consumir indice.json;
- consumir relacionados.json V1;
- validar o estado editorial oficial;
- renderizar relações já calculadas;
- nunca recalcular ranking;
- produzir HTML estático rastreável;
- suportar migração controlada do layout legado;
- operar inicialmente apenas em diretório de saída;
- oferecer --check sem escrita.

Nesta fase não existe escrita in-place nos artigos oficiais.
"""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import stat
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

REPOSITORY_ROOT = (
    SCRIPT_DIR
    .parents[1]
)

DEFAULT_ARTICLES_DIR = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "artigos"
)

DEFAULT_TEMPLATE_PATH = (
    SCRIPT_DIR
    / "templates"
    / "artigo-v1.html"
)

DEFAULT_INDEX_PATH = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

DEFAULT_RELATED_PATH = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "relacionados.json"
)

DEFAULT_CATEGORIES_PATH = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

DEFAULT_CATALOG_PATH = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
)

CATALOG_VALIDATOR_PATH = (
    SCRIPT_DIR
    / "validar-catalogo-editorial.py"
)


VERSION = 1
MAX_RELATED = 3


SLUG_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)


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


RELATED_ROOT_FIELDS = {
    "version",
    "articles",
}


HTML_START = (
    "        <!-- DATADARK:RELATED:START -->"
)

HTML_END = (
    "        <!-- DATADARK:RELATED:END -->"
)

CSS_START = (
    "    /* DATADARK:RELATED:CSS:START */"
)

CSS_END = (
    "    /* DATADARK:RELATED:CSS:END */"
)


LEGACY_HTML_ANCHOR = (
    '        <div class="article-actions">\n'
)

STYLE_END = (
    "  </style>"
)


class RenderRelatedError(RuntimeError):
    """Erro estrutural que bloqueia a renderização."""


def without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:

    result: dict[str, Any] = {}

    for key, value in pairs:

        if key in result:
            raise RenderRelatedError(
                f"chave JSON duplicada: {key}"
            )

        result[key] = value

    return result


def read_json(
    path: Path,
) -> Any:

    try:

        text = path.read_text(
            encoding="utf-8"
        )

    except OSError as exc:

        raise RenderRelatedError(
            f"falha ao ler {path}: {exc}"
        ) from exc

    try:

        return json.loads(
            text,
            object_pairs_hook=
                without_duplicate_keys,
        )

    except json.JSONDecodeError as exc:

        raise RenderRelatedError(
            f"JSON inválido em {path}: {exc}"
        ) from exc


def require_text(
    value: Any,
    field: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise RenderRelatedError(
            f"{field} deve ser string"
        )

    normalized = (
        " ".join(
            value.split()
        )
    )

    if not normalized:
        raise RenderRelatedError(
            f"{field} não pode ser vazio"
        )

    return normalized


def validate_editorial_state(
    *,
    catalog_path: Path,
    articles_dir: Path,
    index_path: Path,
    categories_path: Path,
) -> None:

    if not CATALOG_VALIDATOR_PATH.is_file():
        raise RenderRelatedError(
            "validador editorial oficial ausente"
        )

    environment = os.environ.copy()

    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(
                CATALOG_VALIDATOR_PATH
            ),
            "--catalog",
            str(
                catalog_path
            ),
            "--articles-dir",
            str(
                articles_dir
            ),
            "--index",
            str(
                index_path
            ),
            "--categories",
            str(
                categories_path
            ),
        ],
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:

        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "sem detalhes"
        )

        raise RenderRelatedError(
            "validação editorial oficial "
            f"falhou: {details}"
        )


def load_index(
    path: Path,
) -> dict[str, dict[str, Any]]:

    data = read_json(
        path
    )

    if not isinstance(
        data,
        list,
    ):
        raise RenderRelatedError(
            "indice.json deve ser uma lista"
        )

    result: dict[
        str,
        dict[str, Any],
    ] = {}

    for position, record in enumerate(
        data
    ):

        prefix = (
            f"indice[{position}]"
        )

        if not isinstance(
            record,
            dict,
        ):
            raise RenderRelatedError(
                f"{prefix} deve ser objeto"
            )

        if set(
            record
        ) != INDEX_FIELDS:

            missing = (
                INDEX_FIELDS
                - set(record)
            )

            extra = (
                set(record)
                - INDEX_FIELDS
            )

            raise RenderRelatedError(
                f"{prefix}: schema inválido; "
                f"ausentes={sorted(missing)}; "
                f"extras={sorted(extra)}"
            )

        slug = require_text(
            record["slug"],
            f"{prefix}.slug",
        )

        if not SLUG_RE.fullmatch(
            slug
        ):
            raise RenderRelatedError(
                f"{prefix}.slug inválido: {slug}"
            )

        if slug in result:
            raise RenderRelatedError(
                f"slug duplicado no índice: {slug}"
            )

        require_text(
            record["title"],
            f"{prefix}.title",
        )

        require_text(
            record["category_id"],
            f"{prefix}.category_id",
        )

        require_text(
            record["category"],
            f"{prefix}.category",
        )

        result[slug] = record

    if not result:
        raise RenderRelatedError(
            "índice não possui artigos"
        )

    return result


def load_relations(
    path: Path,
    index: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, list[str]]:

    data = read_json(
        path
    )

    if not isinstance(
        data,
        dict,
    ):
        raise RenderRelatedError(
            "relacionados.json deve ser objeto"
        )

    if set(
        data
    ) != RELATED_ROOT_FIELDS:
        raise RenderRelatedError(
            "schema raiz de relacionados.json "
            "inválido"
        )

    if data["version"] != VERSION:
        raise RenderRelatedError(
            "version de relacionados.json "
            f"deve ser {VERSION}"
        )

    articles = data[
        "articles"
    ]

    if not isinstance(
        articles,
        dict,
    ):
        raise RenderRelatedError(
            "articles deve ser objeto"
        )

    if set(
        articles
    ) != set(
        index
    ):
        missing = (
            set(index)
            - set(articles)
        )

        extra = (
            set(articles)
            - set(index)
        )

        raise RenderRelatedError(
            "cobertura de relacionados.json "
            "diverge do índice; "
            f"ausentes={sorted(missing)}; "
            f"extras={sorted(extra)}"
        )

    result: dict[
        str,
        list[str],
    ] = {}

    for source in sorted(
        articles
    ):

        targets = articles[
            source
        ]

        if not isinstance(
            targets,
            list,
        ):
            raise RenderRelatedError(
                f"{source}: destinos devem "
                "ser lista"
            )

        if len(
            targets
        ) > MAX_RELATED:
            raise RenderRelatedError(
                f"{source}: mais de "
                f"{MAX_RELATED} relacionados"
            )

        seen: set[str] = set()
        normalized: list[str] = []

        for target in targets:

            if not isinstance(
                target,
                str,
            ):
                raise RenderRelatedError(
                    f"{source}: destino "
                    "não é string"
                )

            if not SLUG_RE.fullmatch(
                target
            ):
                raise RenderRelatedError(
                    f"{source}: slug destino "
                    f"inválido: {target}"
                )

            if target == source:
                raise RenderRelatedError(
                    f"{source}: self-reference"
                )

            if target not in index:
                raise RenderRelatedError(
                    f"{source}: destino ausente "
                    f"do índice: {target}"
                )

            if target in seen:
                raise RenderRelatedError(
                    f"{source}: destino "
                    f"duplicado: {target}"
                )

            seen.add(
                target
            )

            normalized.append(
                target
            )

        result[source] = (
            normalized
        )

    return result


def read_template_contract(
    path: Path,
) -> str:

    try:

        text = path.read_text(
            encoding="utf-8"
        )

    except OSError as exc:

        raise RenderRelatedError(
            f"falha ao ler template: {exc}"
        ) from exc

    for marker in (
        HTML_START,
        HTML_END,
        CSS_START,
        CSS_END,
    ):

        count = text.count(
            marker
        )

        if count != 1:
            raise RenderRelatedError(
                f"template: {marker!r}: "
                f"esperado=1; encontrado={count}"
            )

    html_start = text.index(
        HTML_START
    )

    html_end = text.index(
        HTML_END
    )

    if html_start >= html_end:
        raise RenderRelatedError(
            "template: marcadores HTML "
            "fora de ordem"
        )

    between = text[
        html_start
        + len(HTML_START):
        html_end
    ]

    if between.strip():
        raise RenderRelatedError(
            "template: região RELATED "
            "deve permanecer vazia"
        )

    css_start = text.index(
        CSS_START
    )

    css_end = text.index(
        CSS_END
    )

    if css_start >= css_end:
        raise RenderRelatedError(
            "template: marcadores CSS "
            "fora de ordem"
        )

    css_body = text[
        css_start
        + len(CSS_START):
        css_end
    ]

    if not css_body.strip():
        raise RenderRelatedError(
            "template: CSS RELATED vazio"
        )

    return text


def template_css_region(
    template: str,
) -> str:

    start = template.index(
        CSS_START
    )

    end = (
        template.index(
            CSS_END,
            start,
        )
        + len(CSS_END)
    )

    return template[
        start:end
    ]


def visible_relation_section(
    targets: list[str],
    index: dict[
        str,
        dict[str, Any],
    ],
) -> str:

    if not targets:
        return ""

    lines = [
        '        <section',
        '          class="article-section kb-related"',
        '          aria-labelledby="kb-related-title">',
        '',
        '          <h2 id="kb-related-title">',
        '            Artigos relacionados',
        '          </h2>',
        '',
        '          <ul class="kb-related-list">',
    ]

    for target in targets:

        record = index[
            target
        ]

        title = html.escape(
            require_text(
                record["title"],
                f"{target}.title",
            ),
            quote=False,
        )

        category = html.escape(
            require_text(
                record["category"],
                f"{target}.category",
            ),
            quote=False,
        )

        url = (
            "/base-conhecimento/artigos/"
            f"{target}.html"
        )

        lines.extend(
            [
                '',
                '            <li class="kb-related-item">',
                '              <a',
                '                class="kb-related-link"',
                f'                href="{url}">',
                '',
                '                <span class="kb-related-category">',
                f'                  {category}',
                '                </span>',
                '',
                '                <span class="kb-related-title">',
                f'                  {title}',
                '                </span>',
                '',
                '              </a>',
                '            </li>',
            ]
        )

    lines.extend(
        [
            '',
            '          </ul>',
            '',
            '        </section>',
        ]
    )

    return "\n".join(
        lines
    )


def html_region(
    targets: list[str],
    index: dict[
        str,
        dict[str, Any],
    ],
) -> str:

    section = (
        visible_relation_section(
            targets,
            index,
        )
    )

    if not section:

        return (
            HTML_START
            + "\n"
            + HTML_END
        )

    return (
        HTML_START
        + "\n"
        + section
        + "\n"
        + HTML_END
    )


def replace_or_migrate_css(
    source: str,
    css_region: str,
    slug: str,
) -> str:

    start_count = source.count(
        CSS_START
    )

    end_count = source.count(
        CSS_END
    )

    if (
        start_count == 0
        and end_count == 0
    ):

        if source.count(
            STYLE_END
        ) != 1:
            raise RenderRelatedError(
                f"{slug}: </style> "
                "não é único"
            )

        return source.replace(
            STYLE_END,
            (
                css_region
                + "\n\n"
                + STYLE_END
            ),
            1,
        )

    if (
        start_count != 1
        or end_count != 1
    ):
        raise RenderRelatedError(
            f"{slug}: marcadores CSS "
            "inconsistentes"
        )

    start = source.index(
        CSS_START
    )

    end = (
        source.index(
            CSS_END,
            start,
        )
        + len(CSS_END)
    )

    if start >= end:
        raise RenderRelatedError(
            f"{slug}: marcadores CSS "
            "fora de ordem"
        )

    outside = (
        source[:start]
        + source[end:]
    )

    if ".kb-related" in outside:
        raise RenderRelatedError(
            f"{slug}: CSS RELATED "
            "fora da região controlada"
        )

    return (
        source[:start]
        + css_region
        + source[end:]
    )


def replace_or_migrate_html(
    source: str,
    region: str,
    slug: str,
) -> str:

    start_count = source.count(
        HTML_START
    )

    end_count = source.count(
        HTML_END
    )

    if (
        start_count == 0
        and end_count == 0
    ):

        unknown_html_signatures = (
            'class="article-section kb-related"',
            'class="kb-related-list"',
            'class="kb-related-item"',
            'class="kb-related-link"',
        )

        if any(
            signature in source
            for signature
            in unknown_html_signatures
        ):
            raise RenderRelatedError(
                f"{slug}: estrutura RELATED "
                "legada desconhecida"
            )

        if source.count(
            LEGACY_HTML_ANCHOR
        ) != 1:
            raise RenderRelatedError(
                f"{slug}: anchor article-actions "
                "não é único"
            )

        return source.replace(
            LEGACY_HTML_ANCHOR,
            (
                region
                + "\n\n\n"
                + LEGACY_HTML_ANCHOR
            ),
            1,
        )

    if (
        start_count != 1
        or end_count != 1
    ):
        raise RenderRelatedError(
            f"{slug}: marcadores HTML "
            "inconsistentes"
        )

    start = source.index(
        HTML_START
    )

    end = (
        source.index(
            HTML_END,
            start,
        )
        + len(HTML_END)
    )

    if start >= end:
        raise RenderRelatedError(
            f"{slug}: marcadores HTML "
            "fora de ordem"
        )

    outside = (
        source[:start]
        + source[end:]
    )

    controlled_html_signatures = (
        'class="article-section kb-related"',
        'class="kb-related-list"',
        'class="kb-related-item"',
        'class="kb-related-link"',
        'id="kb-related-title"',
    )

    if any(
        signature in outside
        for signature
        in controlled_html_signatures
    ):
        raise RenderRelatedError(
            f"{slug}: bloco RELATED "
            "fora da região controlada"
        )

    return (
        source[:start]
        + region
        + source[end:]
    )


def render_article(
    *,
    source: str,
    slug: str,
    targets: list[str],
    index: dict[
        str,
        dict[str, Any],
    ],
    css_region: str,
) -> str:

    rendered = (
        replace_or_migrate_css(
            source,
            css_region,
            slug,
        )
    )

    region = html_region(
        targets,
        index,
    )

    rendered = (
        replace_or_migrate_html(
            rendered,
            region,
            slug,
        )
    )

    if rendered.count(
        HTML_START
    ) != 1:
        raise RenderRelatedError(
            f"{slug}: HTML_START inválido"
        )

    if rendered.count(
        HTML_END
    ) != 1:
        raise RenderRelatedError(
            f"{slug}: HTML_END inválido"
        )

    if rendered.count(
        CSS_START
    ) != 1:
        raise RenderRelatedError(
            f"{slug}: CSS_START inválido"
        )

    if rendered.count(
        CSS_END
    ) != 1:
        raise RenderRelatedError(
            f"{slug}: CSS_END inválido"
        )

    expected_visible = (
        1
        if targets
        else 0
    )

    actual_visible = rendered.count(
        'class="article-section kb-related"'
    )

    if actual_visible != expected_visible:
        raise RenderRelatedError(
            f"{slug}: quantidade visual "
            "RELATED divergente"
        )

    if targets:

        if rendered.count(
            'id="kb-related-title"'
        ) != 1:
            raise RenderRelatedError(
                f"{slug}: heading RELATED "
                "inválido"
            )

        for target in targets:

            expected_url = (
                "/base-conhecimento/artigos/"
                f"{target}.html"
            )

            if rendered.count(
                expected_url
            ) != 1:
                raise RenderRelatedError(
                    f"{slug}: URL RELATED "
                    f"divergente: {target}"
                )

    return rendered


def load_source_articles(
    articles_dir: Path,
    index: dict[
        str,
        dict[str, Any],
    ],
) -> dict[str, tuple[Path, bytes, int]]:

    if not articles_dir.is_dir():
        raise RenderRelatedError(
            f"diretório de artigos ausente: "
            f"{articles_dir}"
        )

    public = {
        path.stem: path
        for path in (
            articles_dir.glob(
                "*.html"
            )
        )
        if not path.name.startswith(
            "_"
        )
    }

    if set(public) != set(index):

        missing = (
            set(index)
            - set(public)
        )

        extra = (
            set(public)
            - set(index)
        )

        raise RenderRelatedError(
            "HTMLs públicos divergem do índice; "
            f"ausentes={sorted(missing)}; "
            f"extras={sorted(extra)}"
        )

    result: dict[
        str,
        tuple[
            Path,
            bytes,
            int,
        ],
    ] = {}

    for slug in sorted(
        index
    ):

        path = public[
            slug
        ]

        try:

            content = path.read_bytes()

            mode = stat.S_IMODE(
                path.stat().st_mode
            )

        except OSError as exc:

            raise RenderRelatedError(
                f"{slug}: falha de leitura: {exc}"
            ) from exc

        try:

            content.decode(
                "utf-8"
            )

        except UnicodeDecodeError as exc:

            raise RenderRelatedError(
                f"{slug}: HTML não é UTF-8"
            ) from exc

        result[slug] = (
            path,
            content,
            mode,
        )

    return result


def build_rendered_articles(
    *,
    source_articles: dict[
        str,
        tuple[
            Path,
            bytes,
            int,
        ],
    ],
    relations: dict[
        str,
        list[str],
    ],
    index: dict[
        str,
        dict[str, Any],
    ],
    template: str,
) -> dict[
    str,
    tuple[
        bytes,
        int,
    ],
]:

    css_region = (
        template_css_region(
            template
        )
    )

    result: dict[
        str,
        tuple[
            bytes,
            int,
        ],
    ] = {}

    for slug in sorted(
        index
    ):

        _, source_bytes, mode = (
            source_articles[
                slug
            ]
        )

        source_text = (
            source_bytes.decode(
                "utf-8"
            )
        )

        rendered = render_article(
            source=source_text,
            slug=slug,
            targets=relations[slug],
            index=index,
            css_region=css_region,
        )

        result[slug] = (
            rendered.encode(
                "utf-8"
            ),
            mode,
        )

    return result


def fsync_directory(
    path: Path,
) -> None:

    descriptor = os.open(
        path,
        os.O_RDONLY,
    )

    try:

        os.fsync(
            descriptor
        )

    finally:

        os.close(
            descriptor
        )


def write_output_atomic(
    *,
    output_dir: Path,
    rendered: dict[
        str,
        tuple[
            bytes,
            int,
        ],
    ],
) -> None:

    parent = (
        output_dir
        .parent
    )

    if not parent.is_dir():
        raise RenderRelatedError(
            f"diretório pai da saída "
            f"não existe: {parent}"
        )

    if output_dir.exists():
        raise RenderRelatedError(
            f"saída já existe: {output_dir}"
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=(
                f".{output_dir.name}."
                "related-staging."
            ),
            dir=parent,
        )
    )

    promoted = False

    try:

        for slug in sorted(
            rendered
        ):

            content, mode = (
                rendered[
                    slug
                ]
            )

            target = (
                staging
                / f"{slug}.html"
            )

            with target.open(
                "wb"
            ) as handle:

                handle.write(
                    content
                )

                handle.flush()

                os.fsync(
                    handle.fileno()
                )

            os.chmod(
                target,
                mode,
            )

        fsync_directory(
            staging
        )

        os.replace(
            staging,
            output_dir,
        )

        promoted = True

        fsync_directory(
            parent
        )

    finally:

        if (
            not promoted
            and staging.exists()
        ):
            shutil.rmtree(
                staging,
                ignore_errors=True,
            )


def check_rendered_state(
    *,
    source_articles: dict[
        str,
        tuple[
            Path,
            bytes,
            int,
        ],
    ],
    rendered: dict[
        str,
        tuple[
            bytes,
            int,
        ],
    ],
) -> list[str]:

    divergent: list[str] = []

    for slug in sorted(
        rendered
    ):

        source_bytes = (
            source_articles[
                slug
            ][1]
        )

        desired_bytes = (
            rendered[
                slug
            ][0]
        )

        if (
            source_bytes
            != desired_bytes
        ):
            divergent.append(
                slug
            )

    return divergent


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Renderiza Artigos Relacionados V1 "
            "sem recalcular ranking. "
            "Na ETAPA 8.6.3C não existe "
            "escrita in-place."
        )
    )

    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=
            DEFAULT_ARTICLES_DIR,
    )

    parser.add_argument(
        "--template",
        type=Path,
        default=
            DEFAULT_TEMPLATE_PATH,
    )

    parser.add_argument(
        "--index",
        type=Path,
        default=
            DEFAULT_INDEX_PATH,
    )

    parser.add_argument(
        "--related",
        type=Path,
        default=
            DEFAULT_RELATED_PATH,
    )

    parser.add_argument(
        "--categories",
        type=Path,
        default=
            DEFAULT_CATEGORIES_PATH,
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=
            DEFAULT_CATALOG_PATH,
    )

    mode = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Cria um novo diretório contendo "
            "os HTMLs renderizados. "
            "A saída não pode existir."
        ),
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Compara os artigos informados "
            "com a renderização esperada "
            "sem escrever arquivos."
        ),
    )

    return parser.parse_args()


def main() -> int:

    args = parse_args()

    try:

        validate_editorial_state(
            catalog_path=
                args.catalog,
            articles_dir=
                args.articles_dir,
            index_path=
                args.index,
            categories_path=
                args.categories,
        )

        index = load_index(
            args.index
        )

        relations = load_relations(
            args.related,
            index,
        )

        template = (
            read_template_contract(
                args.template
            )
        )

        source_articles = (
            load_source_articles(
                args.articles_dir,
                index,
            )
        )

        rendered = (
            build_rendered_articles(
                source_articles=
                    source_articles,
                relations=
                    relations,
                index=index,
                template=template,
            )
        )

        divergent = (
            check_rendered_state(
                source_articles=
                    source_articles,
                rendered=rendered,
            )
        )

        visible = sum(
            1
            for targets
            in relations.values()
            if targets
        )

        zero = (
            len(relations)
            - visible
        )

        edges = sum(
            len(targets)
            for targets
            in relations.values()
        )

        if args.check:

            if divergent:

                print(
                    "RESULTADO: RENDERIZAÇÃO "
                    "DIVERGENTE"
                )

                print(
                    "ARTIGOS_DIVERGENTES="
                    f"{len(divergent)}"
                )

                for slug in divergent:
                    print(
                        f"DIVERGENTE={slug}"
                    )

                print(
                    "RENDER_RELACIONADOS=1"
                )

                return 1

            print(
                "RESULTADO: RENDERIZAÇÃO OK"
            )

            print(
                "ARTIGOS_DIVERGENTES=0"
            )

            print(
                "RENDER_RELACIONADOS=0"
            )

            return 0

        output_dir = (
            args.output_dir
        )

        if output_dir is None:
            raise RenderRelatedError(
                "output-dir ausente"
            )

        write_output_atomic(
            output_dir=
                output_dir,
            rendered=
                rendered,
        )

        print(
            "Base de Conhecimento DATADARK"
        )

        print(
            "Renderizador Estático de "
            "Artigos Relacionados V1"
        )

        print(
            "=" * 46
        )

        print(
            f"Artigos: {len(rendered)}"
        )

        print(
            f"Blocos visíveis: {visible}"
        )

        print(
            f"Artigos sem bloco: {zero}"
        )

        print(
            f"Relações: {edges}"
        )

        print(
            f"Artigos alterados: "
            f"{len(divergent)}"
        )

        print(
            f"Saída: {output_dir}"
        )

        print()

        print(
            "RESULTADO: RENDERIZAÇÃO "
            "TEMPORÁRIA CONCLUÍDA"
        )

        print(
            "RENDER_RELACIONADOS=0"
        )

        return 0

    except RenderRelatedError as exc:

        print(
            "ERRO:",
            exc,
            file=sys.stderr,
        )

        print(
            "RENDER_RELACIONADOS=2"
        )

        return 2

    except Exception as exc:

        print(
            "ERRO OPERACIONAL:",
            exc,
            file=sys.stderr,
        )

        print(
            "RENDER_RELACIONADOS=2"
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
