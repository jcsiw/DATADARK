#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 8 — Gerador Oficial de Artigos V1.0
Fase: dry-run seguro e persistência transacional explícita.

Responsabilidades:
- carregar entrada editorial JSON de forma estrita;
- validar categoria pela taxonomia oficial;
- gerar slug pelo algoritmo oficial congelado;
- materializar o Template Oficial de Artigo V1;
- escapar conteúdo editorial;
- recusar colisões;
- validar o conjunto completo de artigos;
- gerar e verificar índice temporário;
- manter dry-run como comportamento padrão;
- gravar somente mediante --write;
- promover artigo e índice atomicamente;
- executar rollback em caso de falha pós-gravação.

Saída:
0 = operação concluída com sucesso
1 = entrada ou conteúdo inválido
2 = erro operacional
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

from taxonomia import (
    TaxonomyError,
    load_taxonomy,
)


SCRIPT_DIR = Path(__file__).resolve().parent

REPOSITORY_ROOT = (
    SCRIPT_DIR
    .parents[1]
)

ARTICLES_DIR = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "artigos"
)

INDEX_PATH = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

CATEGORIES_PATH = (
    REPOSITORY_ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

TEMPLATE_PATH = (
    SCRIPT_DIR
    / "templates"
    / "artigo-v1.html"
)

VALIDATOR_PATH = (
    SCRIPT_DIR
    / "validar-artigos.py"
)

INDEXER_PATH = (
    SCRIPT_DIR
    / "gerar-indice.py"
)


CATALOG_PATH = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
)


CATALOG_VALIDATOR_PATH = (
    SCRIPT_DIR
    / "validar-catalogo-editorial.py"
)


PUBLICATION_TIMEZONE = (
    "America/Sao_Paulo"
)


CANONICAL_ARTICLE_BASE = (
    "https://datadark.com.br/"
    "base-conhecimento/artigos"
)


SITE_NAME = (
    "DATADARK Tecnologia"
)


SITE_URL = (
    "https://datadark.com.br/"
)


TEMPLATE_SHA256 = (
    "3ac8cedd4117df31cb1f94f06e6f2020432531f994582f7a15c4808c98a4c495"
)


EXPECTED_FIELDS = {
    "title",
    "category_id",
    "description",
    "keywords",
    "aliases",
    "overview",
    "diagnosis",
    "procedure_steps",
    "validation",
    "notes",
}


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


PLACEHOLDER_RE = re.compile(
    r"@@[A-Z_]+@@"
)


class ArticleCreationError(
    RuntimeError
):
    """Erro editorial que bloqueia a criação."""


def _without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:

    result: dict[str, Any] = {}

    for key, value in pairs:

        if key in result:
            raise ArticleCreationError(
                "chave JSON duplicada: "
                f"{key}"
            )

        result[key] = value

    return result


def collapse_whitespace(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def require_text(
    value: Any,
    field: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise ArticleCreationError(
            f"{field} deve ser texto"
        )

    normalized = collapse_whitespace(
        value
    )

    if not normalized:
        raise ArticleCreationError(
            f"{field} não pode ser vazio"
        )

    if PLACEHOLDER_RE.search(
        normalized
    ):
        raise ArticleCreationError(
            f"{field} contém marcador "
            "reservado do template"
        )

    return normalized


def require_text_list(
    value: Any,
    field: str,
    *,
    forbid_commas: bool = False,
) -> list[str]:

    if not isinstance(
        value,
        list,
    ):
        raise ArticleCreationError(
            f"{field} deve ser lista"
        )

    if not value:
        raise ArticleCreationError(
            f"{field} não pode ser vazio"
        )

    result: list[str] = []
    seen: set[str] = set()

    for position, raw in enumerate(
        value,
        start=1,
    ):

        item = require_text(
            raw,
            f"{field}[{position}]",
        )

        if (
            forbid_commas
            and "," in item
        ):
            raise ArticleCreationError(
                f"{field}[{position}] "
                "não pode conter vírgula"
            )

        key = item.casefold()

        if key in seen:
            raise ArticleCreationError(
                f"{field} contém item "
                f"duplicado: {item}"
            )

        seen.add(key)

        result.append(
            item
        )

    return result


def load_input(
    path: Path,
) -> dict[str, Any]:

    try:

        raw_text = path.read_text(
            encoding="utf-8"
        )

    except FileNotFoundError as exc:

        raise ArticleCreationError(
            f"arquivo de entrada não encontrado: "
            f"{path}"
        ) from exc

    except UnicodeDecodeError as exc:

        raise ArticleCreationError(
            "arquivo de entrada não é "
            "UTF-8 válido"
        ) from exc

    except OSError as exc:

        raise ArticleCreationError(
            f"falha ao ler entrada: {exc}"
        ) from exc


    try:

        data = json.loads(
            raw_text,
            object_pairs_hook=(
                _without_duplicate_keys
            ),
        )

    except json.JSONDecodeError as exc:

        raise ArticleCreationError(
            "JSON inválido: "
            f"linha {exc.lineno}, "
            f"coluna {exc.colno}: "
            f"{exc.msg}"
        ) from exc


    if not isinstance(
        data,
        dict,
    ):
        raise ArticleCreationError(
            "raiz da entrada deve ser "
            "objeto JSON"
        )


    actual = set(
        data
    )

    if actual != EXPECTED_FIELDS:

        missing = sorted(
            EXPECTED_FIELDS - actual
        )

        extra = sorted(
            actual - EXPECTED_FIELDS
        )

        details: list[str] = []

        if missing:
            details.append(
                "ausentes="
                + ",".join(missing)
            )

        if extra:
            details.append(
                "extras="
                + ",".join(extra)
            )

        raise ArticleCreationError(
            "estrutura da entrada inválida: "
            + "; ".join(details)
        )


    return {
        "title":
            require_text(
                data["title"],
                "title",
            ),

        "category_id":
            require_text(
                data["category_id"],
                "category_id",
            ),

        "description":
            require_text(
                data["description"],
                "description",
            ),

        "keywords":
            require_text_list(
                data["keywords"],
                "keywords",
                forbid_commas=True,
            ),

        "aliases":
            require_text_list(
                data["aliases"],
                "aliases",
                forbid_commas=True,
            ),

        "overview":
            require_text(
                data["overview"],
                "overview",
            ),

        "diagnosis":
            require_text(
                data["diagnosis"],
                "diagnosis",
            ),

        "procedure_steps":
            require_text_list(
                data["procedure_steps"],
                "procedure_steps",
            ),

        "validation":
            require_text(
                data["validation"],
                "validation",
            ),

        "notes":
            require_text(
                data["notes"],
                "notes",
            ),
    }


def load_official_slugify():

    module_name = (
        "_datadark_validar_artigos"
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            module_name,
            VALIDATOR_PATH,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise ArticleCreationError(
            "não foi possível carregar "
            "o algoritmo oficial de slug"
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

    slugify = getattr(
        module,
        "slugify_filename",
        None,
    )

    if not callable(
        slugify
    ):
        raise ArticleCreationError(
            "slugify_filename não localizado "
            "no validador oficial"
        )

    return slugify


def slug_for_title(
    title: str,
) -> str:

    slugify = (
        load_official_slugify()
    )

    filename = slugify(
        f"{title}.html"
    )

    if not isinstance(
        filename,
        str,
    ):
        raise ArticleCreationError(
            "algoritmo de slug retornou "
            "valor inválido"
        )

    return filename


def template_text() -> str:

    try:

        raw = TEMPLATE_PATH.read_bytes()

    except OSError as exc:

        raise ArticleCreationError(
            f"falha ao ler template: {exc}"
        ) from exc


    digest = hashlib.sha256(
        raw
    ).hexdigest()

    if digest != TEMPLATE_SHA256:

        raise ArticleCreationError(
            "Template Oficial V1 difere "
            "da assinatura congelada"
        )


    try:

        text = raw.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:

        raise ArticleCreationError(
            "Template Oficial V1 "
            "não é UTF-8 válido"
        ) from exc


    for placeholder, expected in (
        PLACEHOLDER_COUNTS.items()
    ):

        actual = text.count(
            placeholder
        )

        if actual != expected:

            raise ArticleCreationError(
                f"{placeholder}: "
                f"esperado={expected}; "
                f"encontrado={actual}"
            )


    return text


def escape_text(
    value: str,
) -> str:

    return html.escape(
        value,
        quote=False,
    )


def escape_attribute(
    value: str,
) -> str:

    return html.escape(
        value,
        quote=True,
    )


def canonical_url_for_filename(
    filename: str,
) -> str:

    if not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*\.html",
        filename,
    ):
        raise ArticleCreationError(
            "filename inválido para URL canônica: "
            f"{filename!r}"
        )

    return (
        f"{CANONICAL_ARTICLE_BASE}/"
        f"{filename}"
    )


def build_seo_json_ld(
    data: dict[str, Any],
    canonical_url: str,
) -> str:

    payload = {
        "@context":
            "https://schema.org",

        "@type":
            "TechArticle",

        "headline":
            data["title"],

        "description":
            data["description"],

        "inLanguage":
            "pt-BR",

        "url":
            canonical_url,

        "mainEntityOfPage": {
            "@type":
                "WebPage",

            "@id":
                canonical_url,
        },

        "publisher": {
            "@type":
                "Organization",

            "name":
                SITE_NAME,

            "url":
                SITE_URL,
        },
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return (
        serialized
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def render_article(
    data: dict[str, Any],
    category_label: str,
    filename: str,
) -> str:

    template = template_text()

    canonical_url = (
        canonical_url_for_filename(
            filename
        )
    )

    seo_json_ld = (
        build_seo_json_ld(
            data,
            canonical_url,
        )
    )


    procedure_html = (
        "\n              ".join(
            (
                "<li>"
                + escape_text(step)
                + "</li>"
            )
            for step in data[
                "procedure_steps"
            ]
        )
    )


    replacements = {
        "@@TITLE@@":
            escape_text(
                data["title"]
            ),

        "@@TITLE_ATTRIBUTE@@":
            escape_attribute(
                data["title"]
            ),

        "@@DESCRIPTION@@":
            escape_text(
                data["description"]
            ),

        "@@DESCRIPTION_ATTRIBUTE@@":
            escape_attribute(
                data["description"]
            ),

        "@@KEYWORDS@@":
            escape_attribute(
                ", ".join(
                    data["keywords"]
                )
            ),

        "@@ALIASES@@":
            escape_attribute(
                ", ".join(
                    data["aliases"]
                )
            ),

        "@@CATEGORY_ID@@":
            escape_attribute(
                data["category_id"]
            ),

        "@@CATEGORY_LABEL@@":
            escape_text(
                category_label
            ),

        "@@CANONICAL_URL@@":
            escape_attribute(
                canonical_url
            ),

        "@@SEO_JSON_LD@@":
            seo_json_ld,

        "@@OVERVIEW@@":
            escape_text(
                data["overview"]
            ),

        "@@DIAGNOSIS@@":
            escape_text(
                data["diagnosis"]
            ),

        "@@PROCEDURE_STEPS@@":
            procedure_html,

        "@@VALIDATION@@":
            escape_text(
                data["validation"]
            ),

        "@@NOTES@@":
            escape_text(
                data["notes"]
            ),
    }


    rendered = template


    for placeholder, value in (
        replacements.items()
    ):

        rendered = rendered.replace(
            placeholder,
            value,
        )


    residual = PLACEHOLDER_RE.findall(
        rendered
    )

    if residual:

        raise ArticleCreationError(
            "materialização preservou "
            "placeholder(s): "
            + ", ".join(
                sorted(set(residual))
            )
        )


    return rendered


def run_command(
    command: list[str],
    label: str,
) -> str:

    environment = os.environ.copy()

    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"


    try:

        result = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    except OSError as exc:

        raise ArticleCreationError(
            f"{label}: falha operacional: "
            f"{exc}"
        ) from exc


    if result.returncode != 0:

        details = (
            result.stdout
            + result.stderr
        ).strip()

        raise ArticleCreationError(
            f"{label} falhou "
            f"(status={result.returncode})"
            + (
                f":\n{details}"
                if details
                else ""
            )
        )


    return result.stdout


def require_zero_warnings(
    output: str,
    label: str,
) -> None:

    if not re.search(
        r"^Avisos:\s*0\s*$",
        output,
        re.MULTILINE,
    ):
        raise ArticleCreationError(
            f"{label} não confirmou "
            "Avisos: 0"
        )


def ensure_content_paths_clean() -> None:

    monitored = (
        "base-conhecimento/artigos",
        "base-conhecimento/data/indice.json",
        "base-conhecimento/data/categorias.json",
        (
            "scripts/base-conhecimento/"
            "templates/artigo-v1.html"
        ),
    )


    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain",
            "--",
            *monitored,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


    if result.returncode != 0:

        raise ArticleCreationError(
            "não foi possível verificar "
            "estado Git da Base"
        )


    if result.stdout.strip():

        raise ArticleCreationError(
            "Base de Conhecimento possui "
            "alterações locais nos caminhos "
            "operacionais monitorados"
        )


def ensure_official_index_current() -> None:

    output = run_command(
        [
            sys.executable,
            str(INDEXER_PATH),
            "--articles-dir",
            str(ARTICLES_DIR),
            "--output",
            str(INDEX_PATH),
            "--categories",
            str(CATEGORIES_PATH),
            "--check",
        ],
        "verificação do índice oficial",
    )

    require_zero_warnings(
        output,
        "índice oficial",
    )


def official_state_fingerprint() -> str:
    """
    Assinatura do estado oficial consumido pela
    transação.

    Protege:
    - template;
    - taxonomia;
    - índice;
    - Catálogo Editorial;
    - artigos HTML.

    Detecta alterações concorrentes entre o
    dry-run e a promoção definitiva.
    """

    paths = [
        TEMPLATE_PATH,
        CATEGORIES_PATH,
        INDEX_PATH,
        CATALOG_PATH,
    ]

    paths.extend(
        sorted(
            ARTICLES_DIR.glob(
                "*.html"
            ),
            key=lambda path:
                path.name.casefold(),
        )
    )


    digest = hashlib.sha256()


    for path in paths:

        try:

            if not path.is_file():
                raise ArticleCreationError(
                    "artefato oficial ausente: "
                    f"{path}"
                )

            content = path.read_bytes()

        except OSError as exc:

            raise ArticleCreationError(
                "falha ao calcular estado "
                f"oficial: {path}: {exc}"
            ) from exc


        try:

            relative = (
                path
                .relative_to(
                    REPOSITORY_ROOT
                )
                .as_posix()
            )

        except ValueError:

            relative = str(
                path.resolve()
            )


        encoded_path = (
            relative.encode(
                "utf-8"
            )
        )


        digest.update(
            len(encoded_path)
            .to_bytes(
                8,
                "big",
            )
        )

        digest.update(
            encoded_path
        )

        digest.update(
            len(content)
            .to_bytes(
                8,
                "big",
            )
        )

        digest.update(
            content
        )


    return digest.hexdigest()


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
    directory: Path,
    prefix: str,
    content: bytes,
    mode: int,
) -> Path:

    descriptor, temp_name = (
        tempfile.mkstemp(
            prefix=prefix,
            suffix=".tmp",
            dir=directory,
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


def restore_index_atomic(
    content: bytes,
    mode: int,
) -> None:

    staged = create_staged_file(
        INDEX_PATH.parent,
        f".{INDEX_PATH.name}.rollback.",
        content,
        mode,
    )


    try:

        os.replace(
            staged,
            INDEX_PATH,
        )

        fsync_directory(
            INDEX_PATH.parent
        )

    finally:

        staged.unlink(
            missing_ok=True
        )


def ensure_catalog_path_clean() -> None:
    """
    O Catálogo Editorial oficial não pode possuir
    alteração local pendente antes da operação.
    """

    try:
        relative = (
            CATALOG_PATH
            .relative_to(
                REPOSITORY_ROOT
            )
            .as_posix()
        )

    except ValueError as exc:

        raise ArticleCreationError(
            "catalogo.json está fora do "
            "repositório oficial."
        ) from exc


    try:
        completed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--",
                relative,
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    except OSError as exc:

        raise ArticleCreationError(
            "não foi possível verificar o "
            "estado Git do Catálogo Editorial: "
            f"{exc}"
        ) from exc


    if completed.returncode != 0:

        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or (
                "git status retornou "
                f"{completed.returncode}"
            )
        )

        raise ArticleCreationError(
            "falha ao verificar o Catálogo "
            f"Editorial no Git: {detail}"
        )


    if completed.stdout.strip():

        raise ArticleCreationError(
            "Catálogo Editorial possui "
            "alteração local pendente; "
            "operação cancelada."
        )


def ensure_official_catalog_current() -> None:
    """
    Exige que o Catálogo Editorial oficial esteja
    consistente com os artigos e o índice atuais.
    """

    run_command(
        [
            sys.executable,
            str(
                CATALOG_VALIDATOR_PATH
            ),
            "--catalog",
            str(
                CATALOG_PATH
            ),
            "--articles-dir",
            str(
                ARTICLES_DIR
            ),
            "--index",
            str(
                INDEX_PATH
            ),
            "--categories",
            str(
                CATEGORIES_PATH
            ),
        ],
        "verificação do Catálogo Editorial",
    )


def resolve_publication_date(
    value: str | None,
) -> str:
    """
    Resolve a data editorial em YYYY-MM-DD.

    Se não informada pela CLI, utiliza a data
    corrente em America/Sao_Paulo.
    """

    if value is None:

        try:
            timezone = ZoneInfo(
                PUBLICATION_TIMEZONE
            )

        except ZoneInfoNotFoundError as exc:

            raise ArticleCreationError(
                "timezone editorial indisponível: "
                f"{PUBLICATION_TIMEZONE}"
            ) from exc


        return (
            datetime.now(
                timezone
            )
            .date()
            .isoformat()
        )


    if not isinstance(
        value,
        str,
    ):

        raise ArticleCreationError(
            "publication-date deve ser string "
            "YYYY-MM-DD."
        )


    try:
        parsed = date.fromisoformat(
            value
        )

    except ValueError as exc:

        raise ArticleCreationError(
            "publication-date inválida: "
            f"{value!r}"
        ) from exc


    if parsed.isoformat() != value:

        raise ArticleCreationError(
            "publication-date deve usar "
            "YYYY-MM-DD canônico."
        )


    return value


def load_catalog_for_update() -> dict[str, Any]:
    """
    Carrega o Catálogo já homologado pelo
    validador oficial.
    """

    try:
        data = json.loads(
            CATALOG_PATH.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:

        raise ArticleCreationError(
            "não foi possível carregar o "
            f"Catálogo Editorial: {exc}"
        ) from exc


    if not isinstance(
        data,
        dict,
    ):

        raise ArticleCreationError(
            "Catálogo Editorial deve possuir "
            "objeto JSON na raiz."
        )


    if data.get(
        "version"
    ) != 1:

        raise ArticleCreationError(
            "versão inesperada do "
            "Catálogo Editorial."
        )


    articles = data.get(
        "articles"
    )


    if not isinstance(
        articles,
        list,
    ):

        raise ArticleCreationError(
            "articles inválido no "
            "Catálogo Editorial."
        )


    return data


def next_editorial_id(
    catalog: dict[str, Any],
) -> str:

    numbers: list[int] = []


    for article in catalog[
        "articles"
    ]:

        if not isinstance(
            article,
            dict,
        ):

            raise ArticleCreationError(
                "registro editorial inválido."
            )


        article_id = article.get(
            "id"
        )


        if not isinstance(
            article_id,
            str,
        ):

            raise ArticleCreationError(
                "id editorial inválido."
            )


        match = re.fullmatch(
            r"DD-KB-([0-9]{6})",
            article_id,
        )


        if match is None:

            raise ArticleCreationError(
                "id editorial fora do "
                f"contrato V1: {article_id!r}"
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

        raise ArticleCreationError(
            "sequência editorial DD-KB "
            "esgotada."
        )


    return (
        f"DD-KB-{number:06d}"
    )


def build_catalog_candidate(
    result: dict[str, Any],
    publication_date: str,
) -> tuple[str, bytes]:
    """
    Constrói o Catálogo candidato sem modificar
    o arquivo oficial.
    """

    catalog = (
        load_catalog_for_update()
    )


    editorial_id = (
        next_editorial_id(
            catalog
        )
    )


    record = {
        "id":
            editorial_id,
        "title":
            result["title"],
        "slug":
            result["slug"],
        "category_id":
            result["category_id"],
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


    catalog[
        "articles"
    ].append(
        record
    )


    content = (
        json.dumps(
            catalog,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


    return (
        editorial_id,
        content,
    )


def validate_catalog_candidate(
    result: dict[str, Any],
) -> None:
    """
    Homologa artigo + índice + catálogo candidatos
    em ambiente temporário.
    """

    with tempfile.TemporaryDirectory(
        prefix=(
            "datadark-catalogo-"
            "candidate-"
        )
    ) as temp_name:

        temp_root = Path(
            temp_name
        )

        temp_articles = (
            temp_root
            / "artigos"
        )

        temp_articles.mkdir(
            parents=True,
            exist_ok=True,
        )


        for source in sorted(
            ARTICLES_DIR.glob(
                "*.html"
            ),
            key=lambda item:
                item.name.casefold(),
        ):

            shutil.copy2(
                source,
                temp_articles
                / source.name,
            )


        (
            temp_articles
            / result["filename"]
        ).write_bytes(
            result[
                "article_bytes"
            ]
        )


        temp_index = (
            temp_root
            / "indice.json"
        )

        temp_index.write_bytes(
            result[
                "index_bytes"
            ]
        )


        temp_catalog = (
            temp_root
            / "catalogo.json"
        )

        temp_catalog.write_bytes(
            result[
                "catalog_bytes"
            ]
        )


        run_command(
            [
                sys.executable,
                str(
                    CATALOG_VALIDATOR_PATH
                ),
                "--catalog",
                str(
                    temp_catalog
                ),
                "--articles-dir",
                str(
                    temp_articles
                ),
                "--index",
                str(
                    temp_index
                ),
                "--categories",
                str(
                    CATEGORIES_PATH
                ),
            ],
            (
                "validação do Catálogo "
                "Editorial candidato"
            ),
        )


def restore_file_atomic(
    path: Path,
    content: bytes,
    mode: int,
) -> None:
    """
    Restaura arquivo por staged file + os.replace.
    """

    staged = create_staged_file(
        path.parent,
        f".{path.name}.restore.",
        content,
        mode,
    )


    try:

        os.replace(
            staged,
            path,
        )

        fsync_directory(
            path.parent
        )

    finally:

        staged.unlink(
            missing_ok=True
        )


def persist_candidate(
    result: dict[str, Any],
) -> None:
    """
    Promove artigo, índice e Catálogo Editorial.

    Não existe atomicidade multi-arquivo nativa.
    A operação utiliza:
    - staged files;
    - os.replace individual;
    - fingerprint concorrente;
    - validação pós-gravação;
    - rollback integral.
    """

    ensure_content_paths_clean()

    ensure_catalog_path_clean()


    target = result[
        "target"
    ]


    if target.exists():

        raise ArticleCreationError(
            "artigo já existe: "
            f"{target.relative_to(REPOSITORY_ROOT)}"
        )


    current_state = (
        official_state_fingerprint()
    )


    if (
        current_state
        != result["state_token"]
    ):

        raise ArticleCreationError(
            "estado oficial mudou após o "
            "dry-run; operação cancelada"
        )


    try:

        original_index = (
            INDEX_PATH.read_bytes()
        )

        original_index_mode = (
            stat.S_IMODE(
                INDEX_PATH
                .stat()
                .st_mode
            )
        )

        original_catalog = (
            CATALOG_PATH.read_bytes()
        )

        original_catalog_mode = (
            stat.S_IMODE(
                CATALOG_PATH
                .stat()
                .st_mode
            )
        )

    except OSError as exc:

        raise ArticleCreationError(
            "não foi possível preservar "
            "indice.json/catalogo.json: "
            f"{exc}"
        ) from exc


    article_staged: Path | None = None

    index_staged: Path | None = None

    catalog_staged: Path | None = None

    article_installed = False

    index_installed = False

    catalog_installed = False


    try:

        article_staged = (
            create_staged_file(
                ARTICLES_DIR,
                f".{target.name}.",
                result[
                    "article_bytes"
                ],
                0o644,
            )
        )


        index_staged = (
            create_staged_file(
                INDEX_PATH.parent,
                f".{INDEX_PATH.name}.",
                result[
                    "index_bytes"
                ],
                original_index_mode,
            )
        )


        catalog_staged = (
            create_staged_file(
                CATALOG_PATH.parent,
                f".{CATALOG_PATH.name}.",
                result[
                    "catalog_bytes"
                ],
                original_catalog_mode,
            )
        )


        if (
            official_state_fingerprint()
            != result["state_token"]
        ):

            raise ArticleCreationError(
                "estado oficial mudou durante "
                "a preparação da transação"
            )


        os.replace(
            article_staged,
            target,
        )

        article_staged = None

        article_installed = True

        fsync_directory(
            ARTICLES_DIR
        )


        os.replace(
            index_staged,
            INDEX_PATH,
        )

        index_staged = None

        index_installed = True

        fsync_directory(
            INDEX_PATH.parent
        )


        os.replace(
            catalog_staged,
            CATALOG_PATH,
        )

        catalog_staged = None

        catalog_installed = True

        fsync_directory(
            CATALOG_PATH.parent
        )


        validator_output = (
            run_command(
                [
                    sys.executable,
                    str(
                        VALIDATOR_PATH
                    ),
                    "--directory",
                    str(
                        ARTICLES_DIR
                    ),
                    "--categories",
                    str(
                        CATEGORIES_PATH
                    ),
                ],
                "validador pós-gravação",
            )
        )


        require_zero_warnings(
            validator_output,
            "validador pós-gravação",
        )


        check_output = (
            run_command(
                [
                    sys.executable,
                    str(
                        INDEXER_PATH
                    ),
                    "--articles-dir",
                    str(
                        ARTICLES_DIR
                    ),
                    "--output",
                    str(
                        INDEX_PATH
                    ),
                    "--categories",
                    str(
                        CATEGORIES_PATH
                    ),
                    "--check",
                ],
                "check pós-gravação",
            )
        )


        require_zero_warnings(
            check_output,
            "check pós-gravação",
        )


        run_command(
            [
                sys.executable,
                str(
                    CATALOG_VALIDATOR_PATH
                ),
                "--catalog",
                str(
                    CATALOG_PATH
                ),
                "--articles-dir",
                str(
                    ARTICLES_DIR
                ),
                "--index",
                str(
                    INDEX_PATH
                ),
                "--categories",
                str(
                    CATEGORIES_PATH
                ),
            ],
            (
                "validador editorial "
                "pós-gravação"
            ),
        )


    except Exception as exc:

        rollback_errors: list[str] = []


        if catalog_installed:

            try:

                restore_file_atomic(
                    CATALOG_PATH,
                    original_catalog,
                    original_catalog_mode,
                )

            except Exception as rollback_exc:

                rollback_errors.append(
                    "catalogo.json: "
                    f"{rollback_exc}"
                )


        if index_installed:

            try:

                restore_file_atomic(
                    INDEX_PATH,
                    original_index,
                    original_index_mode,
                )

            except Exception as rollback_exc:

                rollback_errors.append(
                    "indice.json: "
                    f"{rollback_exc}"
                )


        if (
            article_installed
            and target.exists()
        ):

            try:

                target.unlink()

                fsync_directory(
                    ARTICLES_DIR
                )

            except Exception as rollback_exc:

                rollback_errors.append(
                    "artigo: "
                    f"{rollback_exc}"
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

        if article_staged is not None:

            article_staged.unlink(
                missing_ok=True
            )


        if index_staged is not None:

            index_staged.unlink(
                missing_ok=True
            )


        if catalog_staged is not None:

            catalog_staged.unlink(
                missing_ok=True
            )


def _dry_run_article_index(
    data: dict[str, Any],
) -> dict[str, Any]:

    ensure_content_paths_clean()

    ensure_official_index_current()


    state_token = (
        official_state_fingerprint()
    )


    try:

        taxonomy = load_taxonomy(
            CATEGORIES_PATH
        )

        category = (
            taxonomy.resolve_category(
                data["category_id"]
            )
        )

    except TaxonomyError as exc:

        raise ArticleCreationError(
            str(exc)
        ) from exc


    filename = slug_for_title(
        data["title"]
    )

    target = (
        ARTICLES_DIR
        / filename
    )


    if target.exists():

        raise ArticleCreationError(
            "artigo já existe: "
            f"{target.relative_to(REPOSITORY_ROOT)}"
        )


    rendered = render_article(
        data,
        category.label,
        filename,
    )


    with tempfile.TemporaryDirectory(
        prefix="datadark-kb-create-"
    ) as temporary:

        temporary_root = Path(
            temporary
        )

        temporary_articles = (
            temporary_root
            / "artigos"
        )

        temporary_articles.mkdir()


        for existing in sorted(
            ARTICLES_DIR.glob(
                "*.html"
            ),
            key=lambda path:
                path.name.casefold(),
        ):

            shutil.copy2(
                existing,
                temporary_articles
                / existing.name,
            )


        candidate = (
            temporary_articles
            / filename
        )

        candidate.write_text(
            rendered,
            encoding="utf-8",
        )


        validator_output = run_command(
            [
                sys.executable,
                str(VALIDATOR_PATH),
                "--directory",
                str(temporary_articles),
                "--categories",
                str(CATEGORIES_PATH),
            ],
            "validador oficial",
        )

        require_zero_warnings(
            validator_output,
            "validador oficial",
        )


        temporary_index = (
            temporary_root
            / "indice.json"
        )


        generator_output = run_command(
            [
                sys.executable,
                str(INDEXER_PATH),
                "--articles-dir",
                str(temporary_articles),
                "--output",
                str(temporary_index),
                "--categories",
                str(CATEGORIES_PATH),
            ],
            "gerador oficial de índice",
        )

        require_zero_warnings(
            generator_output,
            "gerador oficial de índice",
        )


        check_output = run_command(
            [
                sys.executable,
                str(INDEXER_PATH),
                "--articles-dir",
                str(temporary_articles),
                "--output",
                str(temporary_index),
                "--categories",
                str(CATEGORIES_PATH),
                "--check",
            ],
            "check do índice temporário",
        )

        require_zero_warnings(
            check_output,
            "check do índice temporário",
        )


        try:

            index_data = json.loads(
                temporary_index.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:

            raise ArticleCreationError(
                "índice temporário inválido"
            ) from exc


        matches = [
            entry
            for entry in index_data
            if entry.get("slug")
            == Path(filename).stem
        ]


        if len(matches) != 1:

            raise ArticleCreationError(
                "artigo materializado não "
                "aparece exatamente uma vez "
                "no índice temporário"
            )


        if (
            official_state_fingerprint()
            != state_token
        ):

            raise ArticleCreationError(
                "estado oficial mudou durante "
                "o dry-run"
            )


        try:

            index_bytes = (
                temporary_index
                .read_bytes()
            )

        except OSError as exc:

            raise ArticleCreationError(
                "não foi possível preservar "
                "o índice temporário"
            ) from exc


        return {
            "title":
                data["title"],

            "filename":
                filename,

            "slug":
                Path(filename).stem,

            "category_id":
                category.id,

            "category_label":
                category.label,

            "target":
                target,

            "articles_after":
                len(index_data),

            "article_bytes":
                rendered.encode(
                    "utf-8"
                ),

            "index_bytes":
                index_bytes,

            "state_token":
                state_token,
        }


def dry_run(
    data: dict[str, Any],
    publication_date: str | None = None,
) -> dict[str, Any]:
    """
    Dry-run integrado:

    artigo candidato
    + indice.json candidato
    + catalogo.json candidato

    Nenhum artefato oficial é modificado.
    """

    ensure_catalog_path_clean()

    ensure_official_catalog_current()


    result = (
        _dry_run_article_index(
            data
        )
    )


    resolved_date = (
        resolve_publication_date(
            publication_date
        )
    )


    editorial_id, catalog_bytes = (
        build_catalog_candidate(
            result,
            resolved_date,
        )
    )


    integrated = {
        **result,
        "editorial_id":
            editorial_id,
        "publication_date":
            resolved_date,
        "catalog_bytes":
            catalog_bytes,
    }


    validate_catalog_candidate(
        integrated
    )


    if (
        official_state_fingerprint()
        != result["state_token"]
    ):

        raise ArticleCreationError(
            "estado oficial mudou durante "
            "o dry-run integrado"
        )


    return integrated


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "Materializa e valida um novo "
            "artigo DATADARK. Por padrão "
            "executa dry-run; a gravação "
            "exige --write."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help=(
            "Arquivo JSON contendo os dados "
            "editoriais do artigo."
        ),
    )

    parser.add_argument(
        "--write",
        action="store_true",
        help=(
            "Grava artigo e indice.json somente "
            "após todas as validações. "
            "Sem esta opção, executa dry-run."
        ),
    )


    parser.add_argument(
        "--publication-date",
        metavar="YYYY-MM-DD",
        default=None,
        help=(
            "Data editorial da publicação. "
            "Quando omitida, usa a data corrente "
            "em America/Sao_Paulo."
        ),
    )


    return parser.parse_args()


def main() -> int:

    args = parse_args()


    try:

        data = load_input(
            args.input
        )

        result = dry_run(
            data,
            publication_date=
                args.publication_date,
        )


        if args.write:

            persist_candidate(
                result
            )

    except ArticleCreationError as exc:

        print(
            "ERRO:",
            exc,
            file=sys.stderr,
        )

        return 1

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
        "DATADARK — GERADOR OFICIAL DE ARTIGOS"
    )

    print(
        "MODO="
        + (
            "WRITE"
            if args.write
            else "DRY_RUN"
        )
    )

    print(
        "=============================================="
    )

    print(
        f"TITLE={result['title']}"
    )

    print(
        f"SLUG={result['slug']}"
    )

    print(
        f"CATEGORY_ID={result['category_id']}"
    )

    print(
        f"CATEGORY={result['category_label']}"
    )

    print(
        "ARTICLE_TARGET="
        + str(
            result["target"]
            .relative_to(
                REPOSITORY_ROOT
            )
        )
    )

    print(
        f"ARTICLES_AFTER="
        f"{result['articles_after']}"
    )

    print()
    print(
        "VALIDATOR=OK"
    )

    print(
        "INDEX_GENERATOR=OK"
    )

    print(
        "INDEX_CHECK=OK"
    )

    if args.write:

        print(
            "WRITE_TRANSACTION=OK"
        )

        print(
            "REPOSITORY_MODIFIED=YES"
        )

        print(
            "RESULTADO=ARTIGO_CRIADO"
        )

    else:

        print(
            "REPOSITORY_MODIFIED=NO"
        )

        print(
            "RESULTADO=PRONTO_PARA_GRAVACAO"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
