/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 7 — Testes da Consulta Integrada V1.0
 */


import {
  readFileSync,
} from "node:fs";


import {
  dirname,
  join,
  resolve,
} from "node:path";


import {
  fileURLToPath,
} from "node:url";


import {
  prepareTaxonomy,
} from "../../base-conhecimento/assets/js/categorias.js";


import {
  prepareIndex,
} from "../../base-conhecimento/assets/js/pesquisa.js";


import {
  searchKnowledgeBase,
  listKnowledgeBase,
} from "../../base-conhecimento/assets/js/consulta.js";


/* ==========================================================
   UTILITÁRIOS
   ========================================================== */

function assert(
  condition,
  message
) {

  if (!condition) {

    throw new Error(
      `FALHA: ${message}`
    );

  }

}


function assertThrows(
  callback,
  message
) {

  let thrown = false;


  try {

    callback();

  }

  catch {

    thrown = true;

  }


  assert(
    thrown,
    message
  );

}


function printResult(
  label,
  value
) {

  console.log(
    `[OK] ${label}: ${value}`
  );

}


/* ==========================================================
   TAXONOMIA OFICIAL
   ========================================================== */

const scriptDirectory =
  dirname(
    fileURLToPath(
      import.meta.url
    )
  );


const repositoryRoot =
  resolve(
    scriptDirectory,
    "../.."
  );


const taxonomyPath =
  join(
    repositoryRoot,
    "base-conhecimento",
    "data",
    "categorias.json"
  );


const taxonomy =
  prepareTaxonomy(
    JSON.parse(
      readFileSync(
        taxonomyPath,
        "utf8"
      )
    )
  );


/* ==========================================================
   DATASET DE INTEGRAÇÃO
   ========================================================== */

const index =
  prepareIndex([
    {
      slug:
        "falha-conexao-rede",

      title:
        "Falha geral de conexão",

      description:
        "Diagnóstico de falha de conectividade.",

      url:
        "artigos/falha-conexao-rede.html",

      category_id:
        "rede",

      category:
        "Rede",

      keywords: [
        "falha",
        "wlan",
      ],

      aliases: [],
    },

    {
      slug:
        "falha-conexao-wifi",

      title:
        "Falha geral de conexão",

      description:
        "Diagnóstico de falha de conectividade.",

      url:
        "artigos/falha-conexao-wifi.html",

      category_id:
        "wifi",

      category:
        "Wi-Fi",

      keywords: [
        "falha",
        "wlan",
      ],

      aliases: [],
    },

    {
      slug:
        "termo-de-garantia",

      title:
        "Termo de Garantia",

      description:
        "Documento técnico.",

      url:
        "artigos/termo-de-garantia.html",

      category_id:
        "documentos",

      category:
        "Documentos",

      keywords: [
        "garantia",
      ],

      aliases: [],
    },

    {
      slug:
        "ordem-de-servico",

      title:
        "Ordem de Serviço",

      description:
        "Documento técnico.",

      url:
        "artigos/ordem-de-servico.html",

      category_id:
        "documentos",

      category:
        "Documentos",

      keywords: [
        "ordem",
        "servico",
      ],

      aliases: [],
    },

    {
      slug:
        "laudo-tecnico",

      title:
        "Laudo Técnico",

      description:
        "Documento técnico.",

      url:
        "artigos/laudo-tecnico.html",

      category_id:
        "documentos",

      category:
        "Documentos",

      keywords: [
        "laudo",
      ],

      aliases: [],
    },
  ]);


console.log(
  "Base de Conhecimento DATADARK"
);

console.log(
  "Testes da Consulta Integrada V1.0"
);

console.log(
  "=============================================="
);

console.log();


/* ==========================================================
   TESTE 1 — INTENÇÃO AUTOMÁTICA
   ========================================================== */

const automaticIntent =
  searchKnowledgeBase(
    index,
    taxonomy,
    "wlan falha",
    "todos",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  automaticIntent.length === 2,
  "consulta deve retornar rede e wifi"
);


assert(
  automaticIntent[0]
    .article
    .category_id
    === "wifi",
  "intenção WLAN deve priorizar Wi-Fi"
);


assert(
  automaticIntent[0]
    .categoryIntentBonus
    === 30,
  "Wi-Fi deve receber bônus automático +30"
);


assert(
  automaticIntent[1]
    .categoryIntentBonus
    === 0,
  "Rede não deve receber bônus de intenção WLAN"
);


printResult(
  "Intenção automática",
  "wifi +30"
);


/* ==========================================================
   TESTE 2 — HARD FILTER DOMINA O BÔNUS
   ========================================================== */

const networkOnly =
  searchKnowledgeBase(
    index,
    taxonomy,
    "wlan falha",
    "rede",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  networkOnly.length === 1,
  "filtro Rede deve produzir somente um resultado"
);


assert(
  networkOnly[0]
    .article
    .category_id
    === "rede",
  "hard filter Rede deve excluir Wi-Fi"
);


assert(
  networkOnly[0]
    .categoryIntentBonus
    === 0,
  "bônus não pode atravessar hard filter"
);


printResult(
  "Hard filter > bônus",
  "OK"
);


/* ==========================================================
   TESTE 3 — GRUPO
   ========================================================== */

const networkGroup =
  searchKnowledgeBase(
    index,
    taxonomy,
    "wlan falha",
    "group:area-rede-wifi",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  networkGroup.length === 2,
  "grupo Rede/Wi-Fi deve permitir as duas categorias"
);


assert(
  networkGroup[0]
    .article
    .category_id
    === "wifi",
  "grupo deve manter bônus de intenção Wi-Fi"
);


assert(
  networkGroup[0]
    .categoryIntentBonus
    === 30,
  "Wi-Fi deve receber +30 dentro do grupo"
);


printResult(
  "Filtro de grupo",
  "rede OR wifi"
);


/* ==========================================================
   TESTE 4 — LISTAGEM DE CATEGORIA
   ========================================================== */

const documents =
  listKnowledgeBase(
    index,
    taxonomy,
    "documentos"
  );


const documentTitles =
  documents.map(
    (item) =>
      item.article.title
  );


assert(
  JSON.stringify(
    documentTitles
  )
  ===
  JSON.stringify([
    "Laudo Técnico",
    "Ordem de Serviço",
    "Termo de Garantia",
  ]),
  "Documentos devem ser listados alfabeticamente"
);


printResult(
  "Listagem documentos",
  documentTitles.join(" | ")
);


/* ==========================================================
   TESTE 5 — TODOS SEM CONSULTA
   ========================================================== */

const emptyGlobalSearch =
  searchKnowledgeBase(
    index,
    taxonomy,
    "   ",
    "todos"
  );


assert(
  emptyGlobalSearch.length === 0,
  "Todos sem consulta deve preservar pesquisa vazia"
);


printResult(
  "Todos sem consulta",
  "0 resultados"
);


/* ==========================================================
   TESTE 6 — FILTRO INVÁLIDO
   ========================================================== */

assertThrows(
  () =>
    searchKnowledgeBase(
      index,
      taxonomy,
      "falha",
      "Wi-Fi"
    ),
  "label não pode ser usado como filtro"
);


assertThrows(
  () =>
    listKnowledgeBase(
      index,
      taxonomy,
      "group:inexistente"
    ),
  "grupo inexistente deve falhar"
);


printResult(
  "Filtros fail-closed",
  "OK"
);


/* ==========================================================
   TESTE 7 — OPÇÕES RESERVADAS
   ========================================================== */

assertThrows(
  () =>
    searchKnowledgeBase(
      index,
      taxonomy,
      "falha",
      "todos",
      {
        categoryIds: [
          "wifi",
        ],
      }
    ),
  "orquestrador deve controlar categoryIds"
);


assertThrows(
  () =>
    searchKnowledgeBase(
      index,
      taxonomy,
      "falha",
      "todos",
      {
        categoryIntentIds: [
          "rede",
        ],
      }
    ),
  "orquestrador deve controlar categoryIntentIds"
);


printResult(
  "Opções reservadas",
  "OK"
);


/* ==========================================================
   TESTE 8 — DETERMINISMO
   ========================================================== */

const firstRun =
  searchKnowledgeBase(
    index,
    taxonomy,
    "wlan falha",
    "group:area-rede-wifi",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  ).map(
    (item) =>
      item.article.slug
  );


const secondRun =
  searchKnowledgeBase(
    index,
    taxonomy,
    "wlan falha",
    "group:area-rede-wifi",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  ).map(
    (item) =>
      item.article.slug
  );


assert(
  JSON.stringify(
    firstRun
  )
  ===
  JSON.stringify(
    secondRun
  ),
  "consulta integrada deve ser determinística"
);


printResult(
  "Determinismo",
  "OK"
);


/* ==========================================================
   RESULTADO
   ========================================================== */

console.log();

console.log(
  "=============================================="
);

console.log(
  "RESULTADO: TODOS OS TESTES "
  + "DA CONSULTA INTEGRADA PASSARAM"
);

console.log(
  "Consulta Integrada DATADARK V1.0"
);

console.log(
  "=============================================="
);
