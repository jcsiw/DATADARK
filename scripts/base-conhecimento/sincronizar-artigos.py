#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Sincronizador Editorial V1 — núcleo dry-run.

ETAPA 8.7.2B

Responsabilidades nesta fase:
- inventariar HTMLs públicos e rascunhos;
- detectar artigos novos e já catalogados;
- preservar identidade editorial existente;
- alocar IDs DD-KB de forma determinística;
- construir Catálogo Editorial candidato;
- gerar indice.json candidato;
- gerar relacionados.json candidato;
- renderizar RELATED em diretório candidato;
- validar novamente o estado pós-render;
- detectar alteração concorrente dos artefatos oficiais;
- nunca modificar o repositório oficial.

Modos operacionais:
- sem --write: executa dry-run integral;
- com --write: promove somente o candidato já validado;
- a promoção usa staged files, fingerprint, fsync e rollback.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
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


SCRIPT_PATH = Path(__file__).resolve()

SCRIPTS_DIR = SCRIPT_PATH.parent

REPOSITORY_ROOT = (
    SCRIPT_PATH
    .parents[2]
)


DEFAULT_ARTICLES = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "artigos"
)

DEFAULT_CATEGORIES = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

DEFAULT_INDEX = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

DEFAULT_RELATED = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "relacionados.json"
)

DEFAULT_CATALOG = (
    SCRIPTS_DIR
    / "editorial"
    / "catalogo.json"
)

DEFAULT_TEMPLATE = (
    SCRIPTS_DIR
    / "templates"
    / "artigo-v1.html"
)


VALIDATE_ARTICLES = (
    SCRIPTS_DIR
    / "validar-artigos.py"
)

GENERATE_INDEX = (
    SCRIPTS_DIR
    / "gerar-indice.py"
)

VALIDATE_CATALOG = (
    SCRIPTS_DIR
    / "validar-catalogo-editorial.py"
)

GENERATE_RELATED = (
    SCRIPTS_DIR
    / "gerar-relacionados.py"
)

RENDER_RELATED = (
    SCRIPTS_DIR
    / "renderizar-relacionados.py"
)


EDITORIAL_ID_RE = re.compile(
    r"^DD-KB-([0-9]{6})$"
)


CHECK_PLACEHOLDER_DATE = (
    "2000-01-01"
)


class SynchronizationError(Exception):
    """Falha funcional / estrutural da sincronização."""


def run_tool(
    command: list[str],
    label: str,
) -> subprocess.CompletedProcess[str]:

    result = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        env={
            **__import__("os").environ,
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )

    if result.returncode != 0:

        details = []

        if result.stdout.strip():
            details.append(
                result.stdout.strip()
            )

        if result.stderr.strip():
            details.append(
                result.stderr.strip()
            )

        suffix = (
            "\n\n".join(details)
            if details
            else (
                "comando terminou sem mensagem "
                f"(exit={result.returncode})"
            )
        )

        raise SynchronizationError(
            f"{label} falhou:\n{suffix}"
        )

    return result


def read_json(
    path: Path,
    label: str,
) -> Any:

    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except FileNotFoundError as exc:

        raise SynchronizationError(
            f"{label} ausente: {path}"
        ) from exc

    except json.JSONDecodeError as exc:

        raise SynchronizationError(
            f"{label} contém JSON inválido: "
            f"{exc}"
        ) from exc

    except OSError as exc:

        raise SynchronizationError(
            f"falha ao ler {label}: "
            f"{path}: {exc}"
        ) from exc


def canonical_json_bytes(
    data: Any,
) -> bytes:

    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def direct_html_files(
    directory: Path,
) -> list[Path]:

    if not directory.is_dir():

        raise SynchronizationError(
            "diretório de artigos inválido: "
            f"{directory}"
        )

    return sorted(
        (
            path
            for path in directory.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                    == ".html"
            )
        ),
        key=lambda path:
            path.name.casefold(),
    )


def split_articles(
    directory: Path,
) -> tuple[
    list[Path],
    list[Path],
]:

    all_html = direct_html_files(
        directory
    )

    ignored = [
        path
        for path in all_html
        if path.name.startswith("_")
    ]

    public = [
        path
        for path in all_html
        if not path.name.startswith("_")
    ]

    return public, ignored


def fingerprint_file(
    digest: "hashlib._Hash",
    label: str,
    path: Path,
) -> None:

    try:
        content = path.read_bytes()

    except OSError as exc:

        raise SynchronizationError(
            "falha ao calcular fingerprint: "
            f"{path}: {exc}"
        ) from exc

    digest.update(
        label.encode("utf-8")
    )

    digest.update(b"\0")

    digest.update(
        content
    )

    digest.update(b"\0")


def official_state_fingerprint(
    *,
    articles_dir: Path,
    catalog_path: Path,
    index_path: Path,
    related_path: Path,
    categories_path: Path,
    template_path: Path,
) -> str:

    digest = hashlib.sha256()

    fixed = (
        ("catalog", catalog_path),
        ("index", index_path),
        ("related", related_path),
        ("categories", categories_path),
        ("template", template_path),
    )

    for label, path in fixed:

        fingerprint_file(
            digest,
            label,
            path,
        )

    for article in direct_html_files(
        articles_dir
    ):

        fingerprint_file(
            digest,
            "article:"
            + article.name,
            article,
        )

    return digest.hexdigest()


def validate_publication_date(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    try:
        parsed = date.fromisoformat(
            value
        )

    except ValueError as exc:

        raise SynchronizationError(
            "--publication-date inválida; "
            "use YYYY-MM-DD."
        ) from exc

    normalized = parsed.isoformat()

    if normalized != value:

        raise SynchronizationError(
            "--publication-date deve usar "
            "exatamente YYYY-MM-DD."
        )

    return normalized


def validate_catalog_shell(
    data: Any,
) -> list[dict[str, Any]]:

    if not isinstance(
        data,
        dict,
    ):

        raise SynchronizationError(
            "Catálogo Editorial deve ser "
            "um objeto JSON."
        )

    if data.get("version") != 1:

        raise SynchronizationError(
            "Catálogo Editorial possui "
            "version diferente de 1."
        )

    articles = data.get(
        "articles"
    )

    if not isinstance(
        articles,
        list,
    ):

        raise SynchronizationError(
            "Catálogo Editorial possui "
            "articles inválido."
        )

    result = []

    ids = set()
    slugs = set()

    for number, raw in enumerate(
        articles,
        start=1,
    ):

        if not isinstance(
            raw,
            dict,
        ):

            raise SynchronizationError(
                "registro editorial inválido "
                f"na posição {number}."
            )

        article_id = raw.get("id")
        slug = raw.get("slug")

        if not isinstance(
            article_id,
            str,
        ):

            raise SynchronizationError(
                "registro editorial sem "
                "id válido."
            )

        if (
            EDITORIAL_ID_RE.fullmatch(
                article_id
            )
            is None
        ):

            raise SynchronizationError(
                "id editorial fora do "
                f"contrato V1: {article_id!r}"
            )

        if not isinstance(
            slug,
            str,
        ) or not slug:

            raise SynchronizationError(
                f"{article_id}: slug inválido."
            )

        if article_id in ids:

            raise SynchronizationError(
                "id editorial duplicado: "
                f"{article_id}"
            )

        if slug in slugs:

            raise SynchronizationError(
                "slug editorial duplicado: "
                f"{slug}"
            )

        ids.add(article_id)
        slugs.add(slug)
        result.append(raw)

    return result


def next_editorial_number(
    articles: list[dict[str, Any]],
) -> int:

    numbers = []

    for article in articles:

        article_id = article["id"]

        match = (
            EDITORIAL_ID_RE.fullmatch(
                article_id
            )
        )

        if match is None:

            raise SynchronizationError(
                "id editorial inválido: "
                f"{article_id!r}"
            )

        numbers.append(
            int(
                match.group(1)
            )
        )

    number = (
        max(
            numbers,
            default=0,
        )
        + 1
    )

    if number > 999999:

        raise SynchronizationError(
            "sequência editorial "
            "DD-KB esgotada."
        )

    return number


def load_index_entries(
    path: Path,
) -> list[dict[str, Any]]:

    data = read_json(
        path,
        "índice candidato",
    )

    if not isinstance(
        data,
        list,
    ):

        raise SynchronizationError(
            "indice.json candidato "
            "não contém array."
        )

    slugs = set()

    for entry in data:

        if not isinstance(
            entry,
            dict,
        ):

            raise SynchronizationError(
                "entrada inválida no "
                "índice candidato."
            )

        slug = entry.get("slug")

        if not isinstance(
            slug,
            str,
        ) or not slug:

            raise SynchronizationError(
                "entrada do índice sem "
                "slug válido."
            )

        if slug in slugs:

            raise SynchronizationError(
                "slug duplicado no índice "
                f"candidato: {slug}"
            )

        slugs.add(slug)

    return data


def validate_new_search_metadata(
    entry: dict[str, Any],
) -> None:

    slug = entry["slug"]

    for field, html_name in (
        ("keywords", "keywords"),
        ("aliases", "kb-aliases"),
    ):

        values = entry.get(field)

        if (
            not isinstance(values, list)
            or not values
            or any(
                not isinstance(value, str)
                or not value.strip()
                for value in values
            )
        ):

            raise SynchronizationError(
                f"{slug}: meta {html_name} "
                "é obrigatória e deve possuir "
                "ao menos um valor no "
                "Sincronizador Editorial V1."
            )


def build_catalog_candidate(
    *,
    original_catalog: dict[str, Any],
    catalog_articles: list[dict[str, Any]],
    index_entries: list[dict[str, Any]],
    publication_date: str | None,
) -> tuple[
    dict[str, Any],
    list[tuple[str, str]],
    int,
]:

    catalog_by_slug = {
        article["slug"]:
            article
        for article in catalog_articles
    }

    index_by_slug = {
        entry["slug"]:
            entry
        for entry in index_entries
    }

    published_slugs = {
        article["slug"]
        for article in catalog_articles
        if article.get("status")
            == "published"
    }

    public_slugs = set(
        index_by_slug
    )

    missing_public = sorted(
        published_slugs
        - public_slugs
    )

    if missing_public:

        raise SynchronizationError(
            "artigo(s) published ausente(s) "
            "do diretório público: "
            + ", ".join(
                missing_public
            )
        )

    existing_slugs = sorted(
        public_slugs
        & set(catalog_by_slug),
        key=str.casefold,
    )

    for slug in existing_slugs:

        catalog_entry = (
            catalog_by_slug[slug]
        )

        index_entry = (
            index_by_slug[slug]
        )

        if (
            catalog_entry.get("status")
            != "published"
        ):

            raise SynchronizationError(
                f"{slug}: existe HTML público, "
                "mas o registro editorial não "
                "está published."
            )

        if (
            catalog_entry.get("title")
            != index_entry.get("title")
        ):

            raise SynchronizationError(
                f"{slug}: identidade title "
                "de artigo existente foi "
                "alterada."
            )

        if (
            catalog_entry.get(
                "category_id"
            )
            != index_entry.get(
                "category_id"
            )
        ):

            raise SynchronizationError(
                f"{slug}: identidade "
                "category_id de artigo "
                "existente foi alterada."
            )

    new_slugs = sorted(
        public_slugs
        - set(catalog_by_slug),
        key=str.casefold,
    )

    if (
        new_slugs
        and publication_date is None
    ):

        raise SynchronizationError(
            "existem artigos públicos novos; "
            "--publication-date YYYY-MM-DD "
            "é obrigatória."
        )

    for slug in new_slugs:

        validate_new_search_metadata(
            index_by_slug[slug]
        )

    candidate = json.loads(
        json.dumps(
            original_catalog,
            ensure_ascii=False,
        )
    )

    candidate_articles = (
        candidate["articles"]
    )

    next_number = (
        next_editorial_number(
            catalog_articles
        )
    )

    allocated = []

    for slug in new_slugs:

        if next_number > 999999:

            raise SynchronizationError(
                "sequência editorial "
                "DD-KB esgotada."
            )

        entry = index_by_slug[slug]

        editorial_id = (
            f"DD-KB-{next_number:06d}"
        )

        candidate_articles.append(
            {
                "id":
                    editorial_id,
                "title":
                    entry["title"],
                "slug":
                    slug,
                "category_id":
                    entry["category_id"],
                "status":
                    "published",
                "priority":
                    "normal",
                "created_on":
                    publication_date,
                "published_on":
                    publication_date,
                "review_due":
                    None,
                "notes":
                    "",
            }
        )

        allocated.append(
            (
                editorial_id,
                slug,
            )
        )

        next_number += 1

    candidate_articles.sort(
        key=lambda item:
            item["id"]
    )

    return (
        candidate,
        allocated,
        len(existing_slugs),
    )


def copy_source_articles(
    source: Path,
    destination: Path,
) -> None:

    destination.mkdir(
        parents=True,
        exist_ok=False,
    )

    for article in direct_html_files(
        source
    ):

        shutil.copy2(
            article,
            destination
            / article.name,
        )


def files_differ(
    first: Path,
    second: Path,
) -> bool:

    try:
        return (
            first.read_bytes()
            != second.read_bytes()
        )

    except OSError as exc:

        raise SynchronizationError(
            "falha ao comparar arquivos: "
            f"{exc}"
        ) from exc


def rendered_difference_count(
    *,
    original_articles: Path,
    rendered_articles: Path,
    index_entries: list[dict[str, Any]],
) -> int:

    count = 0

    for entry in index_entries:

        slug = entry["slug"]

        source = (
            original_articles
            / f"{slug}.html"
        )

        rendered = (
            rendered_articles
            / f"{slug}.html"
        )

        if (
            not source.is_file()
            or not rendered.is_file()
        ):

            raise SynchronizationError(
                "comparação de renderização "
                f"incompleta para {slug}."
            )

        if files_differ(
            source,
            rendered,
        ):
            count += 1

    return count


def fsync_directory(
    directory: Path,
) -> None:

    flags = os.O_RDONLY

    flags |= getattr(
        os,
        "O_DIRECTORY",
        0,
    )

    descriptor = os.open(
        directory,
        flags,
    )

    try:

        os.fsync(
            descriptor
        )

    finally:

        os.close(
            descriptor
        )


def create_staged_file(
    *,
    target: Path,
    content: bytes,
    mode: int,
    purpose: str,
) -> Path:

    descriptor, temp_name = (
        tempfile.mkstemp(
            prefix=(
                f".{target.name}."
                f"{purpose}."
            ),
            suffix=".tmp",
            dir=target.parent,
        )
    )

    temp_path = Path(
        temp_name
    )

    try:

        with os.fdopen(
            descriptor,
            "wb",
        ) as handle:

            handle.write(
                content
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.chmod(
            temp_path,
            mode,
        )

        return temp_path

    except Exception:

        try:

            temp_path.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        raise


def restore_file_atomic(
    *,
    target: Path,
    content: bytes,
    mode: int,
) -> None:

    staged = create_staged_file(
        target=target,
        content=content,
        mode=mode,
        purpose="restore",
    )

    try:

        os.replace(
            staged,
            target,
        )

        fsync_directory(
            target.parent
        )

    finally:

        staged.unlink(
            missing_ok=True
        )


def file_mode(
    path: Path,
) -> int:

    try:

        return stat.S_IMODE(
            path.stat().st_mode
        )

    except OSError as exc:

        raise SynchronizationError(
            "não foi possível obter "
            f"modo de {path}: {exc}"
        ) from exc


def build_write_targets(
    *,
    args: argparse.Namespace,
    result: dict[str, Any],
) -> list[
    tuple[
        str,
        Path,
        bytes,
    ]
]:

    articles_dir = (
        args.articles_dir
        .expanduser()
        .resolve()
    )

    catalog_path = (
        args.catalog
        .expanduser()
        .resolve()
    )

    index_path = (
        args.index
        .expanduser()
        .resolve()
    )

    related_path = (
        args.related
        .expanduser()
        .resolve()
    )

    targets = []

    rendered = result[
        "rendered_bytes"
    ]

    for slug in sorted(
        rendered,
        key=str.casefold,
    ):

        target = (
            articles_dir
            / f"{slug}.html"
        )

        if not target.is_file():

            raise SynchronizationError(
                "HTML público desapareceu "
                "antes da gravação: "
                f"{target}"
            )

        desired = rendered[
            slug
        ]

        if (
            target.read_bytes()
            != desired
        ):

            targets.append(
                (
                    f"article:{slug}",
                    target,
                    desired,
                )
            )

    fixed = (
        (
            "index",
            index_path,
            result["index_bytes"],
        ),
        (
            "catalog",
            catalog_path,
            result["catalog_bytes"],
        ),
        (
            "related",
            related_path,
            result["related_bytes"],
        ),
    )

    for label, target, desired in fixed:

        try:

            current = (
                target.read_bytes()
            )

        except OSError as exc:

            raise SynchronizationError(
                f"falha ao preservar "
                f"{target}: {exc}"
            ) from exc

        if current != desired:

            targets.append(
                (
                    label,
                    target,
                    desired,
                )
            )

    return targets


def validate_written_state(
    args: argparse.Namespace,
) -> None:

    articles_dir = (
        args.articles_dir
        .expanduser()
        .resolve()
    )

    catalog_path = (
        args.catalog
        .expanduser()
        .resolve()
    )

    index_path = (
        args.index
        .expanduser()
        .resolve()
    )

    related_path = (
        args.related
        .expanduser()
        .resolve()
    )

    categories_path = (
        args.categories
        .expanduser()
        .resolve()
    )

    template_path = (
        args.template
        .expanduser()
        .resolve()
    )

    run_tool(
        [
            sys.executable,
            str(VALIDATE_ARTICLES),
            "--directory",
            str(articles_dir),
            "--categories",
            str(categories_path),
        ],
        "validação pós-write",
    )

    run_tool(
        [
            sys.executable,
            str(GENERATE_INDEX),
            "--articles-dir",
            str(articles_dir),
            "--output",
            str(index_path),
            "--categories",
            str(categories_path),
            "--check",
        ],
        "check do índice pós-write",
    )

    run_tool(
        [
            sys.executable,
            str(VALIDATE_CATALOG),
            "--catalog",
            str(catalog_path),
            "--articles-dir",
            str(articles_dir),
            "--index",
            str(index_path),
            "--categories",
            str(categories_path),
        ],
        "validação do Catálogo pós-write",
    )

    run_tool(
        [
            sys.executable,
            str(GENERATE_RELATED),
            "--check",
            "--taxonomy",
            str(categories_path),
            "--index",
            str(index_path),
            "--catalog",
            str(catalog_path),
            "--articles-dir",
            str(articles_dir),
            "--output",
            str(related_path),
        ],
        "check dos relacionados pós-write",
    )

    run_tool(
        [
            sys.executable,
            str(RENDER_RELATED),
            "--articles-dir",
            str(articles_dir),
            "--template",
            str(template_path),
            "--index",
            str(index_path),
            "--related",
            str(related_path),
            "--categories",
            str(categories_path),
            "--catalog",
            str(catalog_path),
            "--check",
        ],
        "check do render pós-write",
    )


def persist_candidate(
    *,
    args: argparse.Namespace,
    result: dict[str, Any],
) -> int:

    if not result[
        "synchronization_needed"
    ]:

        return 0

    articles_dir = (
        args.articles_dir
        .expanduser()
        .resolve()
    )

    catalog_path = (
        args.catalog
        .expanduser()
        .resolve()
    )

    index_path = (
        args.index
        .expanduser()
        .resolve()
    )

    related_path = (
        args.related
        .expanduser()
        .resolve()
    )

    categories_path = (
        args.categories
        .expanduser()
        .resolve()
    )

    template_path = (
        args.template
        .expanduser()
        .resolve()
    )

    current_state = (
        official_state_fingerprint(
            articles_dir=articles_dir,
            catalog_path=catalog_path,
            index_path=index_path,
            related_path=related_path,
            categories_path=
                categories_path,
            template_path=
                template_path,
        )
    )

    if (
        current_state
        != result["state_token"]
    ):

        raise SynchronizationError(
            "estado oficial mudou após "
            "o dry-run; operação cancelada."
        )

    targets = build_write_targets(
        args=args,
        result=result,
    )

    if not targets:

        return 0

    originals = {}

    try:

        for label, target, _ in targets:

            originals[target] = (
                target.read_bytes(),
                file_mode(
                    target
                ),
                label,
            )

    except OSError as exc:

        raise SynchronizationError(
            "não foi possível preservar "
            f"os alvos da transação: {exc}"
        ) from exc

    staged = {}

    installed = []

    try:

        # --------------------------------------
        # PREPARAÇÃO COMPLETA
        # --------------------------------------

        for label, target, content in targets:

            original_mode = (
                originals[target][1]
            )

            staged[target] = (
                create_staged_file(
                    target=target,
                    content=content,
                    mode=original_mode,
                    purpose="sync",
                )
            )

        # --------------------------------------
        # SEGUNDO FINGERPRINT
        # --------------------------------------

        if (
            official_state_fingerprint(
                articles_dir=
                    articles_dir,
                catalog_path=
                    catalog_path,
                index_path=
                    index_path,
                related_path=
                    related_path,
                categories_path=
                    categories_path,
                template_path=
                    template_path,
            )
            != result["state_token"]
        ):

            raise SynchronizationError(
                "estado oficial mudou durante "
                "a preparação da transação."
            )

        # --------------------------------------
        # PROMOÇÕES INDIVIDUAIS
        # --------------------------------------

        for label, target, _ in targets:

            staged_path = (
                staged[target]
            )

            os.replace(
                staged_path,
                target,
            )

            staged[target] = None

            installed.append(
                target
            )

            fsync_directory(
                target.parent
            )

        # --------------------------------------
        # VERIFICAÇÃO BYTE A BYTE
        # --------------------------------------

        for label, target, desired in targets:

            if (
                target.read_bytes()
                != desired
            ):

                raise SynchronizationError(
                    "conteúdo pós-promoção "
                    "divergente: "
                    f"{label}"
                )

            if (
                file_mode(target)
                != originals[target][1]
            ):

                raise SynchronizationError(
                    "modo físico alterado "
                    "durante promoção: "
                    f"{label}"
                )

        # --------------------------------------
        # VALIDAÇÃO OFICIAL PÓS-WRITE
        # --------------------------------------

        validate_written_state(
            args
        )

        return len(
            installed
        )

    except Exception as exc:

        rollback_errors = []

        for target in reversed(
            installed
        ):

            original_content, original_mode, label = (
                originals[target]
            )

            try:

                restore_file_atomic(
                    target=target,
                    content=original_content,
                    mode=original_mode,
                )

            except Exception as rollback_exc:

                rollback_errors.append(
                    f"{label}: "
                    f"{rollback_exc}"
                )

        # --------------------------------------
        # VERIFICAÇÃO DO ROLLBACK
        # --------------------------------------

        for target, (
            original_content,
            original_mode,
            label,
        ) in originals.items():

            try:

                if (
                    target.read_bytes()
                    != original_content
                ):

                    rollback_errors.append(
                        f"{label}: bytes "
                        "não restaurados"
                    )

                if (
                    file_mode(target)
                    != original_mode
                ):

                    rollback_errors.append(
                        f"{label}: modo "
                        "não restaurado"
                    )

            except Exception as rollback_exc:

                rollback_errors.append(
                    f"{label}: verificação "
                    f"falhou: {rollback_exc}"
                )

        if rollback_errors:

            raise RuntimeError(
                "ROLLBACK INCOMPLETO: "
                + " | ".join(
                    rollback_errors
                )
            ) from exc

        raise

    finally:

        for staged_path in (
            staged.values()
        ):

            if staged_path is None:
                continue

            try:

                staged_path.unlink(
                    missing_ok=True
                )

            except OSError:
                pass


def run_dry_run(
    args: argparse.Namespace,
) -> dict[str, Any]:

    articles_dir = (
        args.articles_dir
        .expanduser()
        .resolve()
    )

    catalog_path = (
        args.catalog
        .expanduser()
        .resolve()
    )

    index_path = (
        args.index
        .expanduser()
        .resolve()
    )

    related_path = (
        args.related
        .expanduser()
        .resolve()
    )

    categories_path = (
        args.categories
        .expanduser()
        .resolve()
    )

    template_path = (
        args.template
        .expanduser()
        .resolve()
    )

    publication_date = (
        validate_publication_date(
            args.publication_date
        )
    )

    state_before = (
        official_state_fingerprint(
            articles_dir=articles_dir,
            catalog_path=catalog_path,
            index_path=index_path,
            related_path=related_path,
            categories_path=
                categories_path,
            template_path=
                template_path,
        )
    )

    public, ignored = (
        split_articles(
            articles_dir
        )
    )

    original_catalog = read_json(
        catalog_path,
        "Catálogo Editorial",
    )

    catalog_articles = (
        validate_catalog_shell(
            original_catalog
        )
    )

    with tempfile.TemporaryDirectory(
        prefix=(
            "datadark-sync-editorial-"
        )
    ) as temporary:

        temp_root = Path(
            temporary
        )

        temp_articles = (
            temp_root
            / "artigos"
        )

        temp_index = (
            temp_root
            / "indice.json"
        )

        temp_catalog = (
            temp_root
            / "catalogo.json"
        )

        temp_related = (
            temp_root
            / "relacionados.json"
        )

        rendered_dir = (
            temp_root
            / "renderizados"
        )

        post_index = (
            temp_root
            / "indice-pos-render.json"
        )

        post_related = (
            temp_root
            / "relacionados-pos-render.json"
        )

        copy_source_articles(
            articles_dir,
            temp_articles,
        )

        # --------------------------------------
        # VALIDAÇÃO DO HTML DE ENTRADA
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(VALIDATE_ARTICLES),
                "--directory",
                str(temp_articles),
                "--categories",
                str(categories_path),
            ],
            "validação dos artigos de entrada",
        )

        # --------------------------------------
        # ÍNDICE CANDIDATO
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(GENERATE_INDEX),
                "--articles-dir",
                str(temp_articles),
                "--output",
                str(temp_index),
                "--categories",
                str(categories_path),
            ],
            "geração do índice candidato",
        )

        index_entries = (
            load_index_entries(
                temp_index
            )
        )

        candidate_publication_date = (
            publication_date
        )

        if (
            candidate_publication_date
            is None
            and getattr(
                args,
                "check",
                False,
            )
        ):

            candidate_publication_date = (
                CHECK_PLACEHOLDER_DATE
            )

        (
            catalog_candidate,
            allocated,
            existing_count,
        ) = build_catalog_candidate(
            original_catalog=
                original_catalog,
            catalog_articles=
                catalog_articles,
            index_entries=
                index_entries,
            publication_date=
                candidate_publication_date,
        )

        temp_catalog.write_bytes(
            canonical_json_bytes(
                catalog_candidate
            )
        )

        # --------------------------------------
        # CATÁLOGO CANDIDATO
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(VALIDATE_CATALOG),
                "--catalog",
                str(temp_catalog),
                "--articles-dir",
                str(temp_articles),
                "--index",
                str(temp_index),
                "--categories",
                str(categories_path),
            ],
            "validação do Catálogo candidato",
        )

        # --------------------------------------
        # RELACIONADOS CANDIDATO
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(GENERATE_RELATED),
                "--taxonomy",
                str(categories_path),
                "--index",
                str(temp_index),
                "--catalog",
                str(temp_catalog),
                "--articles-dir",
                str(temp_articles),
                "--output",
                str(temp_related),
            ],
            "geração dos relacionados candidatos",
        )

        run_tool(
            [
                sys.executable,
                str(GENERATE_RELATED),
                "--check",
                "--taxonomy",
                str(categories_path),
                "--index",
                str(temp_index),
                "--catalog",
                str(temp_catalog),
                "--articles-dir",
                str(temp_articles),
                "--output",
                str(temp_related),
            ],
            "check dos relacionados candidatos",
        )

        # --------------------------------------
        # RENDERIZAÇÃO CANDIDATA
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(RENDER_RELATED),
                "--articles-dir",
                str(temp_articles),
                "--template",
                str(template_path),
                "--index",
                str(temp_index),
                "--related",
                str(temp_related),
                "--categories",
                str(categories_path),
                "--catalog",
                str(temp_catalog),
                "--output-dir",
                str(rendered_dir),
            ],
            "renderização candidata",
        )

        # --------------------------------------
        # SEGUNDA VALIDAÇÃO, PÓS-RENDER
        # --------------------------------------

        run_tool(
            [
                sys.executable,
                str(VALIDATE_ARTICLES),
                "--directory",
                str(rendered_dir),
                "--categories",
                str(categories_path),
            ],
            "validação pós-render",
        )

        run_tool(
            [
                sys.executable,
                str(GENERATE_INDEX),
                "--articles-dir",
                str(rendered_dir),
                "--output",
                str(post_index),
                "--categories",
                str(categories_path),
            ],
            "índice pós-render",
        )

        if files_differ(
            temp_index,
            post_index,
        ):

            raise SynchronizationError(
                "renderização alterou dados "
                "indexáveis do artigo."
            )

        run_tool(
            [
                sys.executable,
                str(VALIDATE_CATALOG),
                "--catalog",
                str(temp_catalog),
                "--articles-dir",
                str(rendered_dir),
                "--index",
                str(temp_index),
                "--categories",
                str(categories_path),
            ],
            "Catálogo pós-render",
        )

        run_tool(
            [
                sys.executable,
                str(GENERATE_RELATED),
                "--taxonomy",
                str(categories_path),
                "--index",
                str(temp_index),
                "--catalog",
                str(temp_catalog),
                "--articles-dir",
                str(rendered_dir),
                "--output",
                str(post_related),
            ],
            "relacionados pós-render",
        )

        if files_differ(
            temp_related,
            post_related,
        ):

            raise SynchronizationError(
                "renderização alterou o grafo "
                "de relacionados."
            )

        run_tool(
            [
                sys.executable,
                str(RENDER_RELATED),
                "--articles-dir",
                str(rendered_dir),
                "--template",
                str(template_path),
                "--index",
                str(temp_index),
                "--related",
                str(temp_related),
                "--categories",
                str(categories_path),
                "--catalog",
                str(temp_catalog),
                "--check",
            ],
            "check pós-render",
        )

        # --------------------------------------
        # FINGERPRINT CONCORRENTE
        # --------------------------------------

        state_after = (
            official_state_fingerprint(
                articles_dir=
                    articles_dir,
                catalog_path=
                    catalog_path,
                index_path=
                    index_path,
                related_path=
                    related_path,
                categories_path=
                    categories_path,
                template_path=
                    template_path,
            )
        )

        if state_after != state_before:

            raise SynchronizationError(
                "estado oficial mudou durante "
                "o dry-run."
            )

        catalog_changed = (
            catalog_path.read_bytes()
            != temp_catalog.read_bytes()
        )

        index_changed = (
            index_path.read_bytes()
            != temp_index.read_bytes()
        )

        related_changed = (
            related_path.read_bytes()
            != temp_related.read_bytes()
        )

        rendered_changed = (
            rendered_difference_count(
                original_articles=
                    articles_dir,
                rendered_articles=
                    rendered_dir,
                index_entries=
                    index_entries,
            )
        )

        synchronization_needed = (
            catalog_changed
            or index_changed
            or related_changed
            or rendered_changed > 0
        )

        result = {
            "public_count":
                len(public),
            "ignored_count":
                len(ignored),
            "existing_count":
                existing_count,
            "new_count":
                len(allocated),
            "allocated":
                allocated,
            "catalog_changed":
                catalog_changed,
            "index_changed":
                index_changed,
            "related_changed":
                related_changed,
            "rendered_changed":
                rendered_changed,
            "synchronization_needed":
                synchronization_needed,
            "state_token":
                state_before,

            "catalog_bytes":
                temp_catalog.read_bytes(),

            "index_bytes":
                temp_index.read_bytes(),

            "related_bytes":
                temp_related.read_bytes(),

            "rendered_bytes": {
                entry["slug"]:
                    (
                        rendered_dir
                        / (
                            entry["slug"]
                            + ".html"
                        )
                    ).read_bytes()
                for entry in index_entries
            },
        }

    return result


def yes_no(
    value: bool,
) -> str:

    return (
        "YES"
        if value
        else "NO"
    )


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Valida e sincroniza o estado "
            "editorial da Base de Conhecimento "
            "DATADARK. Por padrão executa "
            "dry-run; a gravação exige --write."
        )
    )

    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=DEFAULT_ARTICLES,
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
    )

    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
    )

    parser.add_argument(
        "--related",
        type=Path,
        default=DEFAULT_RELATED,
    )

    parser.add_argument(
        "--categories",
        type=Path,
        default=DEFAULT_CATEGORIES,
    )

    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
    )

    mode = (
        parser.add_mutually_exclusive_group()
    )

    mode.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verifica o estado editorial "
            "sem escrever. Retorna 0 quando "
            "sincronizado, 1 quando existe "
            "divergência e 2 em erro "
            "estrutural ou operacional."
        ),
    )

    mode.add_argument(
        "--write",
        action="store_true",
        help=(
            "Promove o candidato somente "
            "após o dry-run integral, usando "
            "staging, fingerprint, fsync "
            "e rollback."
        ),
    )

    parser.add_argument(
        "--publication-date",
        metavar="YYYY-MM-DD",
        default=None,
        help=(
            "Obrigatória quando existirem "
            "HTMLs públicos novos."
        ),
    )

    return parser.parse_args()


def main() -> int:

    args = parse_args()

    installed_count = 0

    try:

        result = run_dry_run(
            args
        )

        if args.write:

            installed_count = (
                persist_candidate(
                    args=args,
                    result=result,
                )
            )

    except SynchronizationError as exc:

        print(
            "ERRO:",
            exc,
            file=sys.stderr,
        )

        return (
            2
            if getattr(
                args,
                "check",
                False,
            )
            else 1
        )

    except Exception as exc:

        print(
            "ERRO OPERACIONAL:",
            exc,
            file=sys.stderr,
        )

        return 2

    print(
        "=============================================="
    )

    print(
        "DATADARK — SINCRONIZADOR EDITORIAL V1"
    )

    print(
        "MODO="
        + (
            "CHECK"
            if args.check
            else (
                "WRITE"
                if args.write
                else "DRY_RUN"
            )
        )
    )

    print(
        "=============================================="
    )

    print(
        f"PUBLICOS={result['public_count']}"
    )

    print(
        f"EXISTENTES={result['existing_count']}"
    )

    print(
        f"NOVOS={result['new_count']}"
    )

    print(
        "RASCUNHOS_IGNORADOS="
        f"{result['ignored_count']}"
    )

    for editorial_id, slug in (
        result["allocated"]
    ):

        print(
            f"NOVO={editorial_id}|{slug}"
        )

    print()

    print(
        "CATALOGO_DIVERGENTE="
        + yes_no(
            result["catalog_changed"]
        )
    )

    print(
        "INDICE_DIVERGENTE="
        + yes_no(
            result["index_changed"]
        )
    )

    print(
        "RELACIONADOS_DIVERGENTE="
        + yes_no(
            result["related_changed"]
        )
    )

    print(
        "HTMLS_RENDER_DIVERGENTES="
        f"{result['rendered_changed']}"
    )

    print(
        "SINCRONIZACAO_NECESSARIA="
        + yes_no(
            result[
                "synchronization_needed"
            ]
        )
    )

    if args.write:

        print(
            "WRITE_TRANSACTION="
            + (
                "OK"
                if installed_count
                else "NOOP"
            )
        )

        print(
            "FILES_PROMOTED="
            f"{installed_count}"
        )

        print(
            "REPOSITORY_MODIFIED="
            + yes_no(
                installed_count > 0
            )
        )

    else:

        print(
            "REPOSITORY_MODIFIED=NO"
        )

    print(
        "STATE_TOKEN="
        f"{result['state_token']}"
    )

    if args.check:

        final_result = (
            "ESTADO_DIVERGENTE"
            if result[
                "synchronization_needed"
            ]
            else "ESTADO_SINCRONIZADO"
        )

    elif args.write:

        final_result = (
            "ESTADO_SINCRONIZADO"
            if installed_count
            else "ESTADO_JA_SINCRONIZADO"
        )

    else:

        final_result = (
            "PRONTO_PARA_SINCRONIZACAO"
            if result[
                "synchronization_needed"
            ]
            else "ESTADO_JA_SINCRONIZADO"
        )

    print(
        "RESULTADO="
        + final_result
    )

    if (
        args.check
        and result[
            "synchronization_needed"
        ]
    ):

        return 1

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
