/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 7 — Taxonomia e Filtros
 * Categorias V1.0
 *
 * Responsabilidades:
 * - preparar a taxonomia oficial para uso no navegador;
 * - validar categorias e grupos;
 * - resolver filtros canônicos;
 * - resolver grupos em category_ids;
 * - detectar intenção categorial exata da consulta.
 *
 * Não manipula DOM.
 * Não carrega arquivos.
 * Não executa pesquisa textual.
 * Não utiliza fuzzy matching.
 */


import {
  normalizeText,
} from "./normalizador.js";


/* ==========================================================
   CONTRATO
   ========================================================== */

export const TAXONOMY_VERSION = 1;

export const ALL_FILTER =
  "todos";

export const GROUP_FILTER_PREFIX =
  "group:";


const ID_PATTERN =
  /^[a-z0-9]+(?:-[a-z0-9]+)*$/;


/* ==========================================================
   UTILITÁRIOS DE VALIDAÇÃO
   ========================================================== */

function isPlainObject(value) {

  return (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  );

}


function requireObject(
  value,
  label
) {

  if (!isPlainObject(value)) {

    throw new TypeError(
      `${label} deve ser um objeto.`
    );

  }


  return value;
}


function requireExactText(
  value,
  label
) {

  if (
    typeof value !== "string"
    || value.length === 0
    || value.trim() !== value
  ) {

    throw new TypeError(
      `${label} deve ser texto não vazio `
      + "sem espaços externos."
    );

  }


  return value;
}


function requireId(
  value,
  label
) {

  const id =
    requireExactText(
      value,
      label
    );


  if (!ID_PATTERN.test(id)) {

    throw new TypeError(
      `${label} inválido: ${id}`
    );

  }


  return id;
}


function requireOrder(
  value,
  label
) {

  if (
    !Number.isInteger(value)
    || value < 0
  ) {

    throw new TypeError(
      `${label} deve ser inteiro `
      + "maior ou igual a zero."
    );

  }


  return value;
}


function requireArray(
  value,
  label
) {

  if (!Array.isArray(value)) {

    throw new TypeError(
      `${label} deve ser um array.`
    );

  }


  return value;
}


/* ==========================================================
   CONGELAMENTO
   ========================================================== */

function freezeStrings(values) {

  return Object.freeze([
    ...values,
  ]);

}


/* ==========================================================
   CATEGORIA
   ========================================================== */

function prepareCategory(
  rawCategory,
  index,
  categoryIds,
  intentOwners
) {

  const raw =
    requireObject(
      rawCategory,
      `categories[${index}]`
    );


  const id =
    requireId(
      raw.id,
      `categories[${index}].id`
    );


  if (categoryIds.has(id)) {

    throw new TypeError(
      `Categoria duplicada: ${id}`
    );

  }


  const label =
    requireExactText(
      raw.label,
      `categories[${index}].label`
    );


  const order =
    requireOrder(
      raw.order,
      `categories[${index}].order`
    );


  const rawSearchTerms =
    requireArray(
      raw.search_terms,
      `categories[${index}].search_terms`
    );


  if (rawSearchTerms.length === 0) {

    throw new TypeError(
      `Categoria sem search_terms: ${id}`
    );

  }


  const searchTerms = [];
  const localTerms = new Set();


  for (
    let termIndex = 0;
    termIndex < rawSearchTerms.length;
    termIndex += 1
  ) {

    const term =
      requireExactText(
        rawSearchTerms[termIndex],
        (
          `categories[${index}]`
          + `.search_terms[${termIndex}]`
        )
      );


    const normalized =
      normalizeText(term);


    if (!normalized) {

      throw new TypeError(
        `search_term vazio após normalização: ${term}`
      );

    }


    if (localTerms.has(normalized)) {

      throw new TypeError(
        `search_term duplicado na categoria ${id}: `
        + term
      );

    }


    localTerms.add(
      normalized
    );

    searchTerms.push(
      term
    );

  }


  /*
   * A intenção categorial pode vir do ID,
   * do label ou de search_terms.
   *
   * Repetições dentro da MESMA categoria são
   * válidas. Exemplo:
   *
   * id           = windows
   * label        = Windows
   * search_terms = ["windows", "win"]
   *
   * O que não pode existir é o mesmo termo
   * normalizado pertencendo a categorias diferentes.
   */

  const intentSources = [
    id,
    label,
    ...searchTerms,
  ];


  for (
    const source
    of intentSources
  ) {

    const normalized =
      normalizeText(source);


    if (!normalized) {

      continue;

    }


    const currentOwner =
      intentOwners.get(
        normalized
      );


    if (
      currentOwner
      && currentOwner !== id
    ) {

      throw new TypeError(
        "Termo de intenção categorial ambíguo: "
        + `"${source}" pertence a `
        + `${currentOwner} e ${id}`
      );

    }


    intentOwners.set(
      normalized,
      id
    );

  }


  categoryIds.add(
    id
  );


  return Object.freeze({
    id,
    label,
    order,

    search_terms:
      freezeStrings(
        searchTerms
      ),
  });

}


/* ==========================================================
   GRUPO
   ========================================================== */

function prepareGroup(
  rawGroup,
  index,
  knownCategoryIds,
  groupIds
) {

  const raw =
    requireObject(
      rawGroup,
      `groups[${index}]`
    );


  const id =
    requireId(
      raw.id,
      `groups[${index}].id`
    );


  if (groupIds.has(id)) {

    throw new TypeError(
      `Grupo duplicado: ${id}`
    );

  }


  const label =
    requireExactText(
      raw.label,
      `groups[${index}].label`
    );


  const order =
    requireOrder(
      raw.order,
      `groups[${index}].order`
    );


  const description =
    requireExactText(
      raw.description,
      `groups[${index}].description`
    );


  const rawCategoryIds =
    requireArray(
      raw.category_ids,
      `groups[${index}].category_ids`
    );


  if (rawCategoryIds.length === 0) {

    throw new TypeError(
      `Grupo sem categorias: ${id}`
    );

  }


  const categoryIds = [];
  const localIds = new Set();


  for (
    let categoryIndex = 0;
    categoryIndex < rawCategoryIds.length;
    categoryIndex += 1
  ) {

    const categoryId =
      requireId(
        rawCategoryIds[
          categoryIndex
        ],
        (
          `groups[${index}]`
          + `.category_ids[${categoryIndex}]`
        )
      );


    if (
      !knownCategoryIds.has(
        categoryId
      )
    ) {

      throw new TypeError(
        `Grupo ${id} referencia categoria `
        + `inexistente: ${categoryId}`
      );

    }


    if (localIds.has(categoryId)) {

      throw new TypeError(
        `Categoria duplicada no grupo ${id}: `
        + categoryId
      );

    }


    localIds.add(
      categoryId
    );

    categoryIds.push(
      categoryId
    );

  }


  groupIds.add(
    id
  );


  return Object.freeze({
    id,
    label,
    order,
    description,

    category_ids:
      freezeStrings(
        categoryIds
      ),
  });

}


/* ==========================================================
   TAXONOMIA
   ========================================================== */

export function prepareTaxonomy(
  input
) {

  const raw =
    requireObject(
      input,
      "Taxonomia"
    );


  if (
    raw.version
    !== TAXONOMY_VERSION
  ) {

    throw new TypeError(
      "Versão de taxonomia não suportada: "
      + String(raw.version)
    );

  }


  const rawCategories =
    requireArray(
      raw.categories,
      "categories"
    );


  const rawGroups =
    requireArray(
      raw.groups,
      "groups"
    );


  const categoryIds =
    new Set();

  const groupIds =
    new Set();

  const intentOwners =
    new Map();


  const categories =
    rawCategories.map(
      (
        category,
        index
      ) =>
        prepareCategory(
          category,
          index,
          categoryIds,
          intentOwners
        )
    );


  categories.sort(
    (left, right) => {

      if (
        left.order
        !== right.order
      ) {

        return (
          left.order
          - right.order
        );

      }


      return (
        left.id.localeCompare(
          right.id
        )
      );

    }
  );


  const groups =
    rawGroups.map(
      (
        group,
        index
      ) =>
        prepareGroup(
          group,
          index,
          categoryIds,
          groupIds
        )
    );


  groups.sort(
    (left, right) => {

      if (
        left.order
        !== right.order
      ) {

        return (
          left.order
          - right.order
        );

      }


      return (
        left.id.localeCompare(
          right.id
        )
      );

    }
  );


  const categoriesById =
    Object.create(null);

  const groupsById =
    Object.create(null);


  for (
    const category
    of categories
  ) {

    categoriesById[
      category.id
    ] = category;

  }


  for (
    const group
    of groups
  ) {

    groupsById[
      group.id
    ] = group;

  }


  Object.freeze(
    categoriesById
  );

  Object.freeze(
    groupsById
  );


  return Object.freeze({
    version:
      TAXONOMY_VERSION,

    categories:
      Object.freeze(
        categories
      ),

    groups:
      Object.freeze(
        groups
      ),

    categoriesById,

    groupsById,
  });

}


/* ==========================================================
   VALIDAÇÃO DE TAXONOMIA PREPARADA
   ========================================================== */

function requirePreparedTaxonomy(
  taxonomy
) {

  if (
    !taxonomy
    || typeof taxonomy !== "object"
    || taxonomy.version
      !== TAXONOMY_VERSION
    || !Array.isArray(
      taxonomy.categories
    )
    || !Array.isArray(
      taxonomy.groups
    )
    || !taxonomy.categoriesById
    || !taxonomy.groupsById
  ) {

    throw new TypeError(
      "Taxonomia preparada inválida."
    );

  }


  return taxonomy;
}


/* ==========================================================
   FILTROS
   ========================================================== */

export function resolveFilter(
  taxonomyInput,
  filterValue
) {

  const taxonomy =
    requirePreparedTaxonomy(
      taxonomyInput
    );


  if (
    typeof filterValue
    !== "string"
    || filterValue.length === 0
    || filterValue.trim()
      !== filterValue
  ) {

    throw new TypeError(
      "Filtro categorial inválido."
    );

  }


  if (
    filterValue
    === ALL_FILTER
  ) {

    return Object.freeze({
      value:
        ALL_FILTER,

      type:
        "all",

      id:
        null,

      label:
        "Todos",

      category_ids:
        null,
    });

  }


  const category =
    taxonomy.categoriesById[
      filterValue
    ];


  if (category) {

    return Object.freeze({
      value:
        category.id,

      type:
        "category",

      id:
        category.id,

      label:
        category.label,

      category_ids:
        freezeStrings([
          category.id,
        ]),
    });

  }


  if (
    filterValue.startsWith(
      GROUP_FILTER_PREFIX
    )
  ) {

    const groupId =
      filterValue.slice(
        GROUP_FILTER_PREFIX.length
      );


    const group =
      taxonomy.groupsById[
        groupId
      ];


    if (group) {

      return Object.freeze({
        value:
          GROUP_FILTER_PREFIX
          + group.id,

        type:
          "group",

        id:
          group.id,

        label:
          group.label,

        category_ids:
          group.category_ids,
      });

    }

  }


  throw new RangeError(
    "Filtro categorial desconhecido: "
    + filterValue
  );

}


export function categoryIdsForFilter(
  taxonomy,
  filterValue
) {

  return (
    resolveFilter(
      taxonomy,
      filterValue
    ).category_ids
  );

}


/* ==========================================================
   INTENÇÃO CATEGORIAL
   ========================================================== */

function textTokens(
  value
) {

  const normalized =
    normalizeText(
      value
    );


  if (!normalized) {

    return [];

  }


  return normalized
    .split(" ")
    .filter(Boolean);

}


function containsExactSequence(
  queryTokens,
  termTokens
) {

  if (
    termTokens.length === 0
    || termTokens.length
      > queryTokens.length
  ) {

    return false;

  }


  const lastStart =
    queryTokens.length
    - termTokens.length;


  for (
    let start = 0;
    start <= lastStart;
    start += 1
  ) {

    let matches = true;


    for (
      let offset = 0;
      offset < termTokens.length;
      offset += 1
    ) {

      if (
        queryTokens[
          start + offset
        ]
        !== termTokens[offset]
      ) {

        matches = false;
        break;

      }

    }


    if (matches) {

      return true;

    }

  }


  return false;

}


export function detectCategoryIntent(
  taxonomyInput,
  queryInput
) {

  const taxonomy =
    requirePreparedTaxonomy(
      taxonomyInput
    );


  if (
    queryInput === null
    || queryInput === undefined
  ) {

    return Object.freeze([]);

  }


  const queryTokens =
    textTokens(
      String(queryInput)
    );


  if (
    queryTokens.length === 0
  ) {

    return Object.freeze([]);

  }


  const result = [];


  for (
    const category
    of taxonomy.categories
  ) {

    const sources = [
      category.id,
      category.label,
      ...category.search_terms,
    ];


    let matched = false;


    for (
      const source
      of sources
    ) {

      const termTokens =
        textTokens(
          source
        );


      if (
        containsExactSequence(
          queryTokens,
          termTokens
        )
      ) {

        matched = true;
        break;

      }

    }


    if (matched) {

      result.push(
        category.id
      );

    }

  }


  return Object.freeze(
    result
  );

}
