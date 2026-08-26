#!/usr/bin/env python3

"""
DATADARK Tecnologia
Base de Conhecimento

Testes permanentes do Renderizador Estático
de Artigos Relacionados V1.

ETAPA 8.6.3D

A suíte:
- trabalha exclusivamente em diretórios temporários;
- não modifica artigos oficiais;
- não modifica o Template Oficial;
- não recalcula ranking;
- valida migração do layout legado;
- valida topologia visual;
- valida idempotência byte a byte;
- valida fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

SCRIPT_DIR = (
    ROOT
    / "scripts"
    / "base-conhecimento"
)

RENDERER = (
    SCRIPT_DIR
    / "renderizar-relacionados.py"
)

TEMPLATE = (
    SCRIPT_DIR
    / "templates"
    / "artigo-v1.html"
)

ARTICLES_DIR = (
    ROOT
    / "base-conhecimento"
    / "artigos"
)

INDEX = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "indice.json"
)

RELATED = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "relacionados.json"
)

CATEGORIES = (
    ROOT
    / "base-conhecimento"
    / "data"
    / "categorias.json"
)

CATALOG = (
    SCRIPT_DIR
    / "editorial"
    / "catalogo.json"
)


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


errors = 0


def require(
    condition: bool,
    label: str,
) -> None:

    global errors

    if condition:
        print(
            f"[OK] {label}"
        )
    else:
        print(
            f"[ERRO] {label}"
        )
        errors += 1


def run(
    args: list[str],
) -> subprocess.CompletedProcess[str]:

    environment = os.environ.copy()

    environment[
        "PYTHONDONTWRITEBYTECODE"
    ] = "1"

    return subprocess.run(
        args,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def digest_file(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def official_fingerprint() -> dict[str, str]:

    paths = [
        TEMPLATE,
        INDEX,
        RELATED,
        CATEGORIES,
        CATALOG,
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

    return {
        str(
            path.relative_to(
                ROOT
            )
        ):
            digest_file(
                path
            )
        for path in paths
    }


def create_fixture_template(
    target: Path,
) -> None:

    source = TEMPLATE.read_text(
        encoding="utf-8"
    )

    for marker, label in (
        (
            HTML_START,
            "template possui HTML_START único",
        ),
        (
            HTML_END,
            "template possui HTML_END único",
        ),
        (
            CSS_START,
            "template possui CSS_START único",
        ),
        (
            CSS_END,
            "template possui CSS_END único",
        ),
    ):

        require(
            source.count(
                marker
            ) == 1,
            label,
        )


    html_start = source.index(
        HTML_START
    )

    html_end = source.index(
        HTML_END
    )

    require(
        html_start < html_end,
        "região HTML RELATED está ordenada",
    )

    require(
        not source[
            html_start
            + len(HTML_START):
            html_end
        ].strip(),
        "região HTML RELATED do template é vazia",
    )


    css_start = source.index(
        CSS_START
    )

    css_end = source.index(
        CSS_END
    )

    require(
        css_start < css_end,
        "região CSS RELATED está ordenada",
    )

    require(
        bool(
            source[
                css_start
                + len(CSS_START):
                css_end
            ].strip()
        ),
        "região CSS RELATED possui estilos",
    )


    target.write_text(
        source,
        encoding="utf-8",
    )


def extract_controlled_region(
    text: str,
    start_marker: str,
    end_marker: str,
    label: str,
) -> str:

    if text.count(
        start_marker
    ) != 1:
        raise RuntimeError(
            f"{label}: START inválido"
        )

    if text.count(
        end_marker
    ) != 1:
        raise RuntimeError(
            f"{label}: END inválido"
        )

    start = text.index(
        start_marker
    )

    end = (
        text.index(
            end_marker,
            start,
        )
        + len(end_marker)
    )

    if start >= end:
        raise RuntimeError(
            f"{label}: marcadores fora de ordem"
        )

    return text[
        start:end
    ]


def create_legacy_articles(
    target: Path,
) -> None:

    target.mkdir()

    template_text = TEMPLATE.read_text(
        encoding="utf-8"
    )

    template_css = extract_controlled_region(
        template_text,
        CSS_START,
        CSS_END,
        "template CSS RELATED",
    )

    sources = sorted(
        ARTICLES_DIR.glob(
            "*.html"
        ),
        key=lambda item:
            item.name.casefold(),
    )

    require(
        len(sources) == 12,
        "estado oficial possui 12 artigos para fixture legado",
    )

    for source in sources:

        text = source.read_text(
            encoding="utf-8"
        )

        article_css = extract_controlled_region(
            text,
            CSS_START,
            CSS_END,
            f"{source.name}: CSS RELATED",
        )

        if article_css != template_css:
            raise RuntimeError(
                f"{source.name}: CSS RELATED "
                "diverge do Template Oficial"
            )

        css_insertion = (
            article_css
            + "\n\n"
        )

        if text.count(
            css_insertion
        ) != 1:
            raise RuntimeError(
                f"{source.name}: inserção CSS "
                "não é reversível"
            )

        text = text.replace(
            css_insertion,
            "",
            1,
        )

        html_region = extract_controlled_region(
            text,
            HTML_START,
            HTML_END,
            f"{source.name}: HTML RELATED",
        )

        html_insertion = (
            html_region
            + "\n\n\n"
        )

        if text.count(
            html_insertion
        ) != 1:
            raise RuntimeError(
                f"{source.name}: inserção HTML "
                "não é reversível"
            )

        text = text.replace(
            html_insertion,
            "",
            1,
        )

        if (
            HTML_START in text
            or HTML_END in text
            or CSS_START in text
            or CSS_END in text
        ):
            raise RuntimeError(
                f"{source.name}: fixture legado "
                "preservou marcador RELATED"
            )

        destination = (
            target
            / source.name
        )

        destination.write_text(
            text,
            encoding="utf-8",
        )


def collective_digest(
    directory: Path,
) -> str:

    digest = hashlib.sha256()

    for path in sorted(
        directory.glob(
            "*.html"
        ),
        key=lambda item:
            item.name.casefold(),
    ):

        digest.update(
            path.name.encode(
                "utf-8"
            )
        )

        digest.update(
            b"\0"
        )

        digest.update(
            hashlib.sha256(
                path.read_bytes()
            ).digest()
        )

    return digest.hexdigest()


def validate_topology(
    rendered_dir: Path,
) -> None:

    graph = json.loads(
        RELATED.read_text(
            encoding="utf-8"
        )
    )[
        "articles"
    ]

    visible = 0
    empty = 0
    edges = 0

    for slug, targets in sorted(
        graph.items()
    ):

        path = (
            rendered_dir
            / f"{slug}.html"
        )

        require(
            path.is_file(),
            f"{slug}: HTML renderizado existe",
        )

        if not path.is_file():
            continue

        text = path.read_text(
            encoding="utf-8"
        )

        require(
            text.count(
                "DATADARK:RELATED:START"
            ) == 1,
            f"{slug}: HTML_START único",
        )

        require(
            text.count(
                "DATADARK:RELATED:END"
            ) == 1,
            f"{slug}: HTML_END único",
        )

        require(
            text.count(
                "DATADARK:RELATED:CSS:START"
            ) == 1,
            f"{slug}: CSS_START único",
        )

        require(
            text.count(
                "DATADARK:RELATED:CSS:END"
            ) == 1,
            f"{slug}: CSS_END único",
        )

        section_count = (
            text.count(
                'class="article-section kb-related"'
            )
        )

        heading_count = (
            text.count(
                "Artigos relacionados"
            )
        )

        if targets:

            visible += 1
            edges += len(
                targets
            )

            require(
                section_count == 1,
                f"{slug}: bloco visual único",
            )

            require(
                heading_count == 1,
                f"{slug}: heading único",
            )

            for target in targets:

                url = (
                    "/base-conhecimento/artigos/"
                    f"{target}.html"
                )

                require(
                    text.count(
                        url
                    ) == 1,
                    (
                        f"{slug}: destino "
                        f"{target} único"
                    ),
                )

        else:

            empty += 1

            require(
                section_count == 0,
                f"{slug}: sem bloco visual vazio",
            )

            require(
                heading_count == 0,
                f"{slug}: sem heading vazio",
            )

    require(
        len(graph) == 12,
        "grafo oficial possui 12 artigos",
    )

    require(
        visible == 4,
        "grafo atual produz 4 blocos visíveis",
    )

    require(
        empty == 8,
        "grafo atual mantém 8 artigos sem bloco",
    )

    require(
        edges == 4,
        "grafo atual possui 4 relações",
    )


def main() -> int:

    print(
        "Base de Conhecimento DATADARK"
    )

    print(
        "Testes do Renderizador Estático "
        "de Artigos Relacionados V1"
    )

    print(
        "=" * 54
    )


    require(
        RENDERER.is_file(),
        "renderizador existe",
    )

    require(
        os.access(
            RENDERER,
            os.X_OK,
        ),
        "renderizador é executável",
    )


    before = (
        official_fingerprint()
    )


    with tempfile.TemporaryDirectory(
        prefix="datadark-related-render-test-"
    ) as temp_name:

        temp = Path(
            temp_name
        )

        fixture_template = (
            temp
            / "artigo-v1-related.html"
        )

        legacy_articles = (
            temp
            / "legacy-artigos"
        )

        render_1 = (
            temp
            / "render-1"
        )

        render_2 = (
            temp
            / "render-2"
        )

        render_idempotent = (
            temp
            / "render-idempotent"
        )


        create_fixture_template(
            fixture_template
        )

        create_legacy_articles(
            legacy_articles
        )


        legacy_check = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    legacy_articles
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--check",
            ]
        )

        require(
            legacy_check.returncode == 1,
            "layout legado retorna exit 1 no --check",
        )

        require(
            "ARTIGOS_DIVERGENTES=12"
            in legacy_check.stdout,
            "layout legado identifica 12 divergências",
        )

        require(
            "RENDER_RELACIONADOS=1"
            in legacy_check.stdout,
            "layout legado usa status funcional 1",
        )


        first_render = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    legacy_articles
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--output-dir",
                str(
                    render_1
                ),
            ]
        )

        require(
            first_render.returncode == 0,
            "primeira renderização retorna exit 0",
        )

        require(
            render_1.is_dir(),
            "primeira saída foi criada",
        )

        require(
            len(
                list(
                    render_1.glob(
                        "*.html"
                    )
                )
            ) == 12,
            "primeira saída possui 12 HTMLs",
        )

        require(
            "Blocos visíveis: 4"
            in first_render.stdout,
            "primeira renderização informa 4 blocos",
        )

        require(
            "Artigos sem bloco: 8"
            in first_render.stdout,
            "primeira renderização informa 8 sem bloco",
        )

        require(
            "Relações: 4"
            in first_render.stdout,
            "primeira renderização informa 4 relações",
        )

        validate_topology(
            render_1
        )

        require(
            collective_digest(
                render_1
            )
            ==
            collective_digest(
                ARTICLES_DIR
            ),
            (
                "renderização do fixture legado "
                "reproduz estado oficial sincronizado"
            ),
        )


        rendered_check = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    render_1
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--check",
            ]
        )

        require(
            rendered_check.returncode == 0,
            "--check aceita HTML já renderizado",
        )

        require(
            "ARTIGOS_DIVERGENTES=0"
            in rendered_check.stdout,
            "--check encontra zero divergências",
        )

        require(
            "RENDER_RELACIONADOS=0"
            in rendered_check.stdout,
            "--check sincronizado retorna status 0",
        )


        second_render = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    legacy_articles
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--output-dir",
                str(
                    render_2
                ),
            ]
        )

        require(
            second_render.returncode == 0,
            "segunda renderização independente retorna exit 0",
        )

        require(
            collective_digest(
                render_1
            )
            ==
            collective_digest(
                render_2
            ),
            "duas renderizações legadas são determinísticas",
        )


        idempotent_render = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    render_1
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--output-dir",
                str(
                    render_idempotent
                ),
            ]
        )

        require(
            idempotent_render.returncode == 0,
            "renderização sobre HTML pronto retorna exit 0",
        )

        require(
            "Artigos alterados: 0"
            in idempotent_render.stdout,
            "renderização idempotente informa zero alterações",
        )

        require(
            collective_digest(
                render_1
            )
            ==
            collective_digest(
                render_idempotent
            ),
            "renderização é idempotente byte a byte",
        )


        invalid_related = (
            temp
            / "relacionados-invalidos.json"
        )

        invalid_data = json.loads(
            RELATED.read_text(
                encoding="utf-8"
            )
        )

        invalid_data[
            "articles"
        ][
            "wifi-conecta-mas-fica-sem-internet"
        ] = [
            "slug-inexistente"
        ]

        invalid_related.write_text(
            json.dumps(
                invalid_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        invalid_output = (
            temp
            / "invalid-output"
        )

        invalid_result = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--related",
                str(
                    invalid_related
                ),
                "--output-dir",
                str(
                    invalid_output
                ),
            ]
        )

        require(
            invalid_result.returncode == 2,
            "destino inexistente retorna exit 2",
        )

        require(
            not invalid_output.exists(),
            "destino inexistente não cria saída parcial",
        )


        corrupt_dir = (
            temp
            / "corrupt"
        )

        shutil.copytree(
            render_1,
            corrupt_dir,
        )

        corrupt_article = (
            corrupt_dir
            / "windows-inicia-muito-lento.html"
        )

        corrupt_text = (
            corrupt_article.read_text(
                encoding="utf-8"
            )
        )

        body_anchor = (
            "<body>\n"
        )

        require(
            corrupt_text.count(
                body_anchor
            ) == 1,
            "fixture possui body anchor único",
        )

        corrupt_text = (
            corrupt_text.replace(
                body_anchor,
                (
                    body_anchor
                    + '<div class="kb-related-link">'
                    + "</div>\n"
                ),
                1,
            )
        )

        corrupt_article.write_text(
            corrupt_text,
            encoding="utf-8",
        )

        corrupt_result = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--articles-dir",
                str(
                    corrupt_dir
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--check",
            ]
        )

        require(
            corrupt_result.returncode == 2,
            "HTML RELATED fora da região retorna exit 2",
        )

        require(
            "bloco RELATED fora da região controlada"
            in (
                corrupt_result.stderr
                + corrupt_result.stdout
            ),
            "corrupção externa é identificada",
        )


        existing_output = (
            temp
            / "existing-output"
        )

        existing_output.mkdir()

        existing_result = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--template",
                str(
                    fixture_template
                ),
                "--output-dir",
                str(
                    existing_output
                ),
            ]
        )

        require(
            existing_result.returncode == 2,
            "output-dir existente retorna exit 2",
        )


        broken_template = (
            temp
            / "broken-template.html"
        )

        broken_text = (
            fixture_template.read_text(
                encoding="utf-8"
            )
            .replace(
                (
                    "        <!-- "
                    "DATADARK:RELATED:END -->"
                ),
                "",
                1,
            )
        )

        broken_template.write_text(
            broken_text,
            encoding="utf-8",
        )

        broken_result = run(
            [
                sys.executable,
                str(
                    RENDERER
                ),
                "--template",
                str(
                    broken_template
                ),
                "--check",
            ]
        )

        require(
            broken_result.returncode == 2,
            "template sem marcador retorna exit 2",
        )


    after = (
        official_fingerprint()
    )


    require(
        before == after,
        "artefatos oficiais permaneceram imutáveis",
    )


    print()
    print(
        "=" * 54
    )

    if errors:

        print(
            "RESULTADO: "
            f"{errors} TESTE(S) FALHARAM"
        )

        print(
            f"RENDER_TESTES={errors}"
        )

        return 1


    print(
        "RESULTADO: TODOS OS TESTES DO "
        "RENDERIZADOR PASSARAM"
    )

    print(
        "RENDER_TESTES=0"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
