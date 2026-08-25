/*
 * DATADARK TECNOLOGIA
 * Base de Conhecimento
 *
 * ETAPA 4 — Motor Inteligente de Pesquisa
 * Normalizador V1.0
 *
 * Responsabilidades:
 * - normalização Unicode;
 * - remoção de acentos;
 * - tokenização;
 * - equivalências técnicas conservadoras;
 * - comparação aproximada;
 * - preparação das consultas.
 *
 * Não acessa DOM.
 * Não carrega arquivos.
 * Não altera o índice.
 */


/* ==========================================================
   PALAVRAS DE BAIXO VALOR
   ========================================================== */

const LOW_VALUE_WORDS = new Set([
  "a",
  "as",
  "o",
  "os",
  "de",
  "da",
  "das",
  "do",
  "dos",
  "e",
  "em",
  "no",
  "nos",
  "na",
  "nas",
  "para",
  "por",
  "um",
  "uma",
  "uns",
  "umas",
]);


/* ==========================================================
   EQUIVALÊNCIAS TÉCNICAS

   Conservadoras por definição.

   Não devemos transformar conceitos apenas relacionados
   em sinônimos absolutos.
   ========================================================== */

const SYNONYM_GROUPS = [
  [
    "pc",
    "computador",
  ],

  [
    "laptop",
    "notebook",
  ],

  [
    "wifi",
    "wireless",
  ],

  [
    "ram",
    "memoria",
  ],

  [
    "hd",
    "hdd",
    "disco",
  ],

  [
    "psu",
    "fonte",
  ],

  [
    "bsod",
    "telaazul",
  ],
];


const SYNONYM_MAP = new Map();

for (const group of SYNONYM_GROUPS) {
  for (const token of group) {
    SYNONYM_MAP.set(
      token,
      new Set(group)
    );
  }
}


/* ==========================================================
   NORMALIZAÇÃO
   ========================================================== */

export function normalizeText(value) {
  if (
    value === null
    || value === undefined
  ) {
    return "";
  }

  let text = String(value);

  text = text
    .toLocaleLowerCase("pt-BR")
    .normalize("NFKD")
    .replace(
      /[\u0300-\u036f]/g,
      ""
    );

  /*
   * Unifica diferentes tipos de hífen.
   */
  text = text.replace(
    /[\u2010\u2011\u2012\u2013\u2014\u2212]/g,
    "-"
  );

  /*
   * Expressões técnicas equivalentes.
   */
  text = text
    .replace(
      /\bwi[\s-]*fi\b/g,
      "wifi"
    )
    .replace(
      /\btela\s+azul\b/g,
      "telaazul"
    );

  /*
   * Evita que & una palavras.
   */
  text = text.replace(
    /&/g,
    " e "
  );

  /*
   * Mantém somente caracteres úteis ao mecanismo.
   */
  text = text.replace(
    /[^a-z0-9]+/g,
    " "
  );

  return text
    .replace(
      /\s+/g,
      " "
    )
    .trim();
}


/* ==========================================================
   TOKENIZAÇÃO
   ========================================================== */

export function tokenize(value) {
  const normalized = normalizeText(
    value
  );

  if (!normalized) {
    return [];
  }

  return normalized
    .split(" ")
    .filter(Boolean);
}


/* ==========================================================
   TOKENS SIGNIFICATIVOS
   ========================================================== */

export function meaningfulTokens(tokens) {
  if (!Array.isArray(tokens)) {
    return [];
  }

  const filtered = tokens.filter(
    (token) =>
      token
      && !LOW_VALUE_WORDS.has(token)
  );

  /*
   * Se a consulta contiver somente palavras comuns,
   * mantemos os tokens originais.
   */
  return filtered.length
    ? filtered
    : tokens.filter(Boolean);
}


/* ==========================================================
   EXPANSÃO POR EQUIVALÊNCIA
   ========================================================== */

export function expandToken(token) {
  const normalized = normalizeText(
    token
  );

  if (!normalized) {
    return [];
  }

  const equivalents = (
    SYNONYM_MAP.get(normalized)
  );

  if (!equivalents) {
    return [normalized];
  }

  return Array.from(
    equivalents
  );
}


/* ==========================================================
   DISTÂNCIA DE LEVENSHTEIN
   ========================================================== */

export function levenshteinDistance(
  left,
  right,
  maxDistance = Infinity
) {
  const a = normalizeText(left);
  const b = normalizeText(right);

  if (a === b) {
    return 0;
  }

  if (!a) {
    return b.length;
  }

  if (!b) {
    return a.length;
  }

  if (
    Number.isFinite(maxDistance)
    && Math.abs(
      a.length - b.length
    ) > maxDistance
  ) {
    return maxDistance + 1;
  }

  let previous = new Array(
    b.length + 1
  );

  let current = new Array(
    b.length + 1
  );

  for (
    let column = 0;
    column <= b.length;
    column += 1
  ) {
    previous[column] = column;
  }

  for (
    let row = 1;
    row <= a.length;
    row += 1
  ) {
    current[0] = row;

    let rowMinimum = current[0];

    for (
      let column = 1;
      column <= b.length;
      column += 1
    ) {
      const substitutionCost = (
        a[row - 1] === b[column - 1]
          ? 0
          : 1
      );

      current[column] = Math.min(
        current[column - 1] + 1,
        previous[column] + 1,
        previous[column - 1]
          + substitutionCost
      );

      rowMinimum = Math.min(
        rowMinimum,
        current[column]
      );
    }

    if (
      Number.isFinite(maxDistance)
      && rowMinimum > maxDistance
    ) {
      return maxDistance + 1;
    }

    [
      previous,
      current,
    ] = [
      current,
      previous,
    ];
  }

  return previous[b.length];
}


/* ==========================================================
   LIMITE DE FUZZY MATCHING
   ========================================================== */

export function fuzzyDistanceLimit(
  token
) {
  const normalized = normalizeText(
    token
  );

  const length = normalized.length;

  if (length <= 3) {
    return 0;
  }

  if (length <= 7) {
    return 1;
  }

  return 2;
}


/* ==========================================================
   CORRESPONDÊNCIA APROXIMADA
   ========================================================== */

export function isFuzzyMatch(
  left,
  right
) {
  const a = normalizeText(left);
  const b = normalizeText(right);

  if (!a || !b) {
    return false;
  }

  const limit = Math.min(
    fuzzyDistanceLimit(a),
    fuzzyDistanceLimit(b)
  );

  if (limit === 0) {
    return a === b;
  }

  return (
    levenshteinDistance(
      a,
      b,
      limit
    ) <= limit
  );
}


/* ==========================================================
   PREPARAÇÃO DA CONSULTA
   ========================================================== */

export function prepareQuery(value) {
  const normalized = normalizeText(
    value
  );

  const allTokens = tokenize(
    normalized
  );

  const tokens = meaningfulTokens(
    allTokens
  );

  const expandedTokens = tokens.map(
    (token) => ({
      token,
      alternatives: expandToken(
        token
      ),
    })
  );

  return {
    raw:
      value === null
      || value === undefined
        ? ""
        : String(value),

    normalized,

    allTokens,

    tokens,

    expandedTokens,

    isEmpty:
      normalized.length === 0,
  };
}


/* ==========================================================
   UTILITÁRIO DE FRASES ORDENADAS
   ========================================================== */

export function tokensAppearInOrder(
  queryTokens,
  candidateTokens
) {
  if (
    !Array.isArray(queryTokens)
    || !Array.isArray(candidateTokens)
    || queryTokens.length === 0
    || candidateTokens.length === 0
  ) {
    return false;
  }

  let position = 0;

  for (
    const candidate
    of candidateTokens
  ) {
    if (
      candidate
      === queryTokens[position]
    ) {
      position += 1;

      if (
        position
        === queryTokens.length
      ) {
        return true;
      }
    }
  }

  return false;
}
