"""How prose and LaTeX become search words, and how a consumer's words reach the ledger's.

One tokenizer serves every reader that ranks or matches words: `mdept.query`'s
ranked search, the synonym expansion, and the bench. A ledger Statement is LaTeX
source, and a keyword ranker reads `\\le` as noise unless something says it means
"at most". `LATEX_WORDS` is that something: a macro with a meaning becomes its
words, a macro that only formats (`\\text`, `\\mathrm`, `\\left`) becomes
nothing, and any other macro becomes its own name (`\\nabla` reads as nabla).

A token is lower case, either an entry ID (`md_0007`, kept whole so an ID in a
query still finds its entry) or a run of letters and digits. Single letters are
dropped (they are the variables of every statement and select nothing), English
stopwords are dropped, and `stem` folds a plural and an `-ing` or `-ed` ending
(`conditioning`, `conditioned` and `conditions` all read as `condition`).

`ledger/SYNONYMS.yaml` in the public repo is the family's one synonym list: each
pair maps a phrase a consumer types to the phrase the ledger uses. A query that
carries the consumer phrase is matched as if it carried either phrase
(`expand`). The pairs are read at query time and never written into an entry.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from . import ConfigError

#: Where the synonym list lives, relative to the public repo's root.
SYNONYMS_PATH = "ledger/SYNONYMS.yaml"
SYNONYM_KEYS = ("consumer", "ledger")

#: LaTeX macros that carry meaning, by macro name (no backslash), to the words a
#: reader would type for them. Greek letters are spelled out; relations become
#: their English reading.
LATEX_WORDS = {
    # Greek letters, lower and upper case alike.
    **{name: name.lower() for name in (
        "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta",
        "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "pi", "varpi", "rho",
        "varrho", "sigma", "varsigma", "tau", "upsilon", "phi", "varphi", "chi", "psi",
        "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon",
        "Phi", "Psi", "Omega",
    )},
    # Relations.
    "le": "at most", "leq": "at most", "leqslant": "at most",
    "ge": "at least", "geq": "at least", "geqslant": "at least",
    "lt": "less than", "gt": "greater than",
    "neq": "not equal", "ne": "not equal",
    "approx": "approximately", "sim": "asymptotic", "simeq": "approximately",
    "equiv": "equivalent", "propto": "proportional",
    "ll": "much less", "gg": "much greater",
    "in": "in", "notin": "not in", "subset": "subset", "subseteq": "subset",
    "supset": "superset", "supseteq": "superset",
    "to": "to", "mapsto": "maps to", "rightarrow": "implies", "Rightarrow": "implies",
    "implies": "implies", "iff": "if and only if", "Leftrightarrow": "if and only if",
    "forall": "for all", "exists": "exists", "nexists": "no",
    "cap": "intersection", "cup": "union", "bigcap": "intersection", "bigcup": "union",
    "setminus": "minus", "emptyset": "empty set", "varnothing": "empty set",
    "times": "times", "otimes": "tensor product", "oplus": "direct sum",
    "circ": "composed", "perp": "orthogonal",
    # Operators and named functions.
    "sum": "sum", "prod": "product", "int": "integral", "oint": "integral",
    "iint": "integral", "partial": "partial derivative", "nabla": "nabla gradient",
    "infty": "infinity", "lim": "limit", "limsup": "limit superior",
    "liminf": "limit inferior", "sup": "supremum", "inf": "infimum", "max": "maximum",
    "min": "minimum", "arg": "argument", "det": "determinant", "tr": "trace",
    "rank": "rank", "ker": "kernel", "dim": "dimension", "deg": "degree",
    "exp": "exponential", "log": "logarithm", "ln": "logarithm",
    "sin": "sine", "cos": "cosine", "tan": "tangent", "sinh": "hyperbolic sine",
    "cosh": "hyperbolic cosine", "tanh": "hyperbolic tangent", "coth": "hyperbolic cotangent",
    "sech": "hyperbolic secant", "sqrt": "square root", "Re": "real part",
    "Im": "imaginary part", "overline": "conjugate", "bar": "conjugate",
    "hat": "transform", "dot": "time derivative", "ddot": "second derivative",
    "binom": "binomial", "gcd": "gcd", "mod": "mod", "pmod": "mod",
    "langle": "average", "Pr": "probability",
}

#: LaTeX macros that only format: they become nothing. A macro absent from both
#: tables becomes its own name.
LATEX_SILENT = frozenset({
    "text", "textrm", "textit", "textbf", "mathrm", "mathbf", "mathit", "mathsf",
    "mathtt", "mathfrak", "mathscr", "mathbb", "mathcal", "rangle", "boldsymbol", "bm", "operatorname", "displaystyle",
    "textstyle", "scriptstyle", "left", "right", "bigl", "bigr", "Bigl", "Bigr", "big",
    "Big", "bigg", "Bigg", "middle", "frac", "tfrac", "dfrac", "cfrac", "quad", "qquad",
    "cdot", "cdots", "ldots", "dots", "vdots", "ddots", "label", "tag", "nonumber",
    "begin", "end", "hline", "mid", "vert", "Vert", "lvert", "rvert", "lVert", "rVert",
    "lfloor", "rfloor", "lceil", "rceil", "colon", "prime", "star", "ast", "top",
    "intercal", "dagger", "widetilde", "tilde", "widehat", "underline", "overset",
    "underset", "stackrel", "limits", "nolimits", "phantom", "hphantom", "vphantom",
    "mathop", "mathbin", "mathrel", "aligned", "cases", "pmatrix", "bmatrix", "matrix",
    "qed", "square", "blacksquare", "triangleq", "coloneqq", "eqqcolon", "define",
})

#: English words that select nothing.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before
being below between both but by can could did do does doing down during each for
from further had has have having he her here hers him his how i if into is it its itself
just me my no nor not of off on once only or other our ours out over own same
she should so some such than that the their theirs them then there these they this
those through to too under until up very was we were what when where which while who
whom why will with would you your yours let given every whenever holds hold true
""".split())

_MACRO_RE = re.compile(r"\\([A-Za-z]+)")
_SPACING_RE = re.compile(r"\\[,;:!> ]")
_TOKEN_RE = re.compile(r"md_\d{4}|[a-z0-9]+")
#: Words that end like a plural and are not one.
_UNCHANGED = frozenset({"series", "species", "lens", "less", "always", "whereas", "perhaps"})


def latex_to_words(text: str) -> str:
    """`text` with every LaTeX macro replaced by its words, by nothing, or by its own name."""

    def word(match: re.Match) -> str:
        name = match.group(1)
        if name in LATEX_SILENT:
            return " "
        return f" {LATEX_WORDS.get(name, name)} "

    return _MACRO_RE.sub(word, _SPACING_RE.sub(" ", str(text)))


def stem(word: str) -> str:
    """`word` with a plural, `-ing` or `-ed` ending folded: `eigenvalues`, `learning`, `learned` to their root.

    A light suffix stripper, not Porter: the plural first, then `-ing` or `-ed`
    when at least four letters remain, then a doubled final consonant undoubled
    (`mapping` to `map`). Query and ledger go through the same function, so a
    root that is not an English word (`deflat`) still matches itself.
    """
    if word in _UNCHANGED:
        return word
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz" and word[-1] not in "aeiou":
                word = word[:-1]
            break
    return word


def tokens(text: str) -> list[str]:
    """The search tokens of a piece of prose or LaTeX, in order."""
    out = []
    for raw in _TOKEN_RE.findall(latex_to_words(text).lower()):
        if raw in STOPWORDS or (len(raw) == 1 and not raw.isdigit()):
            continue
        out.append(stem(raw))
    return out


# --- display ---------------------------------------------------------------

_UNWRAP_RE = re.compile(r"\\(?:text|textrm|mathrm|operatorname)\{([^{}]*)\}")


def display(text: str) -> str:
    """A Statement on one line for a reader: whitespace collapsed, `$`, `**` and `\\text{}` wrappers gone.

    The rest of the LaTeX stays as written, because the reader of a catalog line is
    an LLM that reads LaTeX source fluently; only the wrappers that cost characters
    and say nothing are removed.
    """
    flat = _UNWRAP_RE.sub(r"\1", str(text).replace("$$", " ").replace("$", "").replace("**", ""))
    flat = _SPACING_RE.sub(" ", flat)
    return " ".join(flat.split())


def cut(text: str, width: int) -> str:
    """`text` on one line, cut to `width` characters with an ellipsis when longer."""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1].rstrip() + "…"


# --- synonyms --------------------------------------------------------------


def load_synonyms(path: Path) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """The synonym pairs as (consumer tokens, ledger tokens), checked for shape.

    A missing file is a broken checkout and fails. A pair whose consumer phrase
    has no search token (all stopwords) could never match, and a consumer phrase
    listed twice would make the expansion depend on file order: both fail too.
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"{path}: the synonym list is missing; it lives at {SYNONYMS_PATH} in the public repo")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: not valid YAML ({exc})") from exc
    if not isinstance(data, dict) or set(data) != {"pairs"} or not isinstance(data["pairs"], list):
        raise ConfigError(f"{path}: expected one key 'pairs' holding a list of {{consumer, ledger}} mappings")
    pairs = []
    seen: dict[tuple[str, ...], str] = {}
    for i, pair in enumerate(data["pairs"]):
        if not isinstance(pair, dict) or set(pair) != set(SYNONYM_KEYS):
            raise ConfigError(f"{path}: pairs[{i}]: expected exactly the keys {list(SYNONYM_KEYS)}, got {pair!r}")
        sides = []
        for key in SYNONYM_KEYS:
            value = pair[key]
            if not isinstance(value, str) or not value.strip() or "$" in value or "\\" in value:
                raise ConfigError(f"{path}: pairs[{i}].{key}: {value!r} is empty or carries LaTeX; a phrase is plain words")
            found = tuple(tokens(value))
            if not found:
                raise ConfigError(f"{path}: pairs[{i}].{key}: {value!r} has no search word once stopwords are dropped")
            sides.append(found)
        if sides[0] in seen:
            raise ConfigError(f"{path}: pairs[{i}].consumer: {pair['consumer']!r} repeats {seen[sides[0]]!r}")
        seen[sides[0]] = pair["consumer"]
        pairs.append((sides[0], sides[1]))
    return pairs


def synonyms_of(family) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """The family's synonym pairs, read from the public repo."""
    public = family.public
    if public is None:
        raise ConfigError("the synonym list lives in the public repo, and this family has none on disk")
    return load_synonyms(public.root / SYNONYMS_PATH)


def expand(query: list[str], pairs) -> list[tuple[int, list[tuple[str, ...]]]]:
    """The query as groups: (how many query tokens the group stands for, its alternatives).

    Every query token is its own group with one alternative. Where a pair's
    consumer phrase occurs in the query as consecutive tokens, those tokens become
    one group whose alternatives are the consumer phrase and the ledger phrase, so
    an entry that says either one scores for it. Longer phrases are matched first
    and a token joins at most one group.
    """
    groups: list[tuple[int, list[tuple[str, ...]]]] = []
    i = 0
    ordered = sorted(pairs, key=lambda pair: -len(pair[0]))
    while i < len(query):
        for consumer, ledger in ordered:
            if tuple(query[i:i + len(consumer)]) == consumer:
                groups.append((len(consumer), [consumer, ledger]))
                i += len(consumer)
                break
        else:
            groups.append((1, [(query[i],)]))
            i += 1
    return groups
