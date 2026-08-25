/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 7 — Pesquisa Categorial
 * Consulta V1.0
 *
 * Responsabilidades:
 * - integrar taxonomia e motor de pesquisa;
 * - resolver filtros canônicos;
 * - detectar intenção categorial;
 * - aplicar filtro rígido;
 * - fornecer listagem categorial.
 *
 * Não manipula DOM.
 * Não carrega arquivos.
 */


import {
  ALL_FILTER,
  categoryIdsForFilter,
  detectCategoryIntent,
} from "./categorias.js";


import {
  searchArticles,
  listArticles,
} from "./pesquisa.js";


/* ==========================================================
   OPÇÕES RESERVADAS
   ========================================================== */

const RESERVED_OPTIONS =
  Object.freeze([
    "categoryIds",
    "categoryIntentIds",
  ]);


/* ==========================================================
   VALIDAÇÃO DE OPÇÕES
   ========================================================== */

function prepareCustomOptions(
  customOptions
) {

  if (
    customOptions === null
    || typeof customOptions
      !== "object"
    || Array.isArray(
      customOptions
    )
  ) {

    throw new TypeError(
      "As opções da consulta devem "
      + "ser um objeto."
    );

  }


  for (
    const key
    of RESERVED_OPTIONS
  ) {

    if (
      Object.prototype
        .hasOwnProperty
        .call(
          customOptions,
          key
        )
    ) {

      throw new TypeError(
        `Opção reservada: ${key}`
      );

    }

  }


  return {
    ...customOptions,
  };

}


/* ==========================================================
   PESQUISA INTEGRADA
   ========================================================== */

export function searchKnowledgeBase(
  preparedIndex,
  taxonomy,
  queryInput,
  filterValue = ALL_FILTER,
  customOptions = {}
) {

  const options =
    prepareCustomOptions(
      customOptions
    );


  const categoryIds =
    categoryIdsForFilter(
      taxonomy,
      filterValue
    );


  const categoryIntentIds =
    detectCategoryIntent(
      taxonomy,
      queryInput
    );


  return searchArticles(
    preparedIndex,
    queryInput,
    {
      ...options,

      categoryIds,

      categoryIntentIds,
    }
  );

}


/* ==========================================================
   LISTAGEM CATEGORIAL
   ========================================================== */

export function listKnowledgeBase(
  preparedIndex,
  taxonomy,
  filterValue = ALL_FILTER,
  customOptions = {}
) {

  const options =
    prepareCustomOptions(
      customOptions
    );


  const categoryIds =
    categoryIdsForFilter(
      taxonomy,
      filterValue
    );


  return listArticles(
    preparedIndex,
    {
      ...options,

      categoryIds,
    }
  );

}
