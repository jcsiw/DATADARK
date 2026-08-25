#!/usr/bin/env node

/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * Testes da Interface Categorial V1.0
 *
 * Responsabilidades:
 * - validar o contrato HTML dos filtros;
 * - validar os seis grupos oficiais;
 * - validar acessibilidade básica dos controles;
 * - validar integração da interface com a taxonomia;
 * - validar persistência categorial;
 * - validar navegação categoria/grupo;
 * - validar separação entre interface e motor;
 * - validar contrato CSS dos controles interativos.
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  ALL_FILTER,
  prepareTaxonomy,
} from "../../base-conhecimento/assets/js/categorias.js";

import {
  fileURLToPath,
} from "node:url";


const HERE =
  path.dirname(
    fileURLToPath(
      import.meta.url
    )
  );


const ROOT =
  path.resolve(
    HERE,
    "../.."
  );


const PATHS = Object.freeze({

  html:
    path.join(
      ROOT,
      "base-conhecimento",
      "index.html"
    ),

  css:
    path.join(
      ROOT,
      "base-conhecimento",
      "assets",
      "css",
      "base-conhecimento.css"
    ),

  interface:
    path.join(
      ROOT,
      "base-conhecimento",
      "assets",
      "js",
      "interface.js"
    ),

  taxonomy:
    path.join(
      ROOT,
      "base-conhecimento",
      "data",
      "categorias.json"
    ),

});


function readUtf8(filePath) {

  return fs.readFileSync(
    filePath,
    "utf8"
  );

}


function countLiteral(
  source,
  literal
) {

  if (!literal) {

    throw new TypeError(
      "Literal de busca vazio."
    );

  }


  return (
    source.split(
      literal
    ).length - 1
  );

}


function extractFunction(
  source,
  name
) {

  const marker =
    `function ${name}(`;


  const start =
    source.indexOf(
      marker
    );


  assert.notEqual(
    start,
    -1,
    `Função ausente: ${name}`
  );


  const braceStart =
    source.indexOf(
      "{",
      start
    );


  assert.notEqual(
    braceStart,
    -1,
    `Corpo ausente: ${name}`
  );


  let depth = 0;


  for (
    let index = braceStart;
    index < source.length;
    index += 1
  ) {

    const character =
      source[index];


    if (character === "{") {

      depth += 1;

    }


    else if (character === "}") {

      depth -= 1;


      if (depth === 0) {

        return source.slice(
          start,
          index + 1
        );

      }

    }

  }


  throw new Error(
    `Função sem fechamento: ${name}`
  );

}


function requireTokens(
  source,
  tokens,
  label
) {

  for (
    const token
    of tokens
  ) {

    assert.equal(
      source.includes(
        token
      ),
      true,
      `${label}: token ausente: ${token}`
    );

  }

}


function logOk(message) {

  console.log(
    `[OK] ${message}`
  );

}


function main() {

  console.log(
    "Base de Conhecimento DATADARK"
  );

  console.log(
    "Testes da Interface Categorial V1.0"
  );

  console.log(
    "=============================================="
  );

  console.log();


  const html =
    readUtf8(
      PATHS.html
    );


  const css =
    readUtf8(
      PATHS.css
    );


  const interfaceSource =
    readUtf8(
      PATHS.interface
    );


  const taxonomyData =
    JSON.parse(
      readUtf8(
        PATHS.taxonomy
      )
    );


  const taxonomy =
    prepareTaxonomy(
      taxonomyData
    );


  /*
   * ========================================================
   * TAXONOMIA OFICIAL
   * ========================================================
   */

  assert.equal(
    taxonomy.categories.length,
    12
  );


  assert.equal(
    taxonomy.groups.length,
    6
  );


  logOk(
    "Taxonomia oficial: 12 categorias / 6 grupos"
  );


  /*
   * ========================================================
   * CONTAINER CATEGORIAL
   * ========================================================
   */

  assert.equal(
    countLiteral(
      html,
      'id="kb-category-strip"'
    ),
    1
  );


  assert.equal(
    countLiteral(
      html,
      '<span class="category-chip'
    ),
    0
  );


  assert.match(
    html,
    /<div\s+id="kb-category-strip"\s+class="category-strip"\s+aria-label="Categorias da Base de Conhecimento">\s*<\/div>/
  );


  logOk(
    "Container categorial dinâmico: OK"
  );


  /*
   * ========================================================
   * GRUPOS NO HTML
   * ========================================================
   */

  const groupFilters =
    Array.from(
      html.matchAll(
        /data-kb-filter="(group:[a-z0-9]+(?:-[a-z0-9]+)*)"/g
      ),
      (match) =>
        match[1]
    );


  const expectedGroupFilters =
    taxonomy.groups.map(
      (group) =>
        `group:${group.id}`
    );


  assert.deepEqual(
    groupFilters,
    expectedGroupFilters
  );


  assert.equal(
    groupFilters.length,
    6
  );


  assert.equal(
    countLiteral(
      html,
      '<article class="explore-card">'
    ),
    0
  );


  const exploreButtons =
    Array.from(
      html.matchAll(
        /<button\s+class="explore-card"\s+type="button"\s+data-kb-filter="(group:[a-z0-9]+(?:-[a-z0-9]+)*)"\s+aria-pressed="false">/g
      ),
      (match) =>
        match[1]
    );


  assert.deepEqual(
    exploreButtons,
    expectedGroupFilters
  );


  logOk(
    "Seis grupos oficiais no HTML: OK"
  );


  /*
   * ========================================================
   * SCRIPT PRINCIPAL
   * ========================================================
   */

  assert.match(
    html,
    /<script\s+type="module"\s+src="assets\/js\/interface\.js">\s*<\/script>/
  );


  logOk(
    "Carregamento modular da interface: OK"
  );


  /*
   * ========================================================
   * CONFIGURAÇÃO E IMPORTS
   * ========================================================
   */

  requireTokens(
    interfaceSource,
    [
      'from "./pesquisa.js"',
      'from "./categorias.js"',
      'from "./consulta.js"',
      "ALL_FILTER",
      "prepareTaxonomy",
      "resolveFilter",
      "searchKnowledgeBase",
      "listKnowledgeBase",
      '"data/categorias.json"',
      '"datadark-kb-query-v1"',
      '"datadark-kb-category-v1"',
    ],
    "Integração da interface"
  );


  assert.equal(
    interfaceSource.includes(
      "searchArticles("
    ),
    false,
    "interface.js não deve chamar searchArticles diretamente."
  );


  logOk(
    "Separação interface / consulta / pesquisa: OK"
  );


  /*
   * ========================================================
   * PERSISTÊNCIA CATEGORIAL
   * ========================================================
   */

  const storeFilter =
    extractFunction(
      interfaceSource,
      "storeCategoryFilter"
    );


  requireTokens(
    storeFilter,
    [
      "CONFIG.categoryStorageKey",
      "sessionStorage.setItem",
      "sessionStorage.removeItem",
      "ALL_FILTER",
    ],
    "storeCategoryFilter"
  );


  const restoreFilter =
    extractFunction(
      interfaceSource,
      "restoreCategoryFilter"
    );


  requireTokens(
    restoreFilter,
    [
      "CONFIG.categoryStorageKey",
      "sessionStorage.getItem",
      "ALL_FILTER",
    ],
    "restoreCategoryFilter"
  );


  const restoreValidated =
    extractFunction(
      interfaceSource,
      "restoreValidatedCategoryFilter"
    );


  requireTokens(
    restoreValidated,
    [
      "restoreCategoryFilter",
      "resolveFilter",
      "activeFilter",
      "ALL_FILTER",
      "storeCategoryFilter",
    ],
    "restoreValidatedCategoryFilter"
  );


  logOk(
    "Persistência datadark-kb-category-v1: OK"
  );


  /*
   * ========================================================
   * GERAÇÃO DOS CHIPS
   * ========================================================
   */

  const createCategoryButton =
    extractFunction(
      interfaceSource,
      "createCategoryButton"
    );


  requireTokens(
    createCategoryButton,
    [
      '"button"',
      '"category-chip"',
      "button.dataset.kbFilter",
      '"aria-pressed"',
      '"false"',
      "button.textContent",
    ],
    "createCategoryButton"
  );


  const renderCategoryFilters =
    extractFunction(
      interfaceSource,
      "renderCategoryFilters"
    );


  requireTokens(
    renderCategoryFilters,
    [
      "ALL_FILTER",
      '"Todos"',
      "taxonomy.categories",
      "category.id",
      "category.label",
      "replaceChildren",
    ],
    "renderCategoryFilters"
  );


  logOk(
    "Chips derivados exclusivamente da taxonomia: OK"
  );


  /*
   * ========================================================
   * SINCRONIZAÇÃO VISUAL / ARIA
   * ========================================================
   */

  const syncUi =
    extractFunction(
      interfaceSource,
      "syncCategoryFilterUi"
    );


  requireTokens(
    syncUi,
    [
      '"aria-pressed"',
      '"true"',
      '"false"',
      '"category-chip-active"',
      '"explore-card-active"',
      "activeFilter",
    ],
    "syncCategoryFilterUi"
  );


  logOk(
    "aria-pressed e estados ativos: OK"
  );


  /*
   * ========================================================
   * ALTERAÇÃO DO FILTRO
   * ========================================================
   */

  const setFilter =
    extractFunction(
      interfaceSource,
      "setActiveFilter"
    );


  requireTokens(
    setFilter,
    [
      "resolveFilter",
      "activeFilter",
      "storeCategoryFilter",
      "syncCategoryFilterUi",
      "executeCurrentSearch",
    ],
    "setActiveFilter"
  );


  const handleFilter =
    extractFunction(
      interfaceSource,
      "handleFilterClick"
    );


  requireTokens(
    handleFilter,
    [
      '"[data-kb-filter]"',
      "elements.categoryStrip",
      "elements.exploreGrid",
      "control.dataset.kbFilter",
      "setActiveFilter",
    ],
    "handleFilterClick"
  );


  logOk(
    "Eventos de categoria e grupo: OK"
  );


  /*
   * ========================================================
   * SEMÂNTICA DA CONSULTA
   * ========================================================
   */

  const executeSearch =
    extractFunction(
      interfaceSource,
      "executeCurrentSearch"
    );


  requireTokens(
    executeSearch,
    [
      "CONFIG.minimumQueryLength",
      "activeFilter",
      "ALL_FILTER",
      "listKnowledgeBase",
      "searchKnowledgeBase",
      "renderResults",
    ],
    "executeCurrentSearch"
  );


  assert.equal(
    executeSearch.indexOf(
      "listKnowledgeBase"
    )
    <
    executeSearch.indexOf(
      "searchKnowledgeBase"
    ),
    true,
    "Listagem categorial deve ser decidida antes da pesquisa textual."
  );


  logOk(
    "Semântica Todos / categoria / grupo / pesquisa: OK"
  );


  /*
   * ========================================================
   * LIMPAR PESQUISA
   * ========================================================
   */

  const clearSearch =
    extractFunction(
      interfaceSource,
      "clearSearch"
    );


  requireTokens(
    clearSearch,
    [
      'elements.search.value =',
      'storeQuery(',
      'executeCurrentSearch',
    ],
    "clearSearch"
  );


  assert.equal(
    /activeFilter\s*=\s*ALL_FILTER/
      .test(
        clearSearch
      ),
    false,
    "Limpar texto não deve limpar o filtro categorial."
  );


  logOk(
    "Limpar pesquisa preserva filtro categorial: OK"
  );


  /*
   * ========================================================
   * CARREGAMENTO FAIL-CLOSED
   * ========================================================
   */

  const loadKnowledgeBase =
    extractFunction(
      interfaceSource,
      "loadKnowledgeBase"
    );


  requireTokens(
    loadKnowledgeBase,
    [
      "Promise.all",
      "CONFIG.indexUrl",
      "CONFIG.categoriesUrl",
      "prepareTaxonomy",
      "prepareIndex",
      "preparedArticle",
      ".category_id",
      "resolveFilter",
      "restoreValidatedCategoryFilter",
      "renderCategoryFilters",
      "syncCategoryFilterUi",
      "indexReady = true",
      'setState(',
      '"error"',
    ],
    "loadKnowledgeBase"
  );


  logOk(
    "Carregamento índice + taxonomia fail-closed: OK"
  );


  /*
   * ========================================================
   * EVENTOS DO DOM
   * ========================================================
   */

  const bindEvents =
    extractFunction(
      interfaceSource,
      "bindEvents"
    );


  assert.match(
    bindEvents,
    /elements\.categoryStrip[\s\S]*addEventListener\([\s\S]*"click"[\s\S]*handleFilterClick/
  );


  assert.match(
    bindEvents,
    /elements\.exploreGrid[\s\S]*addEventListener\([\s\S]*"click"[\s\S]*handleFilterClick/
  );


  logOk(
    "Delegação de eventos dos filtros: OK"
  );


  /*
   * ========================================================
   * CSS
   * ========================================================
   */

  requireTokens(
    css,
    [
      ".category-chip {",
      ".category-chip-active {",
      ".category-chip:hover {",
      ".category-chip:focus-visible {",
      '.explore-card[type="button"] {',
      ".explore-card-active {",
      ".explore-card:focus-visible {",
      "cursor: pointer;",
    ],
    "CSS categorial"
  );


  logOk(
    "Contrato visual e foco por teclado: OK"
  );


  /*
   * ========================================================
   * GARANTIAS DE CARDINALIDADE
   * ========================================================
   */

  assert.equal(
    countLiteral(
      interfaceSource,
      '"datadark-kb-category-v1"'
    ),
    1
  );


  assert.equal(
    countLiteral(
      html,
      'data-kb-filter="group:'
    ),
    taxonomy.groups.length
  );


  assert.equal(
    ALL_FILTER,
    "todos"
  );


  logOk(
    "Cardinalidade e filtro global: OK"
  );


  console.log();

  console.log(
    "=============================================="
  );

  console.log(
    "RESULTADO: TODOS OS TESTES DA INTERFACE PASSARAM"
  );

  console.log(
    "Interface Categorial DATADARK V1.0"
  );

  console.log(
    "=============================================="
  );

}


try {

  main();

}

catch (error) {

  console.error();

  console.error(
    "=============================================="
  );

  console.error(
    "RESULTADO: FALHA NOS TESTES DA INTERFACE"
  );

  console.error(
    "=============================================="
  );

  console.error();

  console.error(
    error
  );


  process.exitCode = 1;

}
