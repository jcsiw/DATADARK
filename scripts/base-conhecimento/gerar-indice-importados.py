#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DIR = (
    ROOT
    / "base-conhecimento"
    / "artigos"
    / "importados"
)

DEFAULT_OUTPUT = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice-importados.json"
)


def collapse(value: str) -> str:
    return " ".join(value.split())


def slugify(value: str) -> str:

    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    ascii_value = (
        normalized
        .encode(
            "ascii",
            "ignore",
        )
        .decode("ascii")
        .lower()
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        ascii_value,
    ).strip("-")

    return slug or "documento"


class HTMLMetadataParser(HTMLParser):

    def __init__(self) -> None:

        super().__init__(
            convert_charrefs=True
        )

        self.in_title = False
        self.in_h1 = False
        self.in_body = False
        self.in_script = False
        self.in_style = False

        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.body_parts: list[str] = []

        self.meta: dict[str, str] = {}


    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attributes = {
            str(key).lower():
                value or ""
            for key, value in attrs
        }

        if tag == "title":
            self.in_title = True

        elif tag == "h1":
            self.in_h1 = True

        elif tag == "body":
            self.in_body = True

        elif tag == "script":
            self.in_script = True

        elif tag == "style":
            self.in_style = True

        elif tag == "meta":

            name = (
                attributes
                .get("name", "")
                .strip()
                .lower()
            )

            content = (
                attributes
                .get("content", "")
            )

            if (
                name
                and name not in self.meta
            ):
                self.meta[name] = content


    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if tag == "title":
            self.in_title = False

        elif tag == "h1":
            self.in_h1 = False

        elif tag == "body":
            self.in_body = False

        elif tag == "script":
            self.in_script = False

        elif tag == "style":
            self.in_style = False


    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.in_title:
            self.title_parts.append(data)

        if self.in_h1:
            self.h1_parts.append(data)

        if (
            self.in_body
            and not self.in_script
            and not self.in_style
        ):
            text = collapse(data)

            if text:
                self.body_parts.append(text)


def parse_html(
    path: Path,
) -> HTMLMetadataParser:

    try:

        raw = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        raw = path.read_text(
            encoding="latin-1"
        )

    parser = HTMLMetadataParser()

    parser.feed(raw)
    parser.close()

    return parser


def parse_list(
    value: str,
) -> list[str]:

    return [
        collapse(item)
        for item in value.split(",")
        if collapse(item)
    ]


def build_entry(
    path: Path,
    base: Path,
) -> dict:

    parser = parse_html(path)

    relative = path.relative_to(base)

    title = collapse(
        " ".join(
            parser.title_parts
        )
    )

    if not title:

        title = collapse(
            " ".join(
                parser.h1_parts
            )
        )

    if not title:

        title = collapse(
            path.stem
            .replace("-", " ")
            .replace("_", " ")
        )

    description = collapse(
        parser.meta.get(
            "description",
            "",
        )
    )

    if not description:

        body = collapse(
            " ".join(
                parser.body_parts
            )
        )

        description = (
            body[:300]
            if body
            else title
        )

    keywords = parse_list(
        parser.meta.get(
            "keywords",
            "",
        )
    )

    aliases = parse_list(
        parser.meta.get(
            "kb-aliases",
            "",
        )
    )

    relative_without_suffix = (
        relative.with_suffix("")
    )

    slug = slugify(
        relative_without_suffix.as_posix()
    )

    encoded_parts = [
        quote(
            part,
            safe="-._~",
        )
        for part in relative.parts
    ]

    url = (
        "artigos/importados/"
        + "/".join(encoded_parts)
    )

    return {
        "slug":
            slug,

        "title":
            html.unescape(title),

        "description":
            html.unescape(description),

        "url":
            url,

        "category_id":
            "documentos",

        "category":
            "Documentos",

        "keywords":
            keywords,

        "aliases":
            aliases,
    }


def discover(
    directory: Path,
) -> list[Path]:

    if not directory.exists():

        return []

    return sorted(
        (
            path
            for path in directory.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                    == ".html"
            )
        ),
        key=lambda path:
            path.relative_to(
                directory
            )
            .as_posix()
            .casefold(),
    )


def generate(
    directory: Path,
) -> list[dict]:

    entries: list[dict] = []
    slugs: set[str] = set()

    for path in discover(directory):

        entry = build_entry(
            path,
            directory,
        )

        slug = entry["slug"]

        if slug in slugs:

            raise RuntimeError(
                "slug duplicado em HTMLs "
                f"importados: {slug}"
            )

        slugs.add(slug)

        entries.append(entry)

    return entries


def serialize(
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


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Gera índice de pesquisa "
            "para HTMLs importados."
        )
    )

    parser.add_argument(
        "--directory",
        type=Path,
        default=DEFAULT_DIR,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--check",
        action="store_true",
    )

    args = parser.parse_args()

    try:

        entries = generate(
            args.directory
        )

        expected = serialize(
            entries
        )

        if args.check:

            try:
                current = (
                    args.output
                    .read_text(
                        encoding="utf-8"
                    )
                )

            except FileNotFoundError:
                print(
                    "INDICE_IMPORTADOS="
                    "DIVERGENTE"
                )
                return 1

            if current != expected:

                print(
                    "INDICE_IMPORTADOS="
                    "DIVERGENTE"
                )
                return 1

            print(
                "INDICE_IMPORTADOS=OK"
            )

            print(
                f"IMPORTADOS={len(entries)}"
            )

            return 0

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = (
            args.output
            .with_name(
                "." + args.output.name
                + ".tmp"
            )
        )

        temporary.write_text(
            expected,
            encoding="utf-8",
        )

        temporary.replace(
            args.output
        )

        print(
            f"IMPORTADOS={len(entries)}"
        )

        print(
            "RESULTADO="
            "INDICE_IMPORTADOS_GERADO"
        )

        return 0

    except Exception as exc:

        print(
            f"ERRO: {exc}",
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(main())
