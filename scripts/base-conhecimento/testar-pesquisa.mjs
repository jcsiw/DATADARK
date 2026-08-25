/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 4 — Testes do Motor de Pesquisa V1.0
 */


import {
  normalizeText,
  tokenize,
  isFuzzyMatch,
} from "../../base-conhecimento/assets/js/normalizador.js";


import {
  CATEGORY_INTENT_BONUS,
  prepareIndex,
  filterPreparedIndex,
  listArticles,
  searchArticles,
} from "../../base-conhecimento/assets/js/pesquisa.js";


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


function firstTitle(
  preparedIndex,
  query
) {
  const results = searchArticles(
    preparedIndex,
    query
  );

  return (
    results[0]
      ?.article
      ?.title
    || null
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
   DATASET CONTROLADO
   ========================================================== */

const articles = [

  {
    slug:
      "computador-nao-liga-e-nao-emite-nenhum-sinal",

    title:
      "Computador não liga e não emite nenhum sinal",

    description:
      "Diagnóstico para computador sem sinal de energia ou sem resposta ao botão de ligar.",

    url:
      "artigos/computador-nao-liga-e-nao-emite-nenhum-sinal.html",

    category_id:
      "hardware",

    category:
      "Hardware",

    keywords: [
      "computador",
      "energia",
      "fonte",
      "nao liga",
    ],

    aliases: [
      "pc morto",
      "computador morto",
      "nao da sinal",
      "sem sinal",
    ],
  },


  {
    slug:
      "wi-fi-conecta-mas-fica-sem-internet",

    title:
      "Wi-Fi conecta mas fica sem internet",

    description:
      "Diagnóstico quando a rede sem fio conecta mas não permite acesso à internet.",

    url:
      "artigos/wi-fi-conecta-mas-fica-sem-internet.html",

    category_id:
      "wifi",

    category:
      "Wi-Fi",

    keywords: [
      "wifi",
      "internet",
      "rede",
      "wireless",
    ],

    aliases: [
      "wifi sem internet",
      "wireless sem internet",
    ],
  },


  {
    slug:
      "reinicia-ao-abrir-jogos-e-programas-pesados",

    title:
      "Reinicia ao abrir jogos e programas pesados",

    description:
      "Diagnóstico de reinicialização durante jogos, aplicações pesadas e alta carga.",

    url:
      "artigos/reinicia-ao-abrir-jogos-e-programas-pesados.html",

    category_id:
      "hardware",

    category:
      "Hardware",

    keywords: [
      "reinicia",
      "jogo",
      "carga",
      "fonte",
    ],

    aliases: [
      "pc reinicia jogando",
      "computador reinicia em jogos",
    ],
  },


  {
    slug:
      "computador-reinicia-sozinho-durante-o-uso",

    title:
      "Computador reinicia sozinho durante o uso",

    description:
      "Diagnóstico geral para reinicializações inesperadas durante a utilização do computador.",

    url:
      "artigos/computador-reinicia-sozinho-durante-o-uso.html",

    category_id:
      "hardware",

    category:
      "Hardware",

    keywords: [
      "computador",
      "reinicia",
      "reinicializacao",
    ],

    aliases: [
      "pc reinicia sozinho",
    ],
  },


  {
    slug:
      "restauracao-do-sistema-nao-conclui",

    title:
      "Restauração do sistema não conclui",

    description:
      "Diagnóstico para falha ao concluir a restauração e recuperação do Windows.",

    url:
      "artigos/restauracao-do-sistema-nao-conclui.html",

    category_id:
      "windows",

    category:
      "Windows",

    keywords: [
      "restauracao",
      "recuperacao",
      "windows",
      "sistema",
    ],

    aliases: [
      "restauracao nao conclui",
      "restauracao falha",
    ],
  },


  {
    slug:
      "tela-azul-com-erro-de-memoria",

    title:
      "Tela azul com erro de memória",

    description:
      "Diagnóstico de tela azul associada a falhas de memória RAM.",

    url:
      "artigos/tela-azul-com-erro-de-memoria.html",

    category_id:
      "windows",

    category:
      "Windows",

    keywords: [
      "bsod",
      "memoria",
      "ram",
      "tela azul",
    ],

    aliases: [
      "bsod memoria",
      "tela azul ram",
    ],
  },


  {
    slug:
      "ssd-nao-aparece-na-bios-nem-no-sistema",

    title:
      "SSD não aparece na BIOS nem no sistema",

    description:
      "Diagnóstico para SSD não detectado pela BIOS ou pelo sistema operacional.",

    url:
      "artigos/ssd-nao-aparece-na-bios-nem-no-sistema.html",

    category_id:
      "armazenamento",

    category:
      "SSD / HD",

    keywords: [
      "ssd",
      "bios",
      "disco",
      "armazenamento",
    ],

    aliases: [
      "ssd nao reconhecido",
      "ssd sumiu",
    ],
  },


  {
    slug:
      "ordem-de-servico",

    title:
      "Ordem de Serviço",

    description:
      "Documento técnico para abertura e registro do atendimento.",

    url:
      "artigos/ordem-de-servico.html",

    category_id:
      "documentos",

    category:
      "Documentos",

    keywords: [
      "ordem",
      "servico",
      "atendimento",
      "documento",
    ],

    aliases: [
      "os",
      "ordem de servico",
    ],
  },


  {
    slug:
      "laudo-tecnico",

    title:
      "Laudo Técnico",

    description:
      "Documento para registrar diagnóstico, testes e serviço executado.",

    url:
      "artigos/laudo-tecnico.html",

    category_id:
      "documentos",

    category:
      "Documentos",

    keywords: [
      "laudo",
      "diagnostico",
      "documento",
    ],

    aliases: [
      "relatorio tecnico",
    ],
  },


  {
    slug:
      "termo-de-garantia",

    title:
      "Termo de Garantia",

    description:
      "Documento com prazo, cobertura e condições da garantia do serviço.",

    url:
      "artigos/termo-de-garantia.html",

    category_id:
      "documentos",

    category:
      "Documentos",

    keywords: [
      "garantia",
      "termo",
      "documento",
    ],

    aliases: [
      "garantia do servico",
    ],
  },

];


/* ==========================================================
   PREPARAÇÃO
   ========================================================== */

const index = prepareIndex(
  articles
);

assert(
  index.length
  === articles.length,
  "todos os artigos válidos devem ser preparados"
);

printResult(
  "Índice preparado",
  `${index.length} artigos`
);


/* ==========================================================
   TESTE 1 — ACENTOS
   ========================================================== */

assert(
  normalizeText(
    "Restauração NÃO Conclui!"
  )
  ===
  "restauracao nao conclui",
  "normalização de acentos"
);

printResult(
  "Normalização",
  normalizeText(
    "Restauração NÃO Conclui!"
  )
);


/* ==========================================================
   TESTE 2 — WI-FI
   ========================================================== */

assert(
  normalizeText(
    "Wi-Fi"
  )
  === "wifi",
  "normalização de Wi-Fi"
);

assert(
  normalizeText(
    "WI FI"
  )
  === "wifi",
  "normalização de Wi Fi"
);

printResult(
  "Wi-Fi",
  normalizeText("WI FI")
);


/* ==========================================================
   TESTE 3 — TOKENIZAÇÃO
   ========================================================== */

assert(
  JSON.stringify(
    tokenize(
      "computador reinicia jogos"
    )
  )
  ===
  JSON.stringify([
    "computador",
    "reinicia",
    "jogos",
  ]),
  "tokenização"
);

printResult(
  "Tokenização",
  tokenize(
    "computador reinicia jogos"
  ).join(" | ")
);


/* ==========================================================
   TESTE 4 — FUZZY
   ========================================================== */

assert(
  isFuzzyMatch(
    "comclui",
    "conclui"
  ),
  "erro simples deve ser tolerado"
);

assert(
  !isFuzzyMatch(
    "rede",
    "ram"
  ),
  "palavras curtas diferentes não podem gerar fuzzy match"
);

printResult(
  "Fuzzy",
  "comclui → conclui"
);


/* ==========================================================
   TESTE 5 — RESTAURAÇÃO
   ========================================================== */

assert(
  firstTitle(
    index,
    "restauracao nao conclui"
  )
  ===
  "Restauração do sistema não conclui",
  "restauração deve ocupar a primeira posição"
);

printResult(
  "Pesquisa restauração",
  firstTitle(
    index,
    "restauracao nao conclui"
  )
);


/* ==========================================================
   TESTE 6 — CASE + WI-FI
   ========================================================== */

assert(
  firstTitle(
    index,
    "WIFI"
  )
  ===
  "Wi-Fi conecta mas fica sem internet",
  "WIFI deve encontrar artigo Wi-Fi"
);

printResult(
  "Pesquisa WIFI",
  firstTitle(
    index,
    "WIFI"
  )
);


/* ==========================================================
   TESTE 7 — FRASE WI-FI SEM INTERNET
   ========================================================== */

assert(
  firstTitle(
    index,
    "wifi sem internet"
  )
  ===
  "Wi-Fi conecta mas fica sem internet",
  "wifi sem internet deve priorizar o artigo correto"
);

printResult(
  "Pesquisa wifi sem internet",
  firstTitle(
    index,
    "wifi sem internet"
  )
);


/* ==========================================================
   TESTE 8 — ERRO DE DIGITAÇÃO
   ========================================================== */

assert(
  firstTitle(
    index,
    "comclui"
  )
  ===
  "Restauração do sistema não conclui",
  "comclui deve encontrar conclui"
);

printResult(
  "Pesquisa com erro",
  firstTitle(
    index,
    "comclui"
  )
);


/* ==========================================================
   TESTE 9 — ALIAS
   ========================================================== */

assert(
  firstTitle(
    index,
    "pc morto"
  )
  ===
  "Computador não liga e não emite nenhum sinal",
  "alias pc morto"
);

printResult(
  "Pesquisa por alias",
  firstTitle(
    index,
    "pc morto"
  )
);


/* ==========================================================
   TESTE 10 — COBERTURA E RANKING
   ========================================================== */

assert(
  firstTitle(
    index,
    "reinicia jogo"
  )
  ===
  "Reinicia ao abrir jogos e programas pesados",
  "reinicia jogo deve priorizar artigo específico"
);

printResult(
  "Ranking reinicia jogo",
  firstTitle(
    index,
    "reinicia jogo"
  )
);


/* ==========================================================
   TESTE 11 — BSOD / MEMÓRIA
   ========================================================== */

assert(
  firstTitle(
    index,
    "bsod ram"
  )
  ===
  "Tela azul com erro de memória",
  "bsod ram deve encontrar tela azul de memória"
);

printResult(
  "Pesquisa BSOD",
  firstTitle(
    index,
    "bsod ram"
  )
);


/* ==========================================================
   TESTE 12 — DOCUMENTO
   ========================================================== */

assert(
  firstTitle(
    index,
    "ordem de servico"
  )
  ===
  "Ordem de Serviço",
  "ordem de serviço deve localizar documento"
);

printResult(
  "Pesquisa documento",
  firstTitle(
    index,
    "ordem de servico"
  )
);


/* ==========================================================
   TESTE 13 — PONTUAÇÃO
   ========================================================== */

assert(
  firstTitle(
    index,
    "Wi-Fi!!!"
  )
  ===
  "Wi-Fi conecta mas fica sem internet",
  "pontuação não deve afetar pesquisa"
);

printResult(
  "Pontuação",
  firstTitle(
    index,
    "Wi-Fi!!!"
  )
);


/* ==========================================================
   TESTE 14 — CONSULTA SEM RELAÇÃO
   ========================================================== */

const irrelevant = searchArticles(
  index,
  "abacaxi quantum"
);

assert(
  irrelevant.length === 0,
  "consulta irrelevante deve retornar zero resultados"
);

printResult(
  "Consulta irrelevante",
  `${irrelevant.length} resultados`
);


/* ==========================================================
   TESTE 15 — CONSULTA VAZIA
   ========================================================== */

const empty = searchArticles(
  index,
  "   "
);

assert(
  empty.length === 0,
  "consulta vazia deve retornar zero resultados"
);

printResult(
  "Consulta vazia",
  `${empty.length} resultados`
);


/* ==========================================================
   TESTE 16 — RANKING DETERMINÍSTICO
   ========================================================== */

const rankingA = searchArticles(
  index,
  "reinicia"
).map(
  (item) => item.article.title
);

const rankingB = searchArticles(
  index,
  "reinicia"
).map(
  (item) => item.article.title
);

assert(
  JSON.stringify(rankingA)
  ===
  JSON.stringify(rankingB),
  "ranking deve ser determinístico"
);

printResult(
  "Ranking determinístico",
  "OK"
);



/* ==========================================================
   TESTE 17 — CONTRATO CATEGORY_ID
   ========================================================== */

const preparedWifi =
  index.find(
    (item) =>
      item.article.slug
      ===
      "wi-fi-conecta-mas-fica-sem-internet"
  );


assert(
  preparedWifi
    ?.article
    ?.category_id
    === "wifi",
  "artigo Wi-Fi deve preservar category_id canônico"
);


assert(
  preparedWifi
    ?.article
    ?.category
    === "Wi-Fi",
  "artigo Wi-Fi deve preservar label de apresentação"
);


const missingCategoryId =
  prepareIndex([
    {
      slug:
        "artigo-sem-category-id",

      title:
        "Artigo sem category id",

      url:
        "artigos/artigo-sem-category-id.html",

      category:
        "Hardware",
    },
  ]);


assert(
  missingCategoryId.length === 0,
  "artigo sem category_id deve ser ignorado"
);


printResult(
  "Contrato category_id",
  "OK"
);


/* ==========================================================
   TESTE 18 — HARD FILTER
   ========================================================== */

const documentArticles =
  filterPreparedIndex(
    index,
    [
      "documentos",
    ]
  );


assert(
  documentArticles.length === 3,
  "filtro documentos deve retornar três artigos"
);


assert(
  documentArticles.every(
    (item) =>
      item.article.category_id
      === "documentos"
  ),
  "hard filter não pode permitir categoria externa"
);


const networkArticles =
  filterPreparedIndex(
    index,
    [
      "rede",
      "wifi",
    ]
  );


assert(
  networkArticles.length === 1,
  "grupo rede/wifi deve aplicar OR entre category_ids"
);


assert(
  networkArticles[0]
    .article
    .category_id
    === "wifi",
  "artigo Wi-Fi deve pertencer ao conjunto rede/wifi"
);


printResult(
  "Hard filter",
  "OK"
);


/* ==========================================================
   TESTE 19 — PESQUISA + FILTRO
   ========================================================== */

const wifiFiltered =
  searchArticles(
    index,
    "wifi",
    {
      categoryIds: [
        "wifi",
      ],

      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  wifiFiltered.length === 1,
  "pesquisa WIFI filtrada por wifi deve retornar artigo"
);


assert(
  wifiFiltered[0]
    .article
    .category_id
    === "wifi",
  "pesquisa filtrada deve respeitar category_id"
);


const wifiBlockedByNetwork =
  searchArticles(
    index,
    "wifi",
    {
      categoryIds: [
        "rede",
      ],

      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  wifiBlockedByNetwork.length === 0,
  "hard filter rede deve excluir artigo category_id wifi"
);


printResult(
  "Pesquisa AND categoria",
  "OK"
);


/* ==========================================================
   TESTE 20 — LISTAGEM SEM CONSULTA
   ========================================================== */

const listedDocuments =
  listArticles(
    index,
    {
      categoryIds: [
        "documentos",
      ],
    }
  );


const listedDocumentTitles =
  listedDocuments.map(
    (item) =>
      item.article.title
  );


assert(
  JSON.stringify(
    listedDocumentTitles
  )
  ===
  JSON.stringify([
    "Laudo Técnico",
    "Ordem de Serviço",
    "Termo de Garantia",
  ]),
  "documentos devem ser listados alfabeticamente"
);


assert(
  searchArticles(
    index,
    ""
  ).length === 0,
  "listArticles não pode alterar contrato de consulta vazia"
);


printResult(
  "Listagem categorial",
  listedDocumentTitles.join(" | ")
);


/* ==========================================================
   TESTE 21 — BÔNUS DE INTENÇÃO CATEGORIAL
   ========================================================== */

assert(
  CATEGORY_INTENT_BONUS === 30,
  "bônus categorial oficial deve ser 30"
);


const bonusIndex =
  prepareIndex([
    {
      slug:
        "falha-geral-rede",

      title:
        "Falha geral de conexão",

      description:
        "Diagnóstico de falha geral.",

      url:
        "artigos/falha-geral-rede.html",

      category_id:
        "rede",

      category:
        "Rede",

      keywords: [
        "falha",
      ],

      aliases: [],
    },

    {
      slug:
        "falha-geral-wifi",

      title:
        "Falha geral de conexão",

      description:
        "Diagnóstico de falha geral.",

      url:
        "artigos/falha-geral-wifi.html",

      category_id:
        "wifi",

      category:
        "Wi-Fi",

      keywords: [
        "falha",
      ],

      aliases: [],
    },
  ]);


const withoutIntent =
  searchArticles(
    bonusIndex,
    "falha",
    {
      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


const withIntent =
  searchArticles(
    bonusIndex,
    "falha",
    {
      categoryIntentIds: [
        "wifi",
      ],

      maxResults:
        Number.MAX_SAFE_INTEGER,
    }
  );


assert(
  withoutIntent.length === 2,
  "dataset de bônus deve produzir dois resultados"
);


assert(
  withIntent.length === 2,
  "bônus não pode excluir resultados"
);


assert(
  withIntent[0]
    .article
    .category_id
    === "wifi",
  "intenção wifi deve priorizar artigo wifi"
);


const wifiWithIntent =
  withIntent.find(
    (item) =>
      item.article.category_id
      === "wifi"
  );


const networkWithIntent =
  withIntent.find(
    (item) =>
      item.article.category_id
      === "rede"
  );


assert(
  wifiWithIntent.categoryIntentBonus
    === 30,
  "artigo da categoria intencional deve receber +30"
);


assert(
  networkWithIntent.categoryIntentBonus
    === 0,
  "categoria não intencional não pode receber bônus"
);


assert(
  wifiWithIntent.score
    - networkWithIntent.score
    === 30,
  "diferença produzida pela intenção deve ser exatamente +30"
);


printResult(
  "Bônus categorial",
  "+30"
);


/* ==========================================================
   TESTE 22 — CATEGORY IDS FAIL-CLOSED
   ========================================================== */

let invalidCategoryIdRejected =
  false;


try {

  filterPreparedIndex(
    index,
    [
      " wifi ",
    ]
  );

}

catch {

  invalidCategoryIdRejected =
    true;

}


assert(
  invalidCategoryIdRejected,
  "category_id com espaços externos deve ser rejeitado"
);


let unknownShapeRejected =
  false;


try {

  filterPreparedIndex(
    index,
    "wifi"
  );

}

catch {

  unknownShapeRejected =
    true;

}


assert(
  unknownShapeRejected,
  "categoryIds deve exigir array ou null"
);


printResult(
  "Category IDs fail-closed",
  "OK"
);


/* ==========================================================
   RESULTADO
   ========================================================== */

console.log();
console.log(
  "=========================================="
);

console.log(
  "RESULTADO: TODOS OS TESTES PASSARAM"
);

console.log(
  "Motor de Pesquisa DATADARK V1.0"
);

console.log(
  "=========================================="
);
