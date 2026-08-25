"""
Base de Conhecimento DATADARK
Contrato compartilhado da taxonomia de categorias.

Responsabilidades:
- localizar a taxonomia oficial;
- carregar categorias.json;
- rejeitar JSON estruturalmente inválido;
- validar categorias e grupos;
- detectar duplicidades e colisões;
- resolver category_id de forma estrita.

Biblioteca padrão Python apenas.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


TAXONOMY_VERSION = 1

CATEGORY_ID_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)

GROUP_ID_RE = re.compile(
    r"^area-[a-z0-9]+(?:-[a-z0-9]+)*$"
)


class TaxonomyError(RuntimeError):
    """Erro de contrato ou carregamento da taxonomia."""


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    order: int
    search_terms: tuple[str, ...]


@dataclass(frozen=True)
class Group:
    id: str
    label: str
    order: int
    description: str
    category_ids: tuple[str, ...]


@dataclass(frozen=True)
class Taxonomy:
    version: int
    categories: tuple[Category, ...]
    groups: tuple[Group, ...]
    categories_by_id: dict[str, Category]
    groups_by_id: dict[str, Group]

    def resolve_category(
        self,
        category_id: str,
    ) -> Category:
        """
        Resolve exclusivamente um ID canônico.

        Não converte labels, caixa, acentos ou listas.
        """

        if not isinstance(
            category_id,
            str,
        ):
            raise TaxonomyError(
                "category_id deve ser texto"
            )

        if not category_id:
            raise TaxonomyError(
                "categoria ausente"
            )

        category = self.categories_by_id.get(
            category_id
        )

        if category is None:
            raise TaxonomyError(
                "categoria desconhecida: "
                f"{category_id}"
            )

        return category


def default_taxonomy_path() -> Path:
    """
    Retorna o caminho oficial de categorias.json
    independentemente do diretório atual.
    """

    repository_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    return (
        repository_root
        / "base-conhecimento"
        / "data"
        / "categorias.json"
    )


def canonical_key(
    value: str,
) -> str:
    """
    Forma canônica usada somente para detectar
    duplicidades e colisões na taxonomia.
    """

    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    normalized = "".join(
        char
        for char in normalized
        if not unicodedata.combining(
            char
        )
    )

    normalized = normalized.casefold()

    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        normalized,
    )

    return re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    """
    object_pairs_hook para impedir que json.loads
    aceite silenciosamente propriedades duplicadas.
    """

    result: dict[str, Any] = {}

    for key, value in pairs:

        if key in result:
            raise TaxonomyError(
                "chave JSON duplicada: "
                f"{key}"
            )

        result[key] = value

    return result


def _require_exact_keys(
    value: Any,
    expected: set[str],
    context: str,
) -> dict[str, Any]:

    if not isinstance(
        value,
        dict,
    ):
        raise TaxonomyError(
            f"{context} deve ser objeto JSON"
        )

    actual = set(value)

    if actual != expected:

        missing = sorted(
            expected - actual
        )

        extra = sorted(
            actual - expected
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

        raise TaxonomyError(
            f"estrutura inválida em {context}: "
            + "; ".join(details)
        )

    return value


def _require_text(
    value: Any,
    context: str,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TaxonomyError(
            f"{context} deve ser texto"
        )

    if not value:
        raise TaxonomyError(
            f"{context} não pode ser vazio"
        )

    if value != value.strip():
        raise TaxonomyError(
            f"{context} possui espaços "
            "externos"
        )

    return value


def _require_positive_integer(
    value: Any,
    context: str,
) -> int:

    if type(value) is not int:
        raise TaxonomyError(
            f"{context} deve ser inteiro"
        )

    if value <= 0:
        raise TaxonomyError(
            f"{context} deve ser positivo"
        )

    return value


def _validate_categories(
    raw_categories: Any,
) -> tuple[
    tuple[Category, ...],
    dict[str, Category],
]:

    if not isinstance(
        raw_categories,
        list,
    ):
        raise TaxonomyError(
            "categories deve ser lista"
        )

    if not raw_categories:
        raise TaxonomyError(
            "categories não pode ser vazio"
        )

    categories: list[Category] = []

    categories_by_id: dict[
        str,
        Category,
    ] = {}

    labels_seen: dict[
        str,
        str,
    ] = {}

    orders_seen: set[int] = set()

    global_terms: dict[
        str,
        str,
    ] = {}

    for position, raw in enumerate(
        raw_categories,
        start=1,
    ):

        context = (
            f"categories[{position}]"
        )

        item = _require_exact_keys(
            raw,
            {
                "id",
                "label",
                "order",
                "search_terms",
            },
            context,
        )

        category_id = _require_text(
            item["id"],
            f"{context}.id",
        )

        if not CATEGORY_ID_RE.fullmatch(
            category_id
        ):
            raise TaxonomyError(
                "ID de categoria inválido: "
                f"{category_id}"
            )

        if category_id in categories_by_id:
            raise TaxonomyError(
                "ID de categoria duplicado: "
                f"{category_id}"
            )

        label = _require_text(
            item["label"],
            f"{context}.label",
        )

        label_key = canonical_key(
            label
        )

        if not label_key:
            raise TaxonomyError(
                "label inválido em "
                f"{category_id}"
            )

        previous_label = labels_seen.get(
            label_key
        )

        if previous_label is not None:
            raise TaxonomyError(
                "label de categoria duplicado: "
                f"{label} "
                f"({previous_label}, "
                f"{category_id})"
            )

        labels_seen[
            label_key
        ] = category_id

        order = _require_positive_integer(
            item["order"],
            f"{context}.order",
        )

        if order in orders_seen:
            raise TaxonomyError(
                "order de categoria duplicado: "
                f"{order}"
            )

        orders_seen.add(
            order
        )

        raw_terms = item[
            "search_terms"
        ]

        if not isinstance(
            raw_terms,
            list,
        ):
            raise TaxonomyError(
                f"{context}.search_terms "
                "deve ser lista"
            )

        if not raw_terms:
            raise TaxonomyError(
                f"{context}.search_terms "
                "não pode ser vazio"
            )

        terms: list[str] = []
        local_terms: set[str] = set()

        for term_position, raw_term in enumerate(
            raw_terms,
            start=1,
        ):

            term = _require_text(
                raw_term,
                (
                    f"{context}.search_terms"
                    f"[{term_position}]"
                ),
            )

            term_key = canonical_key(
                term
            )

            if not term_key:
                raise TaxonomyError(
                    "search_term inválido "
                    f"em {category_id}: "
                    f"{term}"
                )

            if term_key in local_terms:
                raise TaxonomyError(
                    "search_term duplicado "
                    f"em {category_id}: "
                    f"{term}"
                )

            local_terms.add(
                term_key
            )

            previous_owner = (
                global_terms.get(
                    term_key
                )
            )

            if previous_owner is not None:
                raise TaxonomyError(
                    "search_term pertence a "
                    "mais de uma categoria: "
                    f"{term} "
                    f"({previous_owner}, "
                    f"{category_id})"
                )

            global_terms[
                term_key
            ] = category_id

            terms.append(
                term
            )

        category = Category(
            id=category_id,
            label=label,
            order=order,
            search_terms=tuple(
                terms
            ),
        )

        categories.append(
            category
        )

        categories_by_id[
            category_id
        ] = category

    category_orders = [
        category.order
        for category in categories
    ]

    if category_orders != sorted(
        category_orders
    ):
        raise TaxonomyError(
            "categories não está ordenado "
            "por order"
        )

    return (
        tuple(categories),
        categories_by_id,
    )


def _validate_groups(
    raw_groups: Any,
    categories_by_id: dict[
        str,
        Category,
    ],
) -> tuple[
    tuple[Group, ...],
    dict[str, Group],
]:

    if not isinstance(
        raw_groups,
        list,
    ):
        raise TaxonomyError(
            "groups deve ser lista"
        )

    if not raw_groups:
        raise TaxonomyError(
            "groups não pode ser vazio"
        )

    groups: list[Group] = []

    groups_by_id: dict[
        str,
        Group,
    ] = {}

    labels_seen: dict[
        str,
        str,
    ] = {}

    orders_seen: set[int] = set()

    for position, raw in enumerate(
        raw_groups,
        start=1,
    ):

        context = (
            f"groups[{position}]"
        )

        item = _require_exact_keys(
            raw,
            {
                "id",
                "label",
                "order",
                "description",
                "category_ids",
            },
            context,
        )

        group_id = _require_text(
            item["id"],
            f"{context}.id",
        )

        if not GROUP_ID_RE.fullmatch(
            group_id
        ):
            raise TaxonomyError(
                "ID de grupo inválido: "
                f"{group_id}"
            )

        if group_id in groups_by_id:
            raise TaxonomyError(
                "ID de grupo duplicado: "
                f"{group_id}"
            )

        label = _require_text(
            item["label"],
            f"{context}.label",
        )

        label_key = canonical_key(
            label
        )

        if not label_key:
            raise TaxonomyError(
                "label inválido em "
                f"{group_id}"
            )

        previous_label = labels_seen.get(
            label_key
        )

        if previous_label is not None:
            raise TaxonomyError(
                "label de grupo duplicado: "
                f"{label} "
                f"({previous_label}, "
                f"{group_id})"
            )

        labels_seen[
            label_key
        ] = group_id

        order = _require_positive_integer(
            item["order"],
            f"{context}.order",
        )

        if order in orders_seen:
            raise TaxonomyError(
                "order de grupo duplicado: "
                f"{order}"
            )

        orders_seen.add(
            order
        )

        description = _require_text(
            item["description"],
            f"{context}.description",
        )

        raw_category_ids = item[
            "category_ids"
        ]

        if not isinstance(
            raw_category_ids,
            list,
        ):
            raise TaxonomyError(
                f"{context}.category_ids "
                "deve ser lista"
            )

        if not raw_category_ids:
            raise TaxonomyError(
                f"{context}.category_ids "
                "não pode ser vazio"
            )

        category_ids: list[str] = []
        ids_seen: set[str] = set()

        for category_position, raw_id in enumerate(
            raw_category_ids,
            start=1,
        ):

            category_id = _require_text(
                raw_id,
                (
                    f"{context}.category_ids"
                    f"[{category_position}]"
                ),
            )

            if category_id in ids_seen:
                raise TaxonomyError(
                    "categoria repetida no "
                    f"grupo {group_id}: "
                    f"{category_id}"
                )

            ids_seen.add(
                category_id
            )

            if (
                category_id
                not in categories_by_id
            ):
                raise TaxonomyError(
                    f"{group_id} referencia "
                    "categoria inexistente: "
                    f"{category_id}"
                )

            category_ids.append(
                category_id
            )

        group = Group(
            id=group_id,
            label=label,
            order=order,
            description=description,
            category_ids=tuple(
                category_ids
            ),
        )

        groups.append(
            group
        )

        groups_by_id[
            group_id
        ] = group

    group_orders = [
        group.order
        for group in groups
    ]

    if group_orders != sorted(
        group_orders
    ):
        raise TaxonomyError(
            "groups não está ordenado "
            "por order"
        )

    return (
        tuple(groups),
        groups_by_id,
    )


def load_taxonomy(
    path: Path | str,
) -> Taxonomy:
    """
    Carrega e valida integralmente uma taxonomia.

    A função é fail-closed: qualquer desvio
    estrutural gera TaxonomyError.
    """

    taxonomy_path = Path(
        path
    )

    try:

        raw_text = taxonomy_path.read_text(
            encoding="utf-8"
        )

    except FileNotFoundError as exc:

        raise TaxonomyError(
            "arquivo de taxonomia "
            f"não encontrado: "
            f"{taxonomy_path}"
        ) from exc

    except UnicodeDecodeError as exc:

        raise TaxonomyError(
            "taxonomia não é UTF-8 válido: "
            f"{taxonomy_path}"
        ) from exc

    except OSError as exc:

        raise TaxonomyError(
            "falha ao ler taxonomia "
            f"{taxonomy_path}: {exc}"
        ) from exc

    try:

        data = json.loads(
            raw_text,
            object_pairs_hook=(
                _object_without_duplicate_keys
            ),
        )

    except json.JSONDecodeError as exc:

        raise TaxonomyError(
            "JSON inválido em "
            f"{taxonomy_path}: "
            f"linha {exc.lineno}, "
            f"coluna {exc.colno}: "
            f"{exc.msg}"
        ) from exc

    except TaxonomyError:
        raise

    top = _require_exact_keys(
        data,
        {
            "version",
            "categories",
            "groups",
        },
        "raiz",
    )

    version = top[
        "version"
    ]

    if type(version) is not int:
        raise TaxonomyError(
            "version deve ser inteiro"
        )

    if version != TAXONOMY_VERSION:
        raise TaxonomyError(
            "versão de taxonomia "
            "não suportada: "
            f"{version}"
        )

    (
        categories,
        categories_by_id,
    ) = _validate_categories(
        top["categories"]
    )

    (
        groups,
        groups_by_id,
    ) = _validate_groups(
        top["groups"],
        categories_by_id,
    )

    canonical_text = (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    if raw_text != canonical_text:
        raise TaxonomyError(
            "taxonomia não utiliza a "
            "serialização canônica UTF-8 "
            "esperada"
        )

    return Taxonomy(
        version=version,
        categories=categories,
        groups=groups,
        categories_by_id=(
            categories_by_id
        ),
        groups_by_id=(
            groups_by_id
        ),
    )


def resolve_category(
    taxonomy: Taxonomy,
    category_id: str,
) -> Category:
    """
    Interface funcional equivalente ao método
    Taxonomy.resolve_category().
    """

    return taxonomy.resolve_category(
        category_id
    )
