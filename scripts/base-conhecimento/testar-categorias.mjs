/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 7 — Testes da Taxonomia JavaScript V1.0
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
  ALL_FILTER,
  GROUP_FILTER_PREFIX,
  TAXONOMY_VERSION,
  prepareTaxonomy,
  resolveFilter,
  categoryIdsForFilter,
  detectCategoryIntent,
} from "../../base-conhecimento/assets/js/categorias.js";


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


function clone(
  value
) {

  return JSON.parse(
    JSON.stringify(
      value
    )
  );

}


/* ==========================================================
   CAMINHOS
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


/* ==========================================================
   CARREGAMENTO
   ========================================================== */

const taxonomyData =
  JSON.parse(
    readFileSync(
      taxonomyPath,
      "utf8"
    )
  );


const taxonomy =
  prepareTaxonomy(
    taxonomyData
  );


console.log(
  "Base de Conhecimento DATADARK"
);

console.log(
  "Testes da Taxonomia JavaScript V1.0"
);

console.log(
  "=============================================="
);

console.log();


/* ==========================================================
   TESTE 1 — CONTRATO OFICIAL
   ========================================================== */

assert(
  TAXONOMY_VERSION === 1,
  "versão JavaScript deve ser 1"
);

assert(
  taxonomy.version === 1,
  "taxonomia preparada deve manter versão 1"
);

assert(
  taxonomy.categories.length === 12,
  "taxonomia deve possuir 12 categorias"
);

assert(
  taxonomy.groups.length === 6,
  "taxonomia deve possuir 6 grupos"
);

assert(
  taxonomy.categories[0].id
    === "windows",
  "primeira categoria deve respeitar order"
);

assert(
  taxonomy.categories[11].id
    === "documentos",
  "última categoria deve respeitar order"
);

printResult(
  "Contrato oficial",
  "12 categorias / 6 grupos"
);


/* ==========================================================
   TESTE 2 — CONGELAMENTO
   ========================================================== */

assert(
  Object.isFrozen(
    taxonomy
  ),
  "taxonomia deve estar congelada"
);

assert(
  Object.isFrozen(
    taxonomy.categories
  ),
  "categorias devem estar congeladas"
);

assert(
  Object.isFrozen(
    taxonomy.groups
  ),
  "grupos devem estar congelados"
);

printResult(
  "Imutabilidade",
  "OK"
);


/* ==========================================================
   TESTE 3 — FILTRO TODOS
   ========================================================== */

const allFilter =
  resolveFilter(
    taxonomy,
    ALL_FILTER
  );


assert(
  allFilter.type === "all",
  "todos deve resolver como filtro global"
);

assert(
  allFilter.category_ids === null,
  "todos não deve restringir category_ids"
);

printResult(
  "Filtro todos",
  allFilter.label
);


/* ==========================================================
   TESTE 4 — CATEGORIA
   ========================================================== */

const wifiFilter =
  resolveFilter(
    taxonomy,
    "wifi"
  );


assert(
  wifiFilter.type
    === "category",
  "wifi deve resolver como categoria"
);

assert(
  wifiFilter.label
    === "Wi-Fi",
  "wifi deve resolver label oficial"
);

assert(
  JSON.stringify(
    wifiFilter.category_ids
  )
  === JSON.stringify([
    "wifi",
  ]),
  "wifi deve produzir somente category_id wifi"
);

printResult(
  "Filtro categoria",
  `${wifiFilter.value} → ${wifiFilter.label}`
);


/* ==========================================================
   TESTE 5 — GRUPO
   ========================================================== */

const networkGroupValue =
  GROUP_FILTER_PREFIX
  + "area-rede-wifi";


const networkGroup =
  resolveFilter(
    taxonomy,
    networkGroupValue
  );


assert(
  networkGroup.type
    === "group",
  "area-rede-wifi deve resolver como grupo"
);

assert(
  networkGroup.label
    === "Rede e Wi-Fi",
  "grupo deve preservar label oficial"
);

assert(
  JSON.stringify(
    networkGroup.category_ids
  )
  === JSON.stringify([
    "rede",
    "wifi",
  ]),
  "grupo deve resolver rede OR wifi"
);

printResult(
  "Filtro grupo",
  networkGroup.category_ids.join(" | ")
);


/* ==========================================================
   TESTE 6 — categoryIdsForFilter
   ========================================================== */

assert(
  categoryIdsForFilter(
    taxonomy,
    "hardware"
  )[0]
  === "hardware",
  "helper deve resolver categoria"
);

assert(
  categoryIdsForFilter(
    taxonomy,
    networkGroupValue
  ).length === 2,
  "helper deve resolver grupo"
);

assert(
  categoryIdsForFilter(
    taxonomy,
    "todos"
  ) === null,
  "helper deve retornar null para Todos"
);

printResult(
  "categoryIdsForFilter",
  "OK"
);


/* ==========================================================
   TESTE 7 — FILTROS INVÁLIDOS
   ========================================================== */

const invalidFilters = [
  "",
  "Todos",
  " todos ",
  "Wi-Fi",
  "internet",
  "group:internet",
  "group: area-rede-wifi",
];


for (
  const value
  of invalidFilters
) {

  assertThrows(
    () =>
      resolveFilter(
        taxonomy,
        value
      ),
    (
      "filtro inválido deveria ser rejeitado: "
      + JSON.stringify(value)
    )
  );

}


printResult(
  "Filtros inválidos",
  invalidFilters.length
);


/* ==========================================================
   TESTE 8 — INTENÇÃO WI-FI
   ========================================================== */

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "WIFI sem internet"
    )
  )
  === JSON.stringify([
    "wifi",
  ]),
  "WIFI deve produzir intenção wifi"
);

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "wireless instável"
    )
  )
  === JSON.stringify([
    "wifi",
  ]),
  "wireless deve produzir intenção wifi"
);

printResult(
  "Intenção Wi-Fi",
  "OK"
);


/* ==========================================================
   TESTE 9 — INTENÇÃO ARMAZENAMENTO
   ========================================================== */

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "ssd lento"
    )
  )
  === JSON.stringify([
    "armazenamento",
  ]),
  "ssd deve produzir intenção armazenamento"
);

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "nvme não aparece"
    )
  )
  === JSON.stringify([
    "armazenamento",
  ]),
  "nvme deve produzir intenção armazenamento"
);

printResult(
  "Intenção armazenamento",
  "OK"
);


/* ==========================================================
   TESTE 10 — TERMO MULTIPALAVRA
   ========================================================== */

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "problema na placa mãe"
    )
  )
  === JSON.stringify([
    "hardware",
  ]),
  "placa mãe deve produzir intenção hardware"
);

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "preciso de ordem de serviço"
    )
  )
  === JSON.stringify([
    "documentos",
  ]),
  "ordem de serviço deve produzir intenção documentos"
);

printResult(
  "Intenção multipalavra",
  "OK"
);


/* ==========================================================
   TESTE 11 — NÃO USAR PREFIXO/FUZZY
   ========================================================== */

assert(
  detectCategoryIntent(
    taxonomy,
    "red"
  ).length === 0,
  "red não pode inferir rede"
);

assert(
  detectCategoryIntent(
    taxonomy,
    "wif"
  ).length === 0,
  "wif não pode inferir wifi"
);

assert(
  detectCategoryIntent(
    taxonomy,
    "memori"
  ).length === 0,
  "memori não pode inferir memoria"
);

printResult(
  "Sem fuzzy categorial",
  "OK"
);


/* ==========================================================
   TESTE 12 — MÚLTIPLAS INTENÇÕES
   ========================================================== */

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "wifi ethernet instável"
    )
  )
  === JSON.stringify([
    "rede",
    "wifi",
  ]),
  "consulta deve poder detectar rede e wifi"
);

assert(
  JSON.stringify(
    detectCategoryIntent(
      taxonomy,
      "som hdmi"
    )
  )
  === JSON.stringify([
    "audio",
    "video",
  ]),
  "consulta deve poder detectar audio e video"
);

printResult(
  "Múltiplas intenções",
  "OK"
);


/* ==========================================================
   TESTE 13 — LIMITE DE TOKEN
   ========================================================== */

assert(
  detectCategoryIntent(
    taxonomy,
    "hdmi"
  ).includes(
    "video"
  ),
  "hdmi deve detectar video"
);

assert(
  !detectCategoryIntent(
    taxonomy,
    "hdmi"
  ).includes(
    "armazenamento"
  ),
  "hd não pode casar dentro de hdmi"
);

printResult(
  "Fronteira exata",
  "hd != hdmi"
);


/* ==========================================================
   TESTE 14 — TAXONOMIA INVÁLIDA
   ========================================================== */

const duplicateCategory =
  clone(
    taxonomyData
  );


duplicateCategory.categories.push(
  clone(
    duplicateCategory.categories[0]
  )
);


assertThrows(
  () =>
    prepareTaxonomy(
      duplicateCategory
    ),
  "categoria duplicada deve ser rejeitada"
);


const invalidGroupReference =
  clone(
    taxonomyData
  );


invalidGroupReference
  .groups[0]
  .category_ids = [
    "categoria-inexistente",
  ];


assertThrows(
  () =>
    prepareTaxonomy(
      invalidGroupReference
    ),
  "grupo com categoria inexistente deve ser rejeitado"
);


const unsupportedVersion =
  clone(
    taxonomyData
  );


unsupportedVersion.version =
  999;


assertThrows(
  () =>
    prepareTaxonomy(
      unsupportedVersion
    ),
  "versão desconhecida deve ser rejeitada"
);


printResult(
  "Fail-closed",
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
  + "DA TAXONOMIA JAVASCRIPT PASSARAM"
);

console.log(
  "Taxonomia JavaScript DATADARK V1.0"
);

console.log(
  "=============================================="
);
