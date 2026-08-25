#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 5 — Gerador Automático do Índice V1.0

Responsabilidades:
- descobrir artigos HTML;
- extrair metadados do <head>;
- gerar indice.json deterministicamente;
- suportar modo --check;
- gravar atomicamente;
- nunca modificar os artigos.

Saída:
0 = sucesso / índice atualizado no modo --check
1 = conteúdo inválido / índice desatualizado no modo --check
2 = erro operacional
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import sys
import tempfile
import unicodedata

from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


SLUG_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*\.html$"
)

HEAD_END_RE = re.compile(
    r"</head\s*>",
    re.IGNORECASE,
)

HEAD_START_RE = re.compile(
    r"<head\b",
    re.IGNORECASE,
)

HEAD_LIMIT_BYTES = (
    2 * 1024 * 1024
)

READ_CHUNK_BYTES = (
    64 * 1024
)

OPTIONAL_META = (
    "description",
    "keywords",
    "kb-aliases",
    "kb-category",
)


class ArticleContentError(
    Exception
):
    """Erro de conteúdo que bloqueia geração."""


class HeadMetadataParser(
    HTMLParser
):

    def __init__(self) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.head_seen = False

        self.inside_title = False

        self.title_parts: list[str] = []

        self.meta: dict[
            str,
            str
        ] = {}

        self.duplicate_meta: set[str] = set()


    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attr_map = {
            str(name).lower():
            "" if value is None
            else str(value)
            for name, value in attrs
        }


        if tag == "head":

            self.head_seen = True


        elif tag == "title":

            self.inside_title = True


        elif tag == "meta":

            name = (
                attr_map
                .get("name", "")
                .strip()
                .lower()
            )

            if not name:

                return


            content = (
                attr_map
                .get("content", "")
            )


            if name in self.meta:

                self.duplicate_meta.add(
                    name
                )

                return


            self.meta[name] = content


    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        if (
            tag.lower()
            == "title"
        ):

            self.inside_title = False


    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.inside_title:

            self.title_parts.append(
                data
            )


    @property
    def title(self) -> str:

        return collapse_whitespace(
            " ".join(
                self.title_parts
            )
        )


def collapse_whitespace(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def canonical_key(
    value: str,
) -> str:

    normalized = (
        unicodedata
        .normalize(
            "NFKD",
            collapse_whitespace(
                value
            ),
        )
    )

    normalized = "".join(
        char
        for char in normalized
        if not unicodedata
        .combining(char)
    )

    return (
        normalized
        .casefold()
        .strip()
    )


def parse_list_meta(
    value: str,
) -> list[str]:

    if not value:

        return []


    result: list[str] = []

    seen: set[str] = set()


    for raw_item in (
        str(value).split(",")
    ):

        item = collapse_whitespace(
            raw_item
        )

        if not item:

            continue


        key = canonical_key(
            item
        )

        if key in seen:

            continue


        seen.add(key)

        result.append(
            item
        )


    return result


def read_head(
    path: Path,
) -> str:

    decoder = (
        codecs
        .getincrementaldecoder(
            "utf-8-sig"
        )(
            errors="strict"
        )
    )

    pieces: list[str] = []

    total_bytes = 0

    reached_eof = False


    try:

        with path.open(
            "rb"
        ) as handle:

            while (
                total_bytes
                < HEAD_LIMIT_BYTES
            ):

                remaining = (
                    HEAD_LIMIT_BYTES
                    - total_bytes
                )

                chunk = handle.read(
                    min(
                        READ_CHUNK_BYTES,
                        remaining,
                    )
                )


                if not chunk:

                    reached_eof = True

                    break


                total_bytes += len(
                    chunk
                )


                try:

                    text = decoder.decode(
                        chunk,
                        final=False,
                    )

                except UnicodeDecodeError as exc:

                    raise ArticleContentError(
                        "cabeçalho não está "
                        "codificado em UTF-8"
                    ) from exc


                pieces.append(
                    text
                )


                head_text = "".join(
                    pieces
                )


                match = HEAD_END_RE.search(
                    head_text
                )


                if match:

                    return head_text[
                        :match.end()
                    ]


            if reached_eof:

                try:

                    tail = decoder.decode(
                        b"",
                        final=True,
                    )

                except UnicodeDecodeError as exc:

                    raise ArticleContentError(
                        "cabeçalho não está "
                        "codificado em UTF-8"
                    ) from exc


                if tail:

                    pieces.append(
                        tail
                    )


    except OSError as exc:

        raise ArticleContentError(
            "não foi possível ler o arquivo: "
            f"{exc}"
        ) from exc


    head_text = "".join(
        pieces
    )


    match = HEAD_END_RE.search(
        head_text
    )


    if match:

        return head_text[
            :match.end()
        ]


    if (
        total_bytes
        >= HEAD_LIMIT_BYTES
    ):

        raise ArticleContentError(
            "</head> não encontrado "
            "dentro do limite de 2 MiB"
        )


    raise ArticleContentError(
        "</head> ausente"
    )


def extract_article(
    path: Path,
) -> tuple[
    dict,
    list[str],
]:

    warnings: list[str] = []


    if not SLUG_RE.fullmatch(
        path.name
    ):

        raise ArticleContentError(
            "nome de arquivo inválido; "
            "esperado slug ASCII em "
            "minúsculas separado por hífens"
        )


    head = read_head(
        path
    )


    if not HEAD_START_RE.search(
        head
    ):

        raise ArticleContentError(
            "<head> ausente"
        )


    parser = HeadMetadataParser()


    try:

        parser.feed(
            head
        )

        parser.close()

    except Exception as exc:

        raise ArticleContentError(
            "falha ao interpretar "
            f"o <head>: {exc}"
        ) from exc


    if not parser.head_seen:

        raise ArticleContentError(
            "<head> não identificado "
            "pelo parser"
        )


    title = parser.title


    if not title:

        raise ArticleContentError(
            "<title> ausente ou vazio"
        )


    for name in sorted(
        parser.duplicate_meta
    ):

        warnings.append(
            "metadado duplicado "
            f"ignorado após a primeira "
            f"ocorrência: {name}"
        )


    description = (
        collapse_whitespace(
            parser.meta.get(
                "description",
                "",
            )
        )
    )

    category = (
        collapse_whitespace(
            parser.meta.get(
                "kb-category",
                "",
            )
        )
    )

    keywords = parse_list_meta(
        parser.meta.get(
            "keywords",
            "",
        )
    )

    aliases = parse_list_meta(
        parser.meta.get(
            "kb-aliases",
            "",
        )
    )


    for name in OPTIONAL_META:

        if not collapse_whitespace(
            parser.meta.get(
                name,
                "",
            )
        ):

            warnings.append(
                f"meta {name} ausente"
            )


    slug = path.stem

    url = (
        f"artigos/{path.name}"
    )


    entry = {
        "slug":
            slug,

        "title":
            title,

        "description":
            description,

        "url":
            url,

        "category":
            category,

        "keywords":
            keywords,

        "aliases":
            aliases,
    }


    return entry, warnings


def discover_articles(
    directory: Path,
) -> tuple[
    list[Path],
    list[Path],
]:

    all_html = sorted(
        (
            path
            for path
            in directory.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                    == ".html"
            )
        ),
        key=lambda path:
            path.name.casefold(),
    )


    ignored = [
        path
        for path in all_html
        if path.name.startswith(
            "_"
        )
    ]


    articles = [
        path
        for path in all_html
        if not path.name.startswith(
            "_"
        )
    ]


    return articles, ignored


def detect_case_collisions(
    articles: list[Path],
) -> list[list[Path]]:

    groups: dict[
        str,
        list[Path],
    ] = defaultdict(list)


    for article in articles:

        groups[
            article.name.casefold()
        ].append(
            article
        )


    return [
        paths
        for paths in groups.values()
        if len(paths) > 1
    ]


def serialize_index(
    entries: list[dict],
) -> str:

    return (
        json.dumps(
            entries,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def write_atomic(
    output: Path,
    content: str,
) -> None:

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    if output.exists():

        try:

            mode = (
                output.stat().st_mode
                & 0o777
            )

        except OSError as exc:

            raise OSError(
                "não foi possível obter "
                "permissões do índice atual"
            ) from exc

    else:

        mode = 0o644


    descriptor = None

    temporary_path = None


    try:

        descriptor, temp_name = (
            tempfile.mkstemp(
                prefix=(
                    f".{output.name}."
                ),
                suffix=".tmp",
                dir=str(
                    output.parent
                ),
            )
        )


        temporary_path = Path(
            temp_name
        )


        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:

            descriptor = None

            handle.write(
                content
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )


        os.chmod(
            temporary_path,
            mode,
        )


        os.replace(
            temporary_path,
            output,
        )


        temporary_path = None


    finally:

        if descriptor is not None:

            try:

                os.close(
                    descriptor
                )

            except OSError:

                pass


        if (
            temporary_path
            is not None
            and temporary_path.exists()
        ):

            try:

                temporary_path.unlink()

            except OSError:

                pass


def current_output_text(
    output: Path,
) -> str | None:

    if not output.exists():

        return None


    if not output.is_file():

        raise OSError(
            "o caminho de saída "
            "não é um arquivo"
        )


    try:

        return output.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        return None


def build_index(
    articles_dir: Path,
) -> tuple[
    list[dict],
    int,
    list[tuple[str, str]],
    list[tuple[str, str]],
]:

    articles, ignored = (
        discover_articles(
            articles_dir
        )
    )


    errors: list[
        tuple[str, str]
    ] = []

    warnings: list[
        tuple[str, str]
    ] = []

    entries: list[dict] = []


    collisions = (
        detect_case_collisions(
            articles
        )
    )


    for paths in collisions:

        names = ", ".join(
            path.name
            for path in paths
        )

        errors.append(
            (
                "DUPLICIDADE",
                "colisão de nome "
                f"case-insensitive: {names}",
            )
        )


    collision_names = {
        path
        for paths in collisions
        for path in paths
    }


    for article in articles:

        if article in collision_names:

            continue


        try:

            entry, article_warnings = (
                extract_article(
                    article
                )
            )

        except ArticleContentError as exc:

            errors.append(
                (
                    article.name,
                    str(exc),
                )
            )

            continue


        entries.append(
            entry
        )


        for message in (
            article_warnings
        ):

            warnings.append(
                (
                    article.name,
                    message,
                )
            )


    slug_groups: dict[
        str,
        list[str],
    ] = defaultdict(list)

    url_groups: dict[
        str,
        list[str],
    ] = defaultdict(list)

    title_groups: dict[
        str,
        list[str],
    ] = defaultdict(list)


    for entry in entries:

        slug_groups[
            entry["slug"].casefold()
        ].append(
            entry["slug"]
        )

        url_groups[
            entry["url"].casefold()
        ].append(
            entry["url"]
        )

        title_groups[
            canonical_key(
                entry["title"]
            )
        ].append(
            entry["title"]
        )


    for values in (
        slug_groups.values()
    ):

        if len(values) > 1:

            errors.append(
                (
                    "DUPLICIDADE",
                    "slug duplicado: "
                    + ", ".join(values),
                )
            )


    for values in (
        url_groups.values()
    ):

        if len(values) > 1:

            errors.append(
                (
                    "DUPLICIDADE",
                    "URL duplicada: "
                    + ", ".join(values),
                )
            )


    for values in (
        title_groups.values()
    ):

        if len(values) > 1:

            warnings.append(
                (
                    "TÍTULO",
                    "título duplicado: "
                    + " | ".join(values),
                )
            )


    entries.sort(
        key=lambda entry:
            entry["slug"].casefold()
    )


    return (
        entries,
        len(ignored),
        errors,
        warnings,
    )


def parse_args():

    repository_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )


    default_articles = (
        repository_root
        / "base-conhecimento"
        / "artigos"
    )


    default_output = (
        repository_root
        / "base-conhecimento"
        / "data"
        / "indice.json"
    )


    parser = argparse.ArgumentParser(
        description=(
            "Gera automaticamente "
            "o índice da Base de "
            "Conhecimento DATADARK."
        )
    )


    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=default_articles,
        help=(
            "Diretório contendo "
            "os artigos HTML."
        ),
    )


    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=(
            "Arquivo JSON de saída."
        ),
    )


    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Compara o índice esperado "
            "com o arquivo atual sem "
            "modificá-lo."
        ),
    )


    return parser.parse_args()


def print_report(
    articles_count: int,
    indexed_count: int,
    ignored_count: int,
    warnings: list[
        tuple[str, str]
    ],
) -> None:

    print(
        "Artigos encontrados: "
        f"{articles_count}"
    )

    print(
        "Artigos indexados: "
        f"{indexed_count}"
    )

    print(
        "Rascunhos ignorados: "
        f"{ignored_count}"
    )

    print(
        "Avisos: "
        f"{len(warnings)}"
    )


def main() -> int:

    args = parse_args()


    articles_dir = (
        args.articles_dir
        .expanduser()
        .resolve()
    )


    output = (
        args.output
        .expanduser()
        .resolve()
    )


    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Gerador de Índice V1.0"
    )

    print(
        "=" * 42
    )

    print(
        f"Artigos: {articles_dir}"
    )

    print(
        f"Índice:  {output}"
    )

    print()


    if not articles_dir.exists():

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            "Diretório de artigos "
            "não existe."
        )

        return 2


    if not articles_dir.is_dir():

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            "O caminho de artigos "
            "não é um diretório."
        )

        return 2


    try:

        articles, ignored = (
            discover_articles(
                articles_dir
            )
        )


        (
            entries,
            ignored_count,
            errors,
            warnings,
        ) = build_index(
            articles_dir
        )


    except OSError as exc:

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            str(exc)
        )

        return 2


    if errors:

        for source, message in errors:

            print(
                f"[ERRO] {source}"
            )

            print(
                f"  - {message}"
            )


        if warnings:

            print()

            for source, message in warnings:

                print(
                    f"[AVISO] {source}"
                )

                print(
                    f"  - {message}"
                )


        print()

        print_report(
            len(articles),
            len(entries),
            ignored_count,
            warnings,
        )

        print()

        print(
            "RESULTADO: FALHA"
        )

        print(
            "indice.json não foi alterado."
        )

        return 1


    if warnings:

        for source, message in warnings:

            print(
                f"[AVISO] {source}"
            )

            print(
                f"  - {message}"
            )


        print()


    expected = serialize_index(
        entries
    )


    try:

        current = current_output_text(
            output
        )

    except OSError as exc:

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            str(exc)
        )

        return 2


    print_report(
        len(articles),
        len(entries),
        ignored_count,
        warnings,
    )

    print()


    if args.check:

        if current == expected:

            print(
                "RESULTADO: "
                "ÍNDICE ATUALIZADO"
            )

            return 0


        print(
            "RESULTADO: "
            "ÍNDICE DESATUALIZADO"
        )

        print(
            "Execute gerar-indice.py "
            "sem --check."
        )

        return 1


    if current == expected:

        print(
            "RESULTADO: "
            "ÍNDICE JÁ ESTAVA ATUALIZADO"
        )

        return 0


    try:

        write_atomic(
            output,
            expected,
        )

    except OSError as exc:

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            "Não foi possível gravar "
            f"o índice: {exc}"
        )

        return 2


    print(
        "RESULTADO: "
        "ÍNDICE GERADO COM SUCESSO"
    )

    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
