"""Parsing sicuro di espressioni matematiche scritte come le scrive uno studente.

L'input arriva da utenti anonimi del sito, quindi NON viene mai passato a
`eval` senza controlli: si accettano solo caratteri e nomi di una whitelist,
e la valutazione avviene senza builtins.
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

MAX_LEN = 300


class ParseError(ValueError):
    """Errore di input mostrato all'utente (messaggio in italiano)."""


# Nomi accettati -> oggetto SymPy. Includono la notazione italiana (sen, tg, ...).
FUNCTIONS: dict[str, object] = {
    "sin": sp.sin, "sen": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan, "tg": sp.tan,
    "cot": sp.cot, "cotg": sp.cot, "ctg": sp.cot,
    "asin": sp.asin, "arcsin": sp.asin, "arcsen": sp.asin,
    "acos": sp.acos, "arccos": sp.acos,
    "atan": sp.atan, "arctan": sp.atan, "arctg": sp.atan,
    "sinh": sp.sinh, "senh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp,
    "ln": sp.log, "log": sp.log,  # in Analisi 1 "log" è il logaritmo naturale
    "sqrt": sp.sqrt, "radq": sp.sqrt,
    "abs": sp.Abs,
}
CONSTANTS: dict[str, object] = {
    "pi": sp.pi, "e": sp.E,
    "inf": sp.oo, "oo": sp.oo, "infinito": sp.oo,
}
VARIABLES = {name: sp.Symbol(name, real=True) for name in "abcdfghkmnpqrstuvwxyz"}

ALLOWED_CHARS = re.compile(r"^[0-9A-Za-z+\-*/^().,\s]*$")
IDENT = re.compile(r"[A-Za-z]+")

_LOCALS: dict[str, object] = {**FUNCTIONS, **CONSTANTS, **VARIABLES}
_GLOBALS: dict[str, object] = {
    "__builtins__": {},
    "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational,
    "Symbol": sp.Symbol, "Function": sp.Function,
}
_TRANSFORMS = standard_transformations + (convert_xor, implicit_multiplication_application)

x = VARIABLES["x"]


def _normalize(text: str) -> str:
    text = text.strip()
    if not text:
        raise ParseError("Inserisci un'espressione.")
    if len(text) > MAX_LEN:
        raise ParseError(f"Espressione troppo lunga (massimo {MAX_LEN} caratteri).")
    text = (
        text.replace("π", "pi").replace("∞", "oo").replace("·", "*")
        .replace("×", "*").replace("−", "-").replace("²", "^2").replace("³", "^3")
    )
    # |x| -> abs(x) solo per il caso semplice senza annidamenti
    text = re.sub(r"\|([^|]+)\|", r"abs(\1)", text)
    if not ALLOWED_CHARS.match(text):
        raise ParseError("Sono ammessi solo numeri, lettere, + - * / ^ ( ) e la virgola decimale.")
    for name in IDENT.findall(text):
        if name not in _LOCALS:
            raise ParseError(
                f"Non riconosco '{name}'. Usa variabili di una lettera e scrivi i prodotti "
                f"in modo esplicito (es. x*y invece di xy)."
            )
    # virgola decimale italiana: 2,5 -> 2.5 (solo tra cifre)
    return re.sub(r"(?<=\d),(?=\d)", ".", text)


def parse(text: str) -> sp.Expr:
    """Converte una stringa in espressione SymPy, rifiutando tutto il resto."""
    clean = _normalize(text)
    try:
        expr = parse_expr(
            clean, local_dict=dict(_LOCALS), global_dict=dict(_GLOBALS),
            transformations=_TRANSFORMS, evaluate=True,
        )
    except Exception as exc:  # errori di sintassi di ogni tipo
        raise ParseError("Espressione non valida: controlla parentesi e operatori.") from exc
    if not isinstance(expr, sp.Expr):
        raise ParseError("L'input non è un'espressione matematica.")
    return expr


def parse_point(text: str) -> sp.Expr:
    """Punto a cui tendere in un limite: numero, costante o +/- infinito."""
    expr = parse(text)
    if expr.free_symbols:
        raise ParseError("Il punto del limite deve essere un numero (o infinito).")
    return expr


def parse_number(text: str | float | int) -> float:
    if isinstance(text, (int, float)):
        return float(text)
    expr = parse(str(text))
    if expr.free_symbols:
        raise ParseError(f"'{text}' deve essere un numero.")
    value = complex(sp.N(expr))
    if abs(value.imag) > 1e-12:
        raise ParseError(f"'{text}' non è un numero reale.")
    return value.real


def latex(expr: object) -> str:
    return sp.latex(expr, ln_notation=True, inv_trig_style="full")


def nice(expr: sp.Expr) -> sp.Expr:
    """Forma più leggibile tra semplificata e fattorizzata (meno operazioni vince)."""
    candidates = [sp.simplify(expr)]
    try:
        candidates.append(sp.factor(sp.cancel(expr)))
    except Exception:
        pass
    return min(candidates, key=sp.count_ops)
