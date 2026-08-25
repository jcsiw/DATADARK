#!/usr/bin/env python3

"""
DATADARK TECNOLOGIA
Base de Conhecimento

ETAPA 3 — Validador de Artigos V1.0

Responsabilidade:
- validar artigos HTML da Base de Conhecimento;
- NÃO alterar arquivos;
- NÃO gerar indice.json;
- NÃO renomear arquivos automaticamente.

Saída:
0 = validação concluída sem erros
1 = um ou mais erros encontrados
2 = erro operacional
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata

from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


SLUG_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*\.html$"
)

REMOTE_URL_RE = re.compile(
    r"^(?:https?:)?//",
    re.IGNORECASE,
)


def slugify_filename(filename: str) -> str:
    """
    Converte um nome para o padrão sugerido da Base.

    Exemplo:
    Áudio Novo.html
    ->
    audio-novo.html
    """

    stem = Path(filename).stem

    normalized = unicodedata.normalize(
        "NFKD",
        stem,
    )

    normalized = "".join(
        char
        for char in normalized
        if not unicodedata.combining(char)
    )

    normalized = normalized.lower()

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    normalized = normalized.strip("-")

    if not normalized:
        normalized = "artigo"

    return f"{normalized}.html"


class ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.html_lang: str | None = None

        self.charset_found = False

        self.meta: dict[str, str] = {}

        self.title_parts: list[str] = []

        self.inside_title = False
        self.inside_body = False
        self.inside_style = False

        self.body_seen = False
        self.body_has_content = False

        self.style_parts: list[str] = []

        self.errors: list[str] = []


    def add_error(
        self,
        message: str,
    ) -> None:

        if message not in self.errors:
            self.errors.append(message)


    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:

        tag = tag.lower()

        attr_map = {
            str(name).lower():
            "" if value is None else str(value)
            for name, value in attrs
        }


        if tag == "html":
            if self.html_lang is None:
                self.html_lang = (
                    attr_map.get("lang", "")
                    .strip()
                )


        if tag == "meta":

            charset = (
                attr_map.get("charset", "")
                .strip()
                .lower()
            )

            if charset in {
                "utf-8",
                "utf8",
            }:
                self.charset_found = True


            http_equiv = (
                attr_map.get(
                    "http-equiv",
                    "",
                )
                .strip()
                .lower()
            )

            content = (
                attr_map.get(
                    "content",
                    "",
                )
                .strip()
            )

            if (
                http_equiv == "content-type"
                and re.search(
                    r"charset\s*=\s*utf-?8",
                    content,
                    re.IGNORECASE,
                )
            ):
                self.charset_found = True


            name = (
                attr_map.get("name", "")
                .strip()
                .lower()
            )

            if name:
                self.meta[name] = content


        if tag == "title":
            self.inside_title = True


        if tag == "style":
            self.inside_style = True


        if tag == "body":
            self.inside_body = True
            self.body_seen = True


        elif self.inside_body:
            self.body_has_content = True


        if "contenteditable" in attr_map:
            self.add_error(
                "atributo contenteditable não é permitido"
            )


        if tag == "script":
            self.add_error(
                "JavaScript não é permitido nos artigos (<script>)"
            )


        if tag == "iframe":
            self.add_error(
                "iframe não é permitido nos artigos"
            )


        if tag in {
            "object",
            "embed",
        }:
            self.add_error(
                f"elemento <{tag}> não é permitido"
            )


        if tag == "form":
            self.add_error(
                "formulários não são permitidos nos artigos"
            )


        if tag == "link":

            rel = (
                attr_map.get("rel", "")
                .strip()
                .lower()
            )

            if "stylesheet" in rel.split():
                self.add_error(
                    "folha CSS externa/local não é permitida "
                    "(<link rel=\"stylesheet\">)"
                )


        if tag in {
            "img",
            "source",
            "audio",
            "video",
        }:

            src = (
                attr_map.get("src", "")
                .strip()
            )

            if (
                src
                and not src.lower().startswith(
                    "data:"
                )
            ):
                self.add_error(
                    f"<{tag}> referencia recurso externo/local: "
                    f"{src[:100]}"
                )


    def handle_startendtag(
        self,
        tag: str,
        attrs,
    ) -> None:

        self.handle_starttag(
            tag,
            attrs,
        )


    def handle_endtag(
        self,
        tag: str,
    ) -> None:

        tag = tag.lower()

        if tag == "title":
            self.inside_title = False

        elif tag == "style":
            self.inside_style = False

        elif tag == "body":
            self.inside_body = False


    def handle_data(
        self,
        data: str,
    ) -> None:

        if self.inside_title:
            self.title_parts.append(data)

        if self.inside_style:
            self.style_parts.append(data)

        if (
            self.inside_body
            and data.strip()
        ):
            self.body_has_content = True


    @property
    def title(self) -> str:

        return re.sub(
            r"\s+",
            " ",
            " ".join(
                self.title_parts
            ),
        ).strip()


    @property
    def style_text(self) -> str:

        return "\n".join(
            self.style_parts
        )


def validate_article(
    path: Path,
) -> tuple[list[str], list[str]]:

    errors: list[str] = []
    warnings: list[str] = []


    def error(
        message: str,
    ) -> None:

        if message not in errors:
            errors.append(message)


    def warning(
        message: str,
    ) -> None:

        if message not in warnings:
            warnings.append(message)


    # --------------------------------------------------
    # NOME DO ARQUIVO
    # --------------------------------------------------

    if not SLUG_RE.fullmatch(
        path.name
    ):

        suggestion = slugify_filename(
            path.name
        )

        error(
            "nome de arquivo inválido; "
            f"sugestão: {suggestion}"
        )


    # --------------------------------------------------
    # TAMANHO / LEITURA
    # --------------------------------------------------

    try:
        size = path.stat().st_size

    except OSError as exc:
        error(
            f"não foi possível obter metadados: {exc}"
        )
        return errors, warnings


    if size == 0:
        error(
            "arquivo vazio"
        )
        return errors, warnings


    try:
        text = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        error(
            "arquivo não está codificado em UTF-8"
        )
        return errors, warnings

    except OSError as exc:
        error(
            f"não foi possível ler o arquivo: {exc}"
        )
        return errors, warnings


    # --------------------------------------------------
    # ESTRUTURA HTML MÍNIMA
    # --------------------------------------------------

    lower = text.lower()


    if not re.search(
        r"<!doctype\s+html(?:\s|>)",
        lower,
    ):
        error(
            "DOCTYPE HTML5 ausente"
        )


    required_patterns = {
        "<html>":
            r"<html\b",

        "</html>":
            r"</html\s*>",

        "<head>":
            r"<head\b",

        "</head>":
            r"</head\s*>",

        "<body>":
            r"<body\b",

        "</body>":
            r"</body\s*>",
    }


    for label, pattern in (
        required_patterns.items()
    ):

        if not re.search(
            pattern,
            lower,
        ):
            error(
                f"estrutura obrigatória ausente: {label}"
            )


    # --------------------------------------------------
    # PARSE DO HTML
    # --------------------------------------------------

    parser = ArticleHTMLParser()

    try:
        parser.feed(text)
        parser.close()

    except Exception as exc:
        error(
            "falha ao interpretar HTML: "
            f"{exc}"
        )

        return errors, warnings


    for parser_error in (
        parser.errors
    ):
        error(parser_error)


    # --------------------------------------------------
    # LANG
    # --------------------------------------------------

    if not parser.html_lang:

        error(
            '<html lang="pt-BR"> ausente'
        )

    elif (
        parser.html_lang
        .lower()
        != "pt-br"
    ):

        error(
            "idioma HTML inválido; "
            'esperado lang="pt-BR"'
        )


    # --------------------------------------------------
    # CHARSET
    # --------------------------------------------------

    if not parser.charset_found:
        error(
            'meta charset="utf-8" ausente'
        )


    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------

    if not parser.title:

        error(
            "<title> ausente ou vazio"
        )


    # --------------------------------------------------
    # BODY
    # --------------------------------------------------

    if not parser.body_seen:

        error(
            "<body> não identificado pelo parser"
        )

    elif not parser.body_has_content:

        error(
            "<body> não possui conteúdo"
        )


    # --------------------------------------------------
    # CSS INCORPORADO
    # --------------------------------------------------

    style_text = parser.style_text


    if re.search(
        r"@import\b",
        style_text,
        re.IGNORECASE,
    ):
        error(
            "CSS @import não é permitido"
        )


    for match in re.finditer(
        r"url\(\s*([^)]+?)\s*\)",
        style_text,
        re.IGNORECASE,
    ):

        value = (
            match.group(1)
            .strip()
            .strip("\"'")
        )

        if not value:
            continue

        if (
            value.lower().startswith(
                "data:"
            )
            or value.startswith("#")
        ):
            continue

        error(
            "CSS referencia recurso externo/local "
            f"via url(): {value[:100]}"
        )


    # --------------------------------------------------
    # METADADOS OPCIONAIS
    # --------------------------------------------------

    optional_meta = (
        (
            "description",
            "meta description ausente",
        ),
        (
            "keywords",
            "meta keywords ausente",
        ),
        (
            "kb-aliases",
            "meta kb-aliases ausente",
        ),
        (
            "kb-category",
            "meta kb-category ausente",
        ),
    )


    for key, message in (
        optional_meta
    ):

        if not (
            parser.meta
            .get(key, "")
            .strip()
        ):
            warning(message)


    return errors, warnings


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
        if path.name.startswith("_")
    ]


    articles = [
        path
        for path in all_html
        if not path.name.startswith("_")
    ]


    return articles, ignored


def detect_case_collisions(
    articles: list[Path],
) -> dict[str, list[Path]]:

    groups: dict[
        str,
        list[Path],
    ] = defaultdict(list)


    for article in articles:
        groups[
            article.name.casefold()
        ].append(article)


    return {
        key: paths
        for key, paths
        in groups.items()
        if len(paths) > 1
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Valida artigos HTML da "
            "Base de Conhecimento DATADARK."
        )
    )

    default_directory = (
        Path(__file__)
        .resolve()
        .parents[2]
        / "base-conhecimento"
        / "artigos"
    )


    parser.add_argument(
        "--directory",
        type=Path,
        default=default_directory,
        help=(
            "Diretório contendo os artigos. "
            "Por padrão usa "
            "base-conhecimento/artigos/."
        ),
    )


    return parser.parse_args()


def main() -> int:

    args = parse_args()

    directory = (
        args.directory
        .expanduser()
        .resolve()
    )


    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Validação de Artigos V1.0"
    )

    print(
        "=" * 42
    )

    print(
        f"Diretório: {directory}"
    )

    print()


    if not directory.exists():

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            "Diretório não existe."
        )

        return 2


    if not directory.is_dir():

        print(
            "ERRO OPERACIONAL:"
        )

        print(
            "O caminho informado não é "
            "um diretório."
        )

        return 2


    articles, ignored = (
        discover_articles(directory)
    )


    collisions = (
        detect_case_collisions(
            articles
        )
    )


    global_errors = 0

    valid_count = 0

    invalid_count = 0

    warning_count = 0


    if collisions:

        print(
            "ERROS DE DUPLICIDADE:"
        )

        for paths in (
            collisions.values()
        ):

            global_errors += 1

            print(
                "  - colisão de nome:"
            )

            for path in paths:
                print(
                    f"      {path.name}"
                )

        print()


    for article in articles:

        errors, warnings = (
            validate_article(
                article
            )
        )


        warning_count += len(
            warnings
        )


        if errors:

            invalid_count += 1

            print(
                f"[ERRO] {article.name}"
            )

            for message in errors:
                print(
                    f"  - {message}"
                )


        else:

            valid_count += 1

            if warnings:

                print(
                    f"[OK/AVISO] "
                    f"{article.name}"
                )

            else:

                print(
                    f"[OK] {article.name}"
                )


        for message in warnings:
            print(
                f"  - AVISO: {message}"
            )


        if errors or warnings:
            print()


    print(
        "-" * 42
    )

    print(
        f"Artigos encontrados: "
        f"{len(articles)}"
    )

    print(
        f"Artigos válidos: "
        f"{valid_count}"
    )

    print(
        f"Artigos com erro: "
        f"{invalid_count}"
    )

    print(
        f"Avisos: "
        f"{warning_count}"
    )

    print(
        f"Rascunhos ignorados (_*.html): "
        f"{len(ignored)}"
    )


    total_errors = (
        invalid_count
        + global_errors
    )


    if total_errors:

        print()

        print(
            "RESULTADO: FALHA"
        )

        print(
            "A publicação deve ser "
            "interrompida até a correção "
            "dos erros."
        )

        return 1


    print()

    print(
        "RESULTADO: VALIDAÇÃO OK"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
