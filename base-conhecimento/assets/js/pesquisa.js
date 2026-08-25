/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 4 — Motor Inteligente de Pesquisa
 * Pesquisa V1.0
 *
 * Responsabilidades:
 * - preparar o índice para pesquisa;
 * - calcular relevância;
 * - aplicar cobertura;
 * - fuzzy matching controlado;
 * - ordenar resultados.
 *
 * Não manipula DOM.
 * Não carrega indice.json.
 */


import {
  normalizeText,
  tokenize,
  prepareQuery,
  isFuzzyMatch,
  tokensAppearInOrder,
} from "./normalizador.js";


/* ==========================================================
   CONFIGURAÇÃO
   ========================================================== */

export const SEARCH_DEFAULTS = Object.freeze({
  maxResults: 20,

  prefixMinimumLength: 4,

  fieldWeights: Object.freeze({
    title: 100,
    aliases: 90,
    keywords: 65,
    slug: 55,
    description: 40,
    category: 20,
  }),

  quality: Object.freeze({
    exact: 1.00,
    prefix: 0.78,
    fuzzy: 0.56,
  }),
});


/* ==========================================================
   CONVERSÃO DE CAMPOS FLEXÍVEIS
   ========================================================== */

function toStringArray(value) {
  if (Array.isArray(value)) {
    return value
      .map(
        (item) => String(item).trim()
      )
      .filter(Boolean);
  }

  if (
    value === null
    || value === undefined
  ) {
    return [];
  }

  const text = String(value).trim();

  if (!text) {
    return [];
  }

  return text
    .split(",")
    .map(
      (item) => item.trim()
    )
    .filter(Boolean);
}


/* ==========================================================
   SLUG DE FALLBACK
   ========================================================== */

function deriveSlug(article) {
  if (
    typeof article.slug === "string"
    && article.slug.trim()
  ) {
    return article.slug.trim();
  }

  if (
    typeof article.url !== "string"
    || !article.url.trim()
  ) {
    return "";
  }

  const filename = (
    article.url
      .split("/")
      .pop()
      || ""
  );

  return filename.replace(
    /\.html?$/i,
    ""
  );
}


/* ==========================================================
   PREPARAÇÃO DE UM ARTIGO
   ========================================================== */

function prepareArticle(article) {
  if (
    !article
    || typeof article !== "object"
  ) {
    return null;
  }

  const title = (
    typeof article.title === "string"
      ? article.title.trim()
      : ""
  );

  const url = (
    typeof article.url === "string"
      ? article.url.trim()
      : ""
  );

  if (!title || !url) {
    return null;
  }

  const slug = deriveSlug(
    article
  );

  const description = (
    typeof article.description
      === "string"
      ? article.description.trim()
      : ""
  );

  const category = (
    typeof article.category
      === "string"
      ? article.category.trim()
      : ""
  );

  const aliases = toStringArray(
    article.aliases
  );

  const keywords = toStringArray(
    article.keywords
  );

  const normalized = {
    title:
      normalizeText(title),

    description:
      normalizeText(description),

    category:
      normalizeText(category),

    slug:
      normalizeText(
        slug.replace(
          /-/g,
          " "
        )
      ),

    aliases:
      aliases.map(
        normalizeText
      ),

    keywords:
      keywords.map(
        normalizeText
      ),
  };

  const tokens = {
    title:
      tokenize(
        normalized.title
      ),

    description:
      tokenize(
        normalized.description
      ),

    category:
      tokenize(
        normalized.category
      ),

    slug:
      tokenize(
        normalized.slug
      ),

    aliases:
      normalized.aliases.map(
        tokenize
      ),

    keywords:
      normalized.keywords.map(
        tokenize
      ),
  };

  return {
    article: {
      ...article,
      title,
      url,
      slug,
      description,
      category,
      aliases,
      keywords,
    },

    normalized,

    tokens,
  };
}


/* ==========================================================
   PREPARAÇÃO DO ÍNDICE
   ========================================================== */

export function prepareIndex(
  articles
) {
  if (!Array.isArray(articles)) {
    throw new TypeError(
      "O índice da Base de Conhecimento deve ser um array."
    );
  }

  const prepared = [];

  for (const article of articles) {
    const item = prepareArticle(
      article
    );

    if (!item) {
      /*
       * Um item individual incompleto não deve
       * derrubar toda a pesquisa.
       */
      continue;
    }

    prepared.push(item);
  }

  return prepared;
}


/* ==========================================================
   QUALIDADE ENTRE DOIS TOKENS
   ========================================================== */

function tokenQuality(
  queryToken,
  candidateToken,
  options
) {
  if (
    !queryToken
    || !candidateToken
  ) {
    return 0;
  }

  if (
    queryToken
    === candidateToken
  ) {
    return options.quality.exact;
  }

  const shorterLength = Math.min(
    queryToken.length,
    candidateToken.length
  );

  if (
    shorterLength
      >= options.prefixMinimumLength
    && (
      queryToken.startsWith(
        candidateToken
      )
      || candidateToken.startsWith(
        queryToken
      )
    )
  ) {
    return options.quality.prefix;
  }

  if (
    isFuzzyMatch(
      queryToken,
      candidateToken
    )
  ) {
    return options.quality.fuzzy;
  }

  return 0;
}


/* ==========================================================
   MELHOR MATCH DE UM TOKEN EM UM CAMPO
   ========================================================== */

function bestTokenMatch(
  alternatives,
  candidateTokens,
  fieldWeight,
  options
) {
  let bestQuality = 0;

  for (
    const alternative
    of alternatives
  ) {
    for (
      const candidateToken
      of candidateTokens
    ) {
      const quality = tokenQuality(
        alternative,
        candidateToken,
        options
      );

      if (quality > bestQuality) {
        bestQuality = quality;

        if (
          bestQuality
          === options.quality.exact
        ) {
          break;
        }
      }
    }

    if (
      bestQuality
      === options.quality.exact
    ) {
      break;
    }
  }

  return {
    quality: bestQuality,

    score:
      fieldWeight
      * bestQuality,
  };
}


/* ==========================================================
   MELHOR MATCH EM LISTA DE CAMPOS
   ========================================================== */

function bestArrayFieldMatch(
  alternatives,
  tokenGroups,
  fieldWeight,
  options
) {
  let best = {
    quality: 0,
    score: 0,
  };

  for (
    const candidateTokens
    of tokenGroups
  ) {
    const result = bestTokenMatch(
      alternatives,
      candidateTokens,
      fieldWeight,
      options
    );

    if (
      result.score > best.score
    ) {
      best = result;
    }
  }

  return best;
}


/* ==========================================================
   COBERTURA MÍNIMA
   ========================================================== */

function requiredCoverage(
  tokenCount
) {
  if (tokenCount <= 1) {
    return 1;
  }

  if (tokenCount === 2) {
    return 1;
  }

  if (tokenCount === 3) {
    return 2 / 3;
  }

  return 0.60;
}


/* ==========================================================
   BÔNUS DE FRASE
   ========================================================== */

function phraseBonus(
  preparedArticle,
  query
) {
  const queryText = (
    query.normalized
  );

  if (!queryText) {
    return 0;
  }

  const {
    normalized,
    tokens,
  } = preparedArticle;

  let bonus = 0;


  /* --------------------------------------------------
     TÍTULO
     -------------------------------------------------- */

  if (
    normalized.title
    === queryText
  ) {
    bonus += 320;
  }

  else if (
    normalized.title.includes(
      queryText
    )
  ) {
    bonus += 220;
  }

  else if (
    tokensAppearInOrder(
      query.tokens,
      tokens.title
    )
  ) {
    bonus += 140;
  }


  /* --------------------------------------------------
     ALIASES
     -------------------------------------------------- */

  for (
    let index = 0;
    index < normalized.aliases.length;
    index += 1
  ) {
    const alias = (
      normalized.aliases[index]
    );

    if (alias === queryText) {
      bonus += 280;
      break;
    }

    if (
      alias.includes(
        queryText
      )
    ) {
      bonus = Math.max(
        bonus,
        180
      );
      continue;
    }

    if (
      tokensAppearInOrder(
        query.tokens,
        tokens.aliases[index]
      )
    ) {
      bonus = Math.max(
        bonus,
        120
      );
    }
  }


  /* --------------------------------------------------
     SLUG
     -------------------------------------------------- */

  if (
    normalized.slug
    === queryText
  ) {
    bonus += 170;
  }

  return bonus;
}


/* ==========================================================
   SCORE DE UM ARTIGO
   ========================================================== */

export function scoreArticle(
  preparedArticle,
  queryInput,
  customOptions = {}
) {
  const query = (
    typeof queryInput === "string"
      ? prepareQuery(queryInput)
      : queryInput
  );

  if (
    !query
    || query.isEmpty
    || query.tokens.length === 0
  ) {
    return null;
  }

  const options = {
    ...SEARCH_DEFAULTS,
    ...customOptions,

    fieldWeights: {
      ...SEARCH_DEFAULTS.fieldWeights,
      ...(
        customOptions.fieldWeights
        || {}
      ),
    },

    quality: {
      ...SEARCH_DEFAULTS.quality,
      ...(
        customOptions.quality
        || {}
      ),
    },
  };

  const matchedTokens = [];

  let tokenScore = 0;
  let titleMatches = 0;


  for (
    const expanded
    of query.expandedTokens
  ) {
    const alternatives = (
      expanded.alternatives
    );

    const matches = [];


    /* TITLE */

    const titleMatch = (
      bestTokenMatch(
        alternatives,
        preparedArticle.tokens.title,
        options.fieldWeights.title,
        options
      )
    );

    matches.push({
      field: "title",
      ...titleMatch,
    });


    /* ALIASES */

    const aliasMatch = (
      bestArrayFieldMatch(
        alternatives,
        preparedArticle.tokens.aliases,
        options.fieldWeights.aliases,
        options
      )
    );

    matches.push({
      field: "aliases",
      ...aliasMatch,
    });


    /* KEYWORDS */

    const keywordMatch = (
      bestArrayFieldMatch(
        alternatives,
        preparedArticle.tokens.keywords,
        options.fieldWeights.keywords,
        options
      )
    );

    matches.push({
      field: "keywords",
      ...keywordMatch,
    });


    /* SLUG */

    const slugMatch = (
      bestTokenMatch(
        alternatives,
        preparedArticle.tokens.slug,
        options.fieldWeights.slug,
        options
      )
    );

    matches.push({
      field: "slug",
      ...slugMatch,
    });


    /* DESCRIPTION */

    const descriptionMatch = (
      bestTokenMatch(
        alternatives,
        preparedArticle.tokens.description,
        options.fieldWeights.description,
        options
      )
    );

    matches.push({
      field: "description",
      ...descriptionMatch,
    });


    /* CATEGORY */

    const categoryMatch = (
      bestTokenMatch(
        alternatives,
        preparedArticle.tokens.category,
        options.fieldWeights.category,
        options
      )
    );

    matches.push({
      field: "category",
      ...categoryMatch,
    });


    matches.sort(
      (left, right) =>
        right.score - left.score
    );

    const best = matches[0];


    if (
      best
      && best.score > 0
    ) {
      matchedTokens.push(
        expanded.token
      );

      tokenScore += best.score;

      if (
        best.field === "title"
      ) {
        titleMatches += 1;
      }
    }
  }


  const coverage = (
    matchedTokens.length
    / query.tokens.length
  );

  if (
    coverage
    < requiredCoverage(
      query.tokens.length
    )
  ) {
    return null;
  }


  /* ======================================================
     BÔNUS DE COBERTURA
     ====================================================== */

  let coverageBonus = 0;

  if (coverage === 1) {
    coverageBonus = 180;
  }

  else if (coverage >= 0.75) {
    coverageBonus = 90;
  }

  else if (coverage >= 0.60) {
    coverageBonus = 40;
  }


  /* ======================================================
     BÔNUS POR MATCH NO TÍTULO
     ====================================================== */

  const titleBonus = (
    titleMatches * 24
  );


  /* ======================================================
     FRASE
     ====================================================== */

  const directPhraseBonus = (
    phraseBonus(
      preparedArticle,
      query
    )
  );


  const score = (
    tokenScore
    + coverageBonus
    + titleBonus
    + directPhraseBonus
  );


  /*
   * Barreira absoluta contra resultados
   * excessivamente fracos.
   */
  if (score < 45) {
    return null;
  }


  return {
    article:
      preparedArticle.article,

    score,

    coverage,

    matchedTokens,

    titleMatches,
  };
}


/* ==========================================================
   PESQUISA
   ========================================================== */

export function searchArticles(
  preparedIndex,
  queryInput,
  customOptions = {}
) {
  if (!Array.isArray(preparedIndex)) {
    throw new TypeError(
      "O índice preparado deve ser um array."
    );
  }

  const query = prepareQuery(
    queryInput
  );

  if (
    query.isEmpty
    || query.tokens.length === 0
  ) {
    return [];
  }

  const options = {
    ...SEARCH_DEFAULTS,
    ...customOptions,
  };

  const scored = [];


  for (
    const preparedArticle
    of preparedIndex
  ) {
    const result = scoreArticle(
      preparedArticle,
      query,
      options
    );

    if (result) {
      scored.push(result);
    }
  }


  scored.sort(
    (left, right) => {

      if (
        right.score
        !== left.score
      ) {
        return (
          right.score
          - left.score
        );
      }

      if (
        right.coverage
        !== left.coverage
      ) {
        return (
          right.coverage
          - left.coverage
        );
      }

      if (
        right.titleMatches
        !== left.titleMatches
      ) {
        return (
          right.titleMatches
          - left.titleMatches
        );
      }

      return (
        left.article.title
          .localeCompare(
            right.article.title,
            "pt-BR",
            {
              sensitivity: "base",
            }
          )
      );
    }
  );


  return scored.slice(
    0,
    options.maxResults
  );
}
