/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 4 — Motor Inteligente de Pesquisa
 * Interface V1.0
 *
 * Responsabilidades:
 * - carregar indice.json e categorias.json;
 * - integrar taxonomia, consulta e DOM;
 * - controlar estados visuais;
 * - debounce;
 * - renderizar resultados;
 * - navegação por teclado;
 * - preservar consulta e filtro na sessão.
 *
 * As regras de ranking permanecem em pesquisa.js.
 * As regras categoriais permanecem em categorias.js.
 * A orquestração permanece em consulta.js.
 */

import {
  prepareIndex,
} from "./pesquisa.js";


import {
  ALL_FILTER,
  prepareTaxonomy,
  resolveFilter,
} from "./categorias.js";


import {
  searchKnowledgeBase,
  listKnowledgeBase,
} from "./consulta.js";


const CONFIG = Object.freeze({
  indexUrl: "data/indice.json",

  categoriesUrl:
    "data/categorias.json",

  debounceMs: 100,

  minimumQueryLength: 2,

  maxRenderedResults: 20,

  storageKey:
    "datadark-kb-query-v1",

  categoryStorageKey:
    "datadark-kb-category-v1",
});


let initialized = false;
let elements = null;

let preparedIndex = [];

let taxonomy = null;

let indexReady = false;

let activeFilter =
  ALL_FILTER;

let debounceTimer = null;

let resultCards = [];
let activeResultIndex = -1;


/* ==========================================================
   ELEMENTOS
   ========================================================== */

function getElements() {

  const result = {

    search:
      document.getElementById(
        "kb-search"
      ),

    clear:
      document.getElementById(
        "kb-clear"
      ),

    categoryStrip:
      document.getElementById(
        "kb-category-strip"
      ),

    exploreGrid:
      document.querySelector(
        ".explore-grid"
      ),

    retry:
      document.getElementById(
        "kb-retry"
      ),

    initial:
      document.getElementById(
        "kb-initial"
      ),

    loading:
      document.getElementById(
        "kb-loading"
      ),

    results:
      document.getElementById(
        "kb-results"
      ),

    resultsList:
      document.getElementById(
        "kb-results-list"
      ),

    resultsCount:
      document.getElementById(
        "kb-results-count"
      ),

    empty:
      document.getElementById(
        "kb-empty"
      ),

    error:
      document.getElementById(
        "kb-error"
      ),
  };


  for (
    const [name, element]
    of Object.entries(result)
  ) {

    if (!element) {

      throw new Error(
        "Elemento obrigatório ausente: "
        + name
      );

    }

  }


  return result;
}


/* ==========================================================
   ESTADOS VISUAIS
   ========================================================== */

function setState(state) {

  const states = {

    initial:
      elements.initial,

    loading:
      elements.loading,

    results:
      elements.results,

    empty:
      elements.empty,

    error:
      elements.error,
  };


  if (!states[state]) {

    throw new Error(
      `Estado desconhecido: ${state}`
    );

  }


  for (
    const [name, element]
    of Object.entries(states)
  ) {

    element.hidden =
      name !== state;

  }

}


/* ==========================================================
   SESSION STORAGE
   ========================================================== */

function storeQuery(value) {

  try {

    const query =
      String(value || "").trim();


    if (query) {

      sessionStorage.setItem(
        CONFIG.storageKey,
        query
      );

    }

    else {

      sessionStorage.removeItem(
        CONFIG.storageKey
      );

    }

  }

  catch {

    /*
     * A pesquisa continua funcionando
     * mesmo sem sessionStorage.
     */

  }

}


function restoreQuery() {

  try {

    return (
      sessionStorage.getItem(
        CONFIG.storageKey
      )
      || ""
    );

  }

  catch {

    return "";

  }

}




/* ==========================================================
   SESSION STORAGE — FILTRO CATEGORIAL
   ========================================================== */

function storeCategoryFilter(value) {

  try {

    if (
      value
      && value !== ALL_FILTER
    ) {

      sessionStorage.setItem(
        CONFIG.categoryStorageKey,
        value
      );

    }

    else {

      sessionStorage.removeItem(
        CONFIG.categoryStorageKey
      );

    }

  }

  catch {

    /*
     * A filtragem continua funcionando
     * mesmo sem sessionStorage.
     */

  }

}


function restoreCategoryFilter() {

  try {

    return (
      sessionStorage.getItem(
        CONFIG.categoryStorageKey
      )
      || ALL_FILTER
    );

  }

  catch {

    return ALL_FILTER;

  }

}


function restoreValidatedCategoryFilter() {

  const storedFilter =
    restoreCategoryFilter();


  try {

    resolveFilter(
      taxonomy,
      storedFilter
    );


    activeFilter =
      storedFilter;

  }

  catch {

    /*
     * Um valor antigo, manualmente alterado ou
     * pertencente a outra versão da taxonomia
     * nunca pode contaminar a interface atual.
     */

    activeFilter =
      ALL_FILTER;


    storeCategoryFilter(
      ALL_FILTER
    );

  }

}



/* ==========================================================
   FILTROS — INTERFACE
   ========================================================== */

function createCategoryButton(
  value,
  label
) {

  const button =
    document.createElement(
      "button"
    );


  button.type =
    "button";

  button.className =
    "category-chip";

  button.dataset.kbFilter =
    value;

  button.setAttribute(
    "aria-pressed",
    "false"
  );

  button.textContent =
    label;


  return button;

}


function renderCategoryFilters() {

  const fragment =
    document.createDocumentFragment();


  fragment.append(
    createCategoryButton(
      ALL_FILTER,
      "Todos"
    )
  );


  for (
    const category
    of taxonomy.categories
  ) {

    fragment.append(
      createCategoryButton(
        category.id,
        category.label
      )
    );

  }


  elements.categoryStrip
    .replaceChildren(
      fragment
    );

}


function filterControls() {

  return Array.from(
    document.querySelectorAll(
      "[data-kb-filter]"
    )
  );

}


function syncCategoryFilterUi() {

  for (
    const control
    of filterControls()
  ) {

    const value =
      control.dataset.kbFilter
      || "";

    const active =
      value === activeFilter;


    control.setAttribute(
      "aria-pressed",
      active
        ? "true"
        : "false"
    );


    if (
      control.classList.contains(
        "category-chip"
      )
    ) {

      control.classList.toggle(
        "category-chip-active",
        active
      );

    }


    if (
      control.classList.contains(
        "explore-card"
      )
    ) {

      control.classList.toggle(
        "explore-card-active",
        active
      );

    }

  }

}


function setActiveFilter(value) {

  if (
    !indexReady
    || !taxonomy
  ) {

    return;

  }


  /*
   * resolveFilter é também a barreira de
   * validação do valor vindo do DOM.
   */
  resolveFilter(
    taxonomy,
    value
  );


  activeFilter =
    value;


  storeCategoryFilter(
    activeFilter
  );


  syncCategoryFilterUi();


  executeCurrentSearch();

}


function handleFilterClick(event) {

  const control =
    event.target.closest(
      "[data-kb-filter]"
    );


  if (!control) {

    return;

  }


  if (
    !elements.categoryStrip
      .contains(control)
    && !elements.exploreGrid
      .contains(control)
  ) {

    return;

  }


  const value =
    control.dataset.kbFilter;


  if (!value) {

    return;

  }


  setActiveFilter(
    value
  );

}

/* ==========================================================
   BOTÃO LIMPAR
   ========================================================== */

function updateClearButton() {

  elements.clear.hidden =
    elements.search.value.length === 0;

}


/* ==========================================================
   RESULTADOS
   ========================================================== */

function resetResultNavigation() {

  resultCards = [];

  activeResultIndex = -1;

}


function clearRenderedResults() {

  elements.resultsList
    .replaceChildren();

  elements.resultsCount
    .textContent = "";

  resetResultNavigation();

}


/* ==========================================================
   URL SEGURA
   ========================================================== */

function safeArticleUrl(value) {

  if (
    typeof value !== "string"
  ) {

    return null;

  }


  const url =
    value.trim();


  if (
    !/^artigos\/[a-z0-9]+(?:-[a-z0-9]+)*\.html$/
      .test(url)
  ) {

    return null;

  }


  return url;
}


/* ==========================================================
   CARD
   ========================================================== */

function createResultCard(result) {

  const article =
    result.article;


  const url =
    safeArticleUrl(
      article.url
    );


  if (!url) {

    return null;

  }


  const link =
    document.createElement(
      "a"
    );


  link.className =
    "result-card";


  link.href =
    url;


  link.addEventListener(
    "click",
    () => {

      storeQuery(
        elements.search.value
      );

    }
  );


  const category =
    document.createElement(
      "span"
    );


  category.className =
    "result-category";


  category.textContent =
    article.category
      ? article.category
      : "Artigo";


  const title =
    document.createElement(
      "h3"
    );


  title.className =
    "result-title";


  title.textContent =
    article.title;


  link.append(
    category,
    title
  );


  if (
    article.description
  ) {

    const description =
      document.createElement(
        "p"
      );


    description.className =
      "result-description";


    description.textContent =
      article.description;


    link.append(
      description
    );

  }


  return link;
}


/* ==========================================================
   CONTADOR
   ========================================================== */

function formatResultCount(count) {

  if (count === 1) {

    return "1 resultado encontrado";

  }


  return (
    `${count} resultados encontrados`
  );

}


/* ==========================================================
   RENDERIZAÇÃO
   ========================================================== */

function renderResults(results) {

  clearRenderedResults();


  const validResults =
    results.filter(
      (result) =>
        safeArticleUrl(
          result.article.url
        )
    );


  if (
    validResults.length === 0
  ) {

    setState(
      "empty"
    );

    return;

  }


  elements.resultsCount.textContent =
    formatResultCount(
      validResults.length
    );


  const visibleResults =
    validResults.slice(
      0,
      CONFIG.maxRenderedResults
    );


  const fragment =
    document.createDocumentFragment();


  for (
    const result
    of visibleResults
  ) {

    const card =
      createResultCard(
        result
      );


    if (card) {

      fragment.append(
        card
      );

    }

  }


  elements.resultsList.append(
    fragment
  );


  resultCards =
    Array.from(
      elements.resultsList
        .querySelectorAll(
          ".result-card"
        )
    );


  setState(
    "results"
  );

}


/* ==========================================================
   EXECUÇÃO DA PESQUISA
   ========================================================== */

function executeCurrentSearch() {

  updateClearButton();

  resetResultNavigation();


  if (
    !indexReady
    || !taxonomy
  ) {

    setState(
      "loading"
    );

    return;

  }


  const query =
    elements.search.value.trim();


  /*
   * Consulta curta no filtro global mantém
   * a experiência inicial histórica.
   *
   * Consulta curta com categoria/grupo ativo
   * passa a representar navegação categorial.
   */
  if (
    query.length
    < CONFIG.minimumQueryLength
  ) {

    if (
      activeFilter
      === ALL_FILTER
    ) {

      clearRenderedResults();

      setState(
        "initial"
      );

      return;

    }


    const listedResults =
      listKnowledgeBase(
        preparedIndex,
        taxonomy,
        activeFilter,
        {
          maxResults:
            Number.MAX_SAFE_INTEGER,
        }
      );


    renderResults(
      listedResults
    );

    return;

  }


  const results =
    searchKnowledgeBase(
      preparedIndex,
      taxonomy,
      query,
      activeFilter,
      {
        maxResults:
          Number.MAX_SAFE_INTEGER,
      }
    );


  renderResults(
    results
  );

}


/* ==========================================================
   DEBOUNCE
   ========================================================== */

function scheduleSearch() {

  if (
    debounceTimer !== null
  ) {

    clearTimeout(
      debounceTimer
    );

  }


  const query =
    elements.search.value;


  updateClearButton();

  storeQuery(
    query
  );


  if (
    query.trim().length
    < CONFIG.minimumQueryLength
  ) {

    executeCurrentSearch();

    return;

  }


  if (!indexReady) {

    setState(
      "loading"
    );

    return;

  }


  debounceTimer =
    window.setTimeout(
      () => {

        debounceTimer = null;

        executeCurrentSearch();

      },
      CONFIG.debounceMs
    );

}


/* ==========================================================
   CARREGAMENTO DA BASE
   ========================================================== */

async function loadKnowledgeBase() {

  indexReady = false;

  preparedIndex = [];

  taxonomy = null;

  activeFilter =
    ALL_FILTER;


  elements.categoryStrip
    .replaceChildren();


  clearRenderedResults();

  setState(
    "loading"
  );


  try {

    const fetchOptions = {
      cache: "no-store",
      credentials: "same-origin",
    };


    const [
      indexResponse,
      categoriesResponse,
    ] = await Promise.all([
      fetch(
        CONFIG.indexUrl,
        fetchOptions
      ),

      fetch(
        CONFIG.categoriesUrl,
        fetchOptions
      ),
    ]);


    if (!indexResponse.ok) {

      throw new Error(
        "Falha HTTP ao carregar índice: "
        + indexResponse.status
      );

    }


    if (!categoriesResponse.ok) {

      throw new Error(
        "Falha HTTP ao carregar taxonomia: "
        + categoriesResponse.status
      );

    }


    const [
      indexData,
      taxonomyData,
    ] = await Promise.all([
      indexResponse.json(),
      categoriesResponse.json(),
    ]);


    if (
      !Array.isArray(
        indexData
      )
    ) {

      throw new TypeError(
        "indice.json deve conter um array."
      );

    }


    taxonomy =
      prepareTaxonomy(
        taxonomyData
      );


    preparedIndex =
      prepareIndex(
        indexData
      );


    if (
      preparedIndex.length
      !== indexData.length
    ) {

      console.warn(
        "Base de Conhecimento DATADARK: "
        + "registros incompletos foram ignorados."
      );

    }


    /*
     * O índice oficial é gerado pelo backend,
     * mas o navegador também confirma que todo
     * category_id pertence à taxonomia carregada.
     */
    for (
      const preparedArticle
      of preparedIndex
    ) {

      resolveFilter(
        taxonomy,
        preparedArticle
          .article
          .category_id
      );

    }


    restoreValidatedCategoryFilter();


    renderCategoryFilters();

    syncCategoryFilterUi();


    indexReady = true;


    executeCurrentSearch();

  }

  catch (error) {

    indexReady = false;

    preparedIndex = [];

    taxonomy = null;

    activeFilter =
      ALL_FILTER;


    clearRenderedResults();

    setState(
      "error"
    );


    console.error(
      "Base de Conhecimento DATADARK: "
      + "não foi possível carregar índice e taxonomia.",
      error
    );

  }

}


/* ==========================================================
   LIMPAR PESQUISA
   ========================================================== */

function clearSearch() {

  if (
    debounceTimer !== null
  ) {

    clearTimeout(
      debounceTimer
    );

    debounceTimer = null;

  }


  elements.search.value =
    "";


  storeQuery(
    ""
  );


  updateClearButton();

  clearRenderedResults();


  if (indexReady) {

    executeCurrentSearch();

  }

  else {

    setState(
      "loading"
    );

  }


  elements.search.focus();

}


/* ==========================================================
   FOCO DOS RESULTADOS
   ========================================================== */

function focusResult(index) {

  if (
    resultCards.length === 0
  ) {

    return;

  }


  let target =
    index;


  if (
    target < 0
  ) {

    target =
      resultCards.length - 1;

  }


  if (
    target >= resultCards.length
  ) {

    target = 0;

  }


  activeResultIndex =
    target;


  resultCards[
    activeResultIndex
  ].focus();

}


/* ==========================================================
   TECLADO NO CAMPO
   ========================================================== */

function handleSearchKeydown(event) {

  if (
    event.key === "ArrowDown"
    && resultCards.length
  ) {

    event.preventDefault();

    focusResult(
      0
    );

    return;

  }


  if (
    event.key === "ArrowUp"
    && resultCards.length
  ) {

    event.preventDefault();

    focusResult(
      resultCards.length - 1
    );

    return;

  }


  if (
    event.key === "Enter"
    && resultCards.length
  ) {

    event.preventDefault();


    const target =
      activeResultIndex >= 0
        ? resultCards[
            activeResultIndex
          ]
        : resultCards[0];


    target.click();

  }

}


/* ==========================================================
   TECLADO NOS CARDS
   ========================================================== */

function handleResultsKeydown(event) {

  const card =
    event.target.closest(
      ".result-card"
    );


  if (!card) {

    return;

  }


  const index =
    resultCards.indexOf(
      card
    );


  if (index < 0) {

    return;

  }


  if (
    event.key === "ArrowDown"
  ) {

    event.preventDefault();

    focusResult(
      index + 1
    );

  }


  else if (
    event.key === "ArrowUp"
  ) {

    event.preventDefault();

    focusResult(
      index - 1
    );

  }

}


/* ==========================================================
   ESC
   ========================================================== */

function handleGlobalKeydown(event) {

  if (
    event.key !== "Escape"
  ) {

    return;

  }


  if (
    elements.search.value.length === 0
  ) {

    return;

  }


  event.preventDefault();

  clearSearch();

}


/* ==========================================================
   EVENTOS
   ========================================================== */

function bindEvents() {

  elements.search
    .addEventListener(
      "input",
      scheduleSearch
    );


  elements.search
    .addEventListener(
      "keydown",
      handleSearchKeydown
    );


  elements.clear
    .addEventListener(
      "click",
      clearSearch
    );


  elements.categoryStrip
    .addEventListener(
      "click",
      handleFilterClick
    );


  elements.exploreGrid
    .addEventListener(
      "click",
      handleFilterClick
    );


  elements.retry
    .addEventListener(
      "click",
      loadKnowledgeBase
    );


  elements.resultsList
    .addEventListener(
      "keydown",
      handleResultsKeydown
    );


  document.addEventListener(
    "keydown",
    handleGlobalKeydown
  );

}


/* ==========================================================
   INICIALIZAÇÃO
   ========================================================== */

export async function initKnowledgeBase() {

  if (initialized) {

    return;

  }


  initialized = true;


  elements =
    getElements();


  const storedQuery =
    restoreQuery();


  if (storedQuery) {

    elements.search.value =
      storedQuery;

  }


  updateClearButton();

  bindEvents();

  await loadKnowledgeBase();

}


/* ==========================================================
   AUTO-INICIALIZAÇÃO
   ========================================================== */

if (
  typeof document !== "undefined"
) {

  if (
    document.readyState
    === "loading"
  ) {

    document.addEventListener(
      "DOMContentLoaded",
      () => {

        initKnowledgeBase();

      },
      {
        once: true,
      }
    );

  }

  else {

    initKnowledgeBase();

  }

}
