#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DEFAULT_OFFICIAL = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

DEFAULT_IMPORTED = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice-importados.json"
)

DEFAULT_OUTPUT = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice-pesquisa.json"
)


class SearchIndexError(RuntimeError):
    pass


def load_index(
    path: Path,
    label: str,
) -> list[dict]:

    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError as exc:
        raise SearchIndexError(
            f"{label} ausente: {path}"
        ) from exc

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SearchIndexError(
            f"{label} inválido: {path}"
        ) from exc


    if not isinstance(data, list):
        raise SearchIndexError(
            f"{label} deve conter um array"
        )


    seen: set[str] = set()

    for entry in data:

        if not isinstance(entry, dict):
            raise SearchIndexError(
                f"{label} contém entrada inválida"
            )

        slug = entry.get("slug")

        if (
            not isinstance(slug, str)
            or not slug.strip()
        ):
            raise SearchIndexError(
                f"{label} contém slug inválido"
            )

        if slug in seen:
            raise SearchIndexError(
                f"{label} contém slug duplicado: "
                f"{slug}"
            )

        seen.add(slug)


    return data


def build_index(
    official: list[dict],
    imported: list[dict],
) -> list[dict]:

    official_slugs = {
        entry["slug"]
        for entry in official
    }

    collisions = sorted(
        entry["slug"]
        for entry in imported
        if entry["slug"] in official_slugs
    )

    if collisions:
        raise SearchIndexError(
            "slug de HTML importado conflita "
            "com artigo editorial: "
            + ", ".join(collisions)
        )


    return [
        *official,
        *imported,
    ]


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


def write_atomic(
    path: Path,
    content: str,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_name = (
        tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
    )

    temporary = Path(
        temporary_name
    )

    try:

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:

            handle.write(content)
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:

        temporary.unlink(
            missing_ok=True
        )


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Gera o índice unificado usado "
            "pela pesquisa da Base de Conhecimento."
        )
    )

    parser.add_argument(
        "--official",
        type=Path,
        default=DEFAULT_OFFICIAL,
    )

    parser.add_argument(
        "--imported",
        type=Path,
        default=DEFAULT_IMPORTED,
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

        official = load_index(
            args.official,
            "indice.json",
        )

        imported = load_index(
            args.imported,
            "indice-importados.json",
        )

        combined = build_index(
            official,
            imported,
        )

        expected = serialize(
            combined
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
                    "INDICE_PESQUISA=DIVERGENTE"
                )
                return 1

            if current != expected:
                print(
                    "INDICE_PESQUISA=DIVERGENTE"
                )
                return 1

            print(
                "INDICE_PESQUISA=OK"
            )

            print(
                f"EDITORIAIS={len(official)}"
            )

            print(
                f"IMPORTADOS={len(imported)}"
            )

            print(
                f"TOTAL={len(combined)}"
            )

            return 0


        write_atomic(
            args.output,
            expected,
        )

        print(
            f"EDITORIAIS={len(official)}"
        )

        print(
            f"IMPORTADOS={len(imported)}"
        )

        print(
            f"TOTAL={len(combined)}"
        )

        print(
            "RESULTADO="
            "INDICE_PESQUISA_GERADO"
        )

        return 0

    except SearchIndexError as exc:

        print(
            f"ERRO: {exc}",
            file=sys.stderr,
        )

        return 2


if __name__ == "__main__":
    raise SystemExit(main())
