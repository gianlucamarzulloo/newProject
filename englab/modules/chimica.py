"""Elementi di Chimica: masse molari, bilanciamento e stechiometria."""

from __future__ import annotations

import re
from collections import Counter
from functools import reduce
from math import gcd

import sympy as sp

from ..core.parsing import ParseError

# Masse atomiche standard (IUPAC, arrotondate a 3 decimali dove significativo).
MASSE: dict[str, float] = {
    "H": 1.008, "He": 4.003, "Li": 6.94, "Be": 9.012, "B": 10.81, "C": 12.011, "N": 14.007,
    "O": 15.999, "F": 18.998, "Ne": 20.180, "Na": 22.990, "Mg": 24.305, "Al": 26.982,
    "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098,
    "Ca": 40.078, "Sc": 44.956, "Ti": 47.867, "V": 50.942, "Cr": 51.996, "Mn": 54.938,
    "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723,
    "Ge": 72.630, "As": 74.922, "Se": 78.971, "Br": 79.904, "Kr": 83.798, "Rb": 85.468,
    "Sr": 87.62, "Y": 88.906, "Zr": 91.224, "Nb": 92.906, "Mo": 95.95, "Tc": 98.0,
    "Ru": 101.07, "Rh": 102.906, "Pd": 106.42, "Ag": 107.868, "Cd": 112.414, "In": 114.818,
    "Sn": 118.710, "Sb": 121.760, "Te": 127.60, "I": 126.904, "Xe": 131.293, "Cs": 132.905,
    "Ba": 137.327, "La": 138.905, "Ce": 140.116, "Pr": 140.908, "Nd": 144.242, "Pm": 145.0,
    "Sm": 150.36, "Eu": 151.964, "Gd": 157.25, "Tb": 158.925, "Dy": 162.500, "Ho": 164.930,
    "Er": 167.259, "Tm": 168.934, "Yb": 173.045, "Lu": 174.967, "Hf": 178.49, "Ta": 180.948,
    "W": 183.84, "Re": 186.207, "Os": 190.23, "Ir": 192.217, "Pt": 195.084, "Au": 196.967,
    "Hg": 200.592, "Tl": 204.38, "Pb": 207.2, "Bi": 208.980, "Po": 209.0, "At": 210.0,
    "Rn": 222.0, "Fr": 223.0, "Ra": 226.0, "Ac": 227.0, "Th": 232.038, "Pa": 231.036,
    "U": 238.029, "Np": 237.0, "Pu": 244.0, "Am": 243.0,
}

_TOKEN = re.compile(r"([A-Z][a-z]?)|(\d+)|([(\[])|([)\]])")


def composizione(formula: str) -> Counter:
    """Conta gli atomi di una formula: H2O, Ca(OH)2, CuSO4*5H2O, [Fe(CN)6]."""
    formula = formula.strip().replace(" ", "")
    if not formula or len(formula) > 80:
        raise ParseError("Formula vuota o troppo lunga.")
    total: Counter = Counter()
    for part in re.split(r"[*·.]", formula):
        m = re.match(r"^(\d+)(.*)$", part)
        mult, body = (int(m.group(1)), m.group(2)) if m else (1, part)
        for el, n in _parse_group(body).items():
            total[el] += n * mult
    return total


def _parse_group(s: str) -> Counter:
    stack: list[Counter] = [Counter()]
    pos = 0
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ParseError(f"Carattere non valido nella formula: '{s[pos]}'.")
        el, num, op, cl = m.groups()
        pos = m.end()
        if el:
            if el not in MASSE:
                raise ParseError(f"Elemento sconosciuto: {el}.")
            n, pos = _number(s, pos)
            stack[-1][el] += n
        elif op:
            stack.append(Counter())
        elif cl:
            if len(stack) == 1:
                raise ParseError("Parentesi chiusa senza apertura.")
            group = stack.pop()
            n, pos = _number(s, pos)
            for k, v in group.items():
                stack[-1][k] += v * n
        elif num:
            raise ParseError("Numero in posizione inattesa nella formula.")
    if len(stack) != 1:
        raise ParseError("Parentesi non bilanciate.")
    return stack[0]


def _number(s: str, pos: int) -> tuple[int, int]:
    m = re.match(r"\d+", s[pos:])
    return (int(m.group()), pos + m.end()) if m else (1, pos)


def massa_molare(formula: str) -> dict:
    comp = composizione(formula)
    rows = [{"el": el, "n": n, "mass": MASSE[el], "subtotal": round(n * MASSE[el], 4)}
            for el, n in comp.items()]
    M = sum(r["subtotal"] for r in rows)
    for r in rows:
        r["percent"] = round(100 * r["subtotal"] / M, 2)
    return {"formula": formula, "rows": rows, "molar_mass": round(M, 3)}


def _split_side(side: str) -> list[str]:
    species = [s.strip() for s in side.split("+") if s.strip()]
    # rimuove eventuali coefficienti già scritti dall'utente (es. "2H2")
    return [re.sub(r"^\d+\s*", "", s) for s in species]


def bilancia(reazione: str) -> dict:
    text = reazione.replace("→", "->").replace("=", "->").replace("⇌", "->").replace("<->", "->")
    if text.count("->") != 1:
        raise ParseError("Scrivi la reazione come 'reagenti -> prodotti', es. H2 + O2 -> H2O.")
    left, right = text.split("->")
    reag, prod = _split_side(left), _split_side(right)
    if not reag or not prod:
        raise ParseError("Servono almeno un reagente e un prodotto.")
    species = reag + prod
    comps = [composizione(s) for s in species]
    elements = sorted({e for c in comps for e in c})
    M = sp.Matrix([[c[e] * (1 if i < len(reag) else -1) for i, c in enumerate(comps)] for e in elements])
    null = M.nullspace()
    if len(null) != 1:
        raise ParseError("La reazione non ha un bilanciamento unico (controlla le formule).")
    v = null[0]
    lcm = reduce(sp.ilcm, [term.q for term in v], 1)
    coeffs = [int(term * lcm) for term in v]
    if all(c < 0 for c in coeffs):
        coeffs = [-c for c in coeffs]
    if any(c <= 0 for c in coeffs):
        raise ParseError("Non esiste un bilanciamento con coefficienti positivi.")
    g = reduce(gcd, coeffs)
    coeffs = [c // g for c in coeffs]

    def side(names, cs):
        return " + ".join(f"{c if c != 1 else ''}{n}" for n, c in zip(names, cs))

    check = [{"el": e, "left": sum(coeffs[i] * comps[i][e] for i in range(len(reag))),
              "right": sum(coeffs[i] * comps[i][e] for i in range(len(reag), len(species)))}
             for e in elements]
    return {
        "balanced": f"{side(reag, coeffs[:len(reag)])} → {side(prod, coeffs[len(reag):])}",
        "species": [{"formula": s, "coeff": c, "role": "reagente" if i < len(reag) else "prodotto",
                     "molar_mass": massa_molare(s)["molar_mass"]}
                    for i, (s, c) in enumerate(zip(species, coeffs))],
        "check": check,
    }


def stechiometria(reazione: str, masse: dict[str, float]) -> dict:
    """Dati i grammi di uno o più reagenti, trova il limitante e le masse prodotte."""
    bal = bilancia(reazione)
    species = bal["species"]
    given = {k: float(v) for k, v in masse.items() if v not in (None, "")}
    if not given:
        raise ParseError("Inserisci la massa (in grammi) di almeno un reagente.")
    ratios = []
    for s in species:
        if s["formula"] in given:
            if s["role"] != "reagente":
                raise ParseError("Le masse vanno date per i reagenti.")
            if given[s["formula"]] <= 0:
                raise ParseError("Le masse devono essere positive.")
            mol = given[s["formula"]] / s["molar_mass"]
            ratios.append((mol / s["coeff"], s["formula"], mol))
    if not ratios:
        raise ParseError("Nessuna delle masse inserite corrisponde a un reagente.")
    extent, limiting, _ = min(ratios)
    table = []
    for s in species:
        mol = extent * s["coeff"]
        row = {"formula": s["formula"], "role": s["role"], "molar_mass": s["molar_mass"],
               "mol_reacting": round(mol, 6), "mass_reacting": round(mol * s["molar_mass"], 4)}
        if s["formula"] in given:
            row["given"] = given[s["formula"]]
            row["excess"] = round(given[s["formula"]] - row["mass_reacting"], 4)
        table.append(row)
    return {"balanced": bal["balanced"], "limiting": limiting if len(ratios) > 1 else None,
            "extent": round(extent, 6), "table": table}
