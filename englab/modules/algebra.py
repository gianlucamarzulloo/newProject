"""Geometria e Algebra Lineare: matrici, sistemi, autovalori con i passaggi.

Le matrici si inseriscono una riga per linea, con gli elementi separati da
spazi (es. "1 2 3\\n4 5 6"). Gli elementi possono essere frazioni (1/2),
radici (sqrt(2)) o contenere un parametro (es. k) per le discussioni.
"""

from __future__ import annotations

import re

import sympy as sp

from ..core.parsing import ParseError, latex, nice, parse

MAX_SIZE = 6


def parse_matrix(text: str) -> sp.Matrix:
    rows = [r for r in re.split(r"[\n;]+", text.strip()) if r.strip()]
    if not rows:
        raise ParseError("Inserisci una matrice: una riga per linea, elementi separati da spazi.")
    data = []
    for r in rows:
        cells = r.replace("\t", " ").split()
        data.append([parse(c) for c in cells])
    width = len(data[0])
    if any(len(r) != width for r in data):
        raise ParseError("Tutte le righe devono avere lo stesso numero di elementi.")
    if len(data) > MAX_SIZE or width > MAX_SIZE + 1:
        raise ParseError(f"Dimensione massima {MAX_SIZE}x{MAX_SIZE}.")
    return sp.Matrix(data)


def mat_tex(m: sp.Matrix, bar: int | None = None) -> str:
    """LaTeX di una matrice, con barra verticale opzionale prima della colonna `bar`."""
    cols = "c" * m.cols if bar is None else "c" * bar + "|" + "c" * (m.cols - bar)
    body = r" \\ ".join(" & ".join(latex(nice(v)) for v in m.row(i)) for i in range(m.rows))
    return rf"\left(\begin{{array}}{{{cols}}} {body} \end{{array}}\right)"


def _coef(c: sp.Expr) -> str:
    tex = latex(c)
    return tex if c.is_number else rf"\left({tex}\right)"


def _row(i: int) -> str:
    return f"R_{{{i + 1}}}"


def gauss_steps(m: sp.Matrix, bar: int | None = None, jordan: bool = True) -> tuple[sp.Matrix, list[dict], list[int]]:
    """Riduzione a scala (e a scala ridotta se jordan) registrando ogni operazione.

    Restituisce (matrice finale, passaggi, colonne pivot). Le colonne dopo `bar`
    (termini noti o identità) non vengono scelte come pivot.
    """
    m = m.copy()
    steps: list[dict] = [{"op": "Matrice di partenza", "matrix": mat_tex(m, bar)}]
    limit_col = m.cols if bar is None else bar
    pivots: list[int] = []
    r = 0
    for c in range(limit_col):
        if r >= m.rows:
            break
        pivot_row = next((i for i in range(r, m.rows) if sp.simplify(m[i, c]) != 0), None)
        if pivot_row is None:
            continue
        if pivot_row != r:
            m.row_swap(r, pivot_row)
            steps.append({"op": rf"{_row(r)} \leftrightarrow {_row(pivot_row)}", "matrix": mat_tex(m, bar)})
        pv = m[r, c]
        if jordan and pv != 1:
            m[r, :] = (m[r, :] / pv).applyfunc(sp.simplify)
            steps.append({"op": rf"{_row(r)} \to {_coef(1 / pv)}\,{_row(r)}", "matrix": mat_tex(m, bar)})
            pv = sp.Integer(1)
        targets = range(m.rows) if jordan else range(r + 1, m.rows)
        ops = []
        for i in targets:
            if i == r or sp.simplify(m[i, c]) == 0:
                continue
            factor = sp.simplify(m[i, c] / pv)
            m[i, :] = (m[i, :] - factor * m[r, :]).applyfunc(sp.simplify)
            sign = "-" if not factor.could_extract_minus_sign() else "+"
            coef = latex(abs(factor)) if factor.is_number else rf"\left({latex(-factor if sign == '+' else factor)}\right)"
            ops.append(rf"{_row(i)} \to {_row(i)} {sign} {coef if coef != '1' else ''}{_row(r)}")
        if ops:
            steps.append({"op": r",\quad ".join(ops), "matrix": mat_tex(m, bar)})
        pivots.append(c)
        r += 1
    return m, steps, pivots


def _param_symbols(m: sp.Matrix) -> list[sp.Symbol]:
    return sorted(m.free_symbols, key=str)


def riduzione(text: str) -> dict:
    m = parse_matrix(text)
    if _param_symbols(m):
        raise ParseError("La riduzione passo passo richiede una matrice numerica. "
                         "Per i parametri usa 'Discussione con parametro'.")
    final, steps, pivots = gauss_steps(m, jordan=True)
    return {"input": mat_tex(m), "steps": steps, "result": mat_tex(final),
            "rank": len(pivots), "pivots": [p + 1 for p in pivots]}


def determinante(text: str) -> dict:
    m = parse_matrix(text)
    if m.rows != m.cols:
        raise ParseError("Il determinante è definito solo per matrici quadrate.")
    det = nice(m.det())
    steps = []
    n = m.rows
    if n == 2:
        a, b, c, d = m
        steps.append({"op": "Formula per matrici 2x2",
                      "matrix": rf"ad - bc = ({latex(a)})({latex(d)}) - ({latex(b)})({latex(c)}) = {latex(det)}"})
    elif n == 3:
        plus = [m[0, 0] * m[1, 1] * m[2, 2], m[0, 1] * m[1, 2] * m[2, 0], m[0, 2] * m[1, 0] * m[2, 1]]
        minus = [m[0, 2] * m[1, 1] * m[2, 0], m[0, 0] * m[1, 2] * m[2, 1], m[0, 1] * m[1, 0] * m[2, 2]]
        steps.append({"op": "Regola di Sarrus",
                      "matrix": "(" + " + ".join(f"{{{latex(t)}}}" for t in plus) + ") - ("
                      + " + ".join(f"{{{latex(t)}}}" for t in minus) + rf") = {latex(det)}"})
    elif n > 3:
        terms = []
        for j in range(n):
            if m[0, j] == 0:
                continue
            minor = m.minor_submatrix(0, j)
            sign = "+" if j % 2 == 0 else "-"
            terms.append(rf"{sign} {latex(m[0, j])} \cdot \det{mat_tex(minor)}")
        steps.append({"op": "Sviluppo di Laplace lungo la prima riga",
                      "matrix": " ".join(terms) + rf" = {latex(det)}"})
    return {"input": mat_tex(m), "result": latex(det), "steps": steps,
            "invertible": None if det.free_symbols else det != 0}


def inversa(text: str) -> dict:
    m = parse_matrix(text)
    if m.rows != m.cols:
        raise ParseError("Solo le matrici quadrate possono essere invertibili.")
    if _param_symbols(m):
        raise ParseError("Inserisci una matrice numerica.")
    if m.det() == 0:
        return {"input": mat_tex(m), "invertible": False, "steps": [],
                "result": r"\det A = 0 \Rightarrow A \text{ non è invertibile}"}
    n = m.rows
    final, steps, _ = gauss_steps(m.row_join(sp.eye(n)), bar=n, jordan=True)
    inv = final[:, n:]
    return {"input": mat_tex(m), "invertible": True, "steps": steps, "result": mat_tex(inv)}


def sistema(text: str) -> dict:
    """Sistema lineare dalla matrice completa [A | b] (ultima colonna = termini noti)."""
    aug = parse_matrix(text)
    if aug.cols < 2:
        raise ParseError("Servono almeno una colonna di coefficienti e la colonna dei termini noti.")
    if _param_symbols(aug):
        raise ParseError("Inserisci un sistema numerico (per i parametri usa la discussione).")
    n = aug.cols - 1
    A, b = aug[:, :n], aug[:, n]
    unknowns = sp.symbols(f"x1:{n + 1}", real=True)
    equations = [rf"{latex(sum(A[i, j] * unknowns[j] for j in range(n)))} = {latex(b[i])}" for i in range(A.rows)]

    final, steps, pivots = gauss_steps(aug, bar=n, jordan=True)
    rA, rAb = A.rank(), aug.rank()
    rouche = rf"\operatorname{{rk}}(A) = {rA},\quad \operatorname{{rk}}(A|b) = {rAb},\quad n = {n}"
    if rA != rAb:
        verdict, solution = "Il sistema è impossibile (nessuna soluzione).", None
    else:
        sol = sp.linsolve((A, b), *unknowns)
        tup = next(iter(sol))
        free = n - rA
        if free == 0:
            verdict = "Il sistema ha un'unica soluzione."
        else:
            liberi = "1 incognita libera" if free == 1 else f"{free} incognite libere"
            verdict = f"Il sistema ha infinite soluzioni (∞^{free}): {liberi}."
        solution = [rf"{latex(u)} \in \mathbb{{R}} \text{{ libera}}" if v == u
                    else rf"{latex(u)} = {latex(nice(v))}" for u, v in zip(unknowns, tup)]
    return {"equations": equations, "steps": steps, "rouche": rouche, "verdict": verdict,
            "solution": solution}


def autovalori(text: str) -> dict:
    m = parse_matrix(text)
    if m.rows != m.cols:
        raise ParseError("Autovalori e autovettori esistono solo per matrici quadrate.")
    if _param_symbols(m):
        raise ParseError("Inserisci una matrice numerica.")
    lam = sp.Symbol("lambda")
    charpoly = (m - lam * sp.eye(m.rows)).det()
    factored = sp.factor(charpoly)
    eig = []
    diag = True
    for value, alg, vectors in m.eigenvects():
        geo = len(vectors)
        diag &= alg == geo
        eig.append({
            "value": latex(nice(value)), "alg": alg, "geo": geo,
            "real": bool(value.is_real),
            "basis": [mat_tex(sp.Matrix([nice(c) for c in v])) for v in vectors],
        })
    out = {
        "input": mat_tex(m),
        "charpoly": rf"p(\lambda) = \det(A - \lambda I) = {latex(factored)}",
        "eigen": eig,
        "diagonalizable": diag,
        "symmetric": m == m.T,
    }
    if diag:
        P, D = m.diagonalize()
        out["P"] = mat_tex(P.applyfunc(nice))
        out["D"] = mat_tex(D.applyfunc(nice))
    return out


def discussione(text: str) -> dict:
    """Rango (e determinante) di una matrice al variare di un parametro."""
    m = parse_matrix(text)
    params = _param_symbols(m)
    if len(params) != 1:
        raise ParseError("Inserisci una matrice con esattamente un parametro (es. k).")
    k = params[0]
    cases = []
    if m.rows == m.cols:
        det = sp.factor(m.det())
        critical = sp.solveset(det, k, domain=sp.S.Reals)
        crit_list = sorted(critical, key=float) if isinstance(critical, sp.FiniteSet) else []
        head = rf"\det A = {latex(det)}"
        generic = m.rows
    else:
        # valori critici: quelli che annullano tutti i minori di ordine massimo
        order = min(m.rows, m.cols)
        minors = []
        from itertools import combinations
        for rows in combinations(range(m.rows), order):
            for cols in combinations(range(m.cols), order):
                minors.append(sp.factor(m.extract(list(rows), list(cols)).det()))
        common = sp.solveset(minors[0], k, domain=sp.S.Reals)
        for mi in minors[1:]:
            common = common.intersect(sp.solveset(mi, k, domain=sp.S.Reals))
        crit_list = sorted(common, key=float) if isinstance(common, sp.FiniteSet) else []
        head = rf"\text{{Minori di ordine {order} nulli insieme per }} {latex(k)} \in {latex(sp.FiniteSet(*crit_list))}"
        generic = order
    excluded = ", ".join(rf"{latex(k)} \neq {latex(c)}" for c in crit_list) or r"\forall " + latex(k)
    cases.append({"cond": excluded, "rank": generic})
    for c in crit_list:
        cases.append({"cond": rf"{latex(k)} = {latex(c)}", "rank": m.subs(k, c).rank(),
                      "matrix": mat_tex(m.subs(k, c))})
    return {"input": mat_tex(m), "head": head, "cases": cases, "param": latex(k)}
