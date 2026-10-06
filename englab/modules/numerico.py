"""Calcolo Numerico: zeri di funzione, quadratura, ODE e interpolazione.

I metodi sono scritti in modo volutamente didattico (come si vedono a lezione):
il loro codice sorgente viene mostrato sul sito accanto ai risultati.
"""

from __future__ import annotations

import inspect
import math

import numpy as np
import sympy as sp

from ..core.parsing import ParseError, latex, parse, parse_number
from ..core.sandbox import soft_limit

MAX_ITER = 200


def _func(text: str, *names: str):
    expr = parse(text)
    allowed = {sp.Symbol(n, real=True) for n in names}
    extra = expr.free_symbols - allowed
    if extra:
        raise ParseError(f"Variabili non ammesse: {', '.join(map(str, extra))}. Usa solo {', '.join(names)}.")
    syms = [sp.Symbol(n, real=True) for n in names]
    return expr, sp.lambdify(syms, expr, modules=["numpy"]), syms


def _f(v) -> float | None:
    v = float(v)
    return v if math.isfinite(v) else None


# --------------------------------------------------------------------------- metodi (codice mostrato agli studenti)

def bisezione(f, a, b, tol, max_iter):
    if f(a) * f(b) > 0:
        raise ValueError("f(a) e f(b) devono avere segno opposto")
    iterazioni = []
    for k in range(max_iter):
        c = (a + b) / 2
        if f(a) * f(c) <= 0:
            b = c
        else:
            a = c
        # |c - radice| <= metà del nuovo intervallo
        iterazioni.append((k, c, f(c), (b - a)))
        if b - a < tol:
            break
    return iterazioni


def newton(f, df, x0, tol, max_iter):
    iterazioni = []
    x = x0
    for k in range(max_iter):
        d = df(x)
        if d == 0:
            raise ValueError("derivata nulla: il metodo di Newton si blocca")
        x_new = x - f(x) / d
        iterazioni.append((k, x_new, f(x_new), abs(x_new - x)))
        if abs(x_new - x) < tol:
            break
        x = x_new
    return iterazioni


def secanti(f, x0, x1, tol, max_iter):
    iterazioni = []
    for k in range(max_iter):
        den = f(x1) - f(x0)
        if den == 0:
            raise ValueError("f(x1) = f(x0): retta secante orizzontale")
        x2 = x1 - f(x1) * (x1 - x0) / den
        iterazioni.append((k, x2, f(x2), abs(x2 - x1)))
        if abs(x2 - x1) < tol:
            break
        x0, x1 = x1, x2
    return iterazioni


def punto_fisso(g, x0, tol, max_iter):
    iterazioni = []
    x = x0
    for k in range(max_iter):
        x_new = g(x)
        iterazioni.append((k, x_new, x_new - g(x_new), abs(x_new - x)))
        if abs(x_new - x) < tol or not math.isfinite(x_new):
            break
        x = x_new
    return iterazioni


def punto_medio(f, a, b, n):
    h = (b - a) / n
    return h * sum(f(a + (i + 0.5) * h) for i in range(n))


def trapezi(f, a, b, n):
    h = (b - a) / n
    return h * (f(a) / 2 + sum(f(a + i * h) for i in range(1, n)) + f(b) / 2)


def simpson(f, a, b, n):
    if n % 2:
        n += 1  # Simpson richiede un numero pari di sottointervalli
    h = (b - a) / n
    s = f(a) + f(b)
    s += 4 * sum(f(a + i * h) for i in range(1, n, 2))
    s += 2 * sum(f(a + i * h) for i in range(2, n, 2))
    return h / 3 * s


def eulero(f, t0, y0, h, n):
    t, y = [t0], [y0]
    for _ in range(n):
        y.append(y[-1] + h * f(t[-1], y[-1]))
        t.append(t[-1] + h)
    return t, y


def heun(f, t0, y0, h, n):
    t, y = [t0], [y0]
    for _ in range(n):
        k1 = f(t[-1], y[-1])
        k2 = f(t[-1] + h, y[-1] + h * k1)
        y.append(y[-1] + h / 2 * (k1 + k2))
        t.append(t[-1] + h)
    return t, y


def runge_kutta4(f, t0, y0, h, n):
    t, y = [t0], [y0]
    for _ in range(n):
        tk, yk = t[-1], y[-1]
        k1 = f(tk, yk)
        k2 = f(tk + h / 2, yk + h / 2 * k1)
        k3 = f(tk + h / 2, yk + h / 2 * k2)
        k4 = f(tk + h, yk + h * k3)
        y.append(yk + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4))
        t.append(tk + h)
    return t, y


def lagrange(xs, ys, x):
    totale = 0.0
    for i in range(len(xs)):
        L = 1.0
        for j in range(len(xs)):
            if j != i:
                L *= (x - xs[j]) / (xs[i] - xs[j])
        totale += ys[i] * L
    return totale


def source(fn) -> str:
    return inspect.getsource(fn)


# --------------------------------------------------------------------------- API

def _order(errors: list[float]) -> float | None:
    """Stima dell'ordine di convergenza p da e_{k+1} ~ C e_k^p."""
    e = [v for v in errors if v and v > 1e-15]
    if len(e) < 3:
        return None
    p = math.log(e[-1] / e[-2]) / math.log(e[-2] / e[-3])
    return round(p, 2) if math.isfinite(p) else None


def zeri(f_text: str, metodo: str, a: str = "", b: str = "", x0: str = "", x1: str = "",
         g_text: str = "", tol: str = "1e-8", max_iter: int = 50) -> dict:
    expr, f, (xs,) = _func(f_text, "x")
    tol_v = parse_number(tol) if str(tol).strip() else 1e-8
    if not 0 < tol_v < 1:
        raise ParseError("La tolleranza deve essere tra 0 e 1 (es. 1e-8).")
    max_iter = max(1, min(int(max_iter), MAX_ITER))
    F = lambda v: float(f(v))  # noqa: E731

    try:
        if metodo == "bisezione":
            its = bisezione(F, parse_number(a), parse_number(b), tol_v, max_iter)
            fn = bisezione
        elif metodo == "newton":
            dexpr = sp.diff(expr, xs)
            df = sp.lambdify(xs, dexpr, modules=["numpy"])
            its = newton(F, lambda v: float(df(v)), parse_number(x0), tol_v, max_iter)
            fn = newton
        elif metodo == "secanti":
            its = secanti(F, parse_number(x0), parse_number(x1), tol_v, max_iter)
            fn = secanti
        elif metodo == "punto_fisso":
            gexpr, g, _ = _func(g_text or f"x - ({f_text})", "x")
            its = punto_fisso(lambda v: float(g(v)), parse_number(x0), tol_v, max_iter)
            fn = punto_fisso
        else:
            raise ParseError("Metodo sconosciuto.")
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        if isinstance(exc, ParseError):
            raise
        raise ParseError(f"Il metodo non può proseguire: {exc}.") from exc

    rows = [{"k": k, "x": _f(xk), "fx": _f(fx), "err": _f(err)} for k, xk, fx, err in its]
    last = rows[-1]
    converged = last["err"] is not None and last["err"] < tol_v
    pts = [r["x"] for r in rows if r["x"] is not None]
    center = pts[-1] if pts else 0.0
    span = max(2.0, (max(pts) - min(pts)) * 1.5 if len(pts) > 1 else 2.0)
    if metodo == "bisezione":
        lo, hi = parse_number(a), parse_number(b)
        span = max(span, (hi - lo) * 0.7)
    grid = np.linspace(center - span, center + span, 400)
    with np.errstate(all="ignore"):
        gy = np.asarray(f(grid), dtype=float) * np.ones_like(grid)
    return {
        "function": latex(expr),
        "method": metodo,
        "rows": rows,
        "root": last["x"],
        "converged": converged,
        "iterations": len(rows),
        "order": _order([r["err"] for r in rows]),
        "plot": {"x": grid.tolist(), "y": [_f(v) for v in gy], "iterates": pts},
        "code": source(fn),
    }


def quadratura(f_text: str, a: str, b: str, n: int = 8) -> dict:
    expr, f, (xs,) = _func(f_text, "x")
    lo, hi = parse_number(a), parse_number(b)
    n = max(1, min(int(n), 10_000))
    F = lambda v: float(f(v))  # noqa: E731

    exact_sym = None
    with soft_limit(3):
        try:
            sym = sp.integrate(expr, (xs, sp.nsimplify(a), sp.nsimplify(b)))
            if not sym.has(sp.Integral):
                exact_sym = sym
        except Exception:
            pass
    if exact_sym is not None:
        exact = float(sp.N(exact_sym, 20))
    else:
        from scipy.integrate import quad
        exact = quad(F, lo, hi, limit=200)[0]

    methods = {"punto_medio": punto_medio, "trapezi": trapezi, "simpson": simpson}
    results = {name: fn(F, lo, hi, n) for name, fn in methods.items()}

    ns = [2 ** k for k in range(1, 11)]
    conv = {name: [abs(fn(F, lo, hi, m) - exact) or None for m in ns] for name, fn in methods.items()}
    orders = {}
    for name, errs in conv.items():
        pairs = [(ns[i], errs[i]) for i in range(len(ns)) if errs[i] and errs[i] > 1e-13]
        if len(pairs) >= 2:
            (n1, e1), (n2, e2) = pairs[0], pairs[min(3, len(pairs) - 1)]
            orders[name] = round(math.log(e1 / e2) / math.log(n2 / n1), 2)
    grid = np.linspace(lo, hi, 300)
    with np.errstate(all="ignore"):
        gy = np.asarray(f(grid), dtype=float) * np.ones_like(grid)
    return {
        "function": latex(expr),
        "interval": [lo, hi],
        "n": n,
        "exact": exact,
        "exact_tex": latex(exact_sym) if exact_sym is not None else None,
        "results": {k: {"value": v, "error": abs(v - exact)} for k, v in results.items()},
        "convergence": {"n": ns, "errors": conv, "orders": orders},
        "plot": {"x": grid.tolist(), "y": [_f(v) for v in gy]},
        "code": {k: source(v) for k, v in methods.items()},
    }


def ode(f_text: str, t0: str, y0: str, T: str, h: str) -> dict:
    expr, f, (ts, ys) = _func(f_text, "t", "y")
    t0v, y0v, Tv, hv = (parse_number(v) for v in (t0, y0, T, h))
    if hv <= 0 or Tv <= t0v:
        raise ParseError("Serve h > 0 e T > t0.")
    n = int(round((Tv - t0v) / hv))
    if n > 20_000:
        raise ParseError("Troppi passi: aumenta h o riduci l'intervallo.")
    F = lambda t, y: float(f(t, y))  # noqa: E731

    exact_tex, exact_fn = None, None
    with soft_limit(3):
        try:
            yf = sp.Function("y")
            sol = sp.dsolve(sp.Eq(yf(ts).diff(ts), expr.subs(ys, yf(ts))), yf(ts),
                            ics={yf(sp.nsimplify(t0)): sp.nsimplify(y0)})
            if not isinstance(sol, list) and not sol.rhs.has(sp.Integral):
                exact_tex = latex(sol.rhs)
                exact_fn = sp.lambdify(ts, sol.rhs, modules=["numpy"])
        except Exception:
            pass

    out_methods = {}
    try:
        for name, fn in (("eulero", eulero), ("heun", heun), ("runge_kutta4", runge_kutta4)):
            t, y = fn(F, t0v, y0v, hv, n)
            out_methods[name] = {"t": t, "y": [_f(v) for v in y]}
    except OverflowError as exc:
        raise ParseError("La soluzione numerica diverge: prova un passo h più piccolo.") from exc

    tt = np.array(out_methods["eulero"]["t"])
    if exact_fn is not None:
        with np.errstate(all="ignore"):
            ref = np.asarray(exact_fn(tt), dtype=float) * np.ones_like(tt)
        ref_label = "soluzione esatta"
    else:
        from scipy.integrate import solve_ivp
        sol = solve_ivp(lambda t, y: [F(t, y[0])], (t0v, tt[-1]), [y0v], t_eval=tt, rtol=1e-10, atol=1e-12)
        ref = sol.y[0]
        ref_label = "riferimento ad alta precisione"
    errors = {}
    for name, data in out_methods.items():
        y = np.array([np.nan if v is None else v for v in data["y"]])
        errors[name] = _f(np.nanmax(np.abs(y - ref))) if np.isfinite(ref).all() else None
    return {
        "equation": rf"y'(t) = {latex(expr)},\quad y({latex(sp.nsimplify(t0))}) = {latex(sp.nsimplify(y0))}",
        "exact": exact_tex,
        "reference": {"t": tt.tolist(), "y": [_f(v) for v in ref], "label": ref_label},
        "methods": out_methods,
        "errors": errors,
        "steps": n,
        "code": {"eulero": source(eulero), "heun": source(heun), "runge_kutta4": source(runge_kutta4)},
    }


def interpolazione(f_text: str, a: str, b: str, n: int = 10) -> dict:
    """Confronta nodi equispaziati e nodi di Chebyshev (fenomeno di Runge)."""
    expr, f, (xs,) = _func(f_text, "x")
    lo, hi = parse_number(a), parse_number(b)
    if hi <= lo:
        raise ParseError("Serve a < b.")
    n = max(1, min(int(n), 40))
    F = lambda v: float(f(v))  # noqa: E731
    equi = np.linspace(lo, hi, n + 1)
    k = np.arange(n + 1)
    cheb = (lo + hi) / 2 + (hi - lo) / 2 * np.cos((2 * k + 1) * np.pi / (2 * (n + 1)))
    grid = np.linspace(lo, hi, 500)
    true = np.array([F(v) for v in grid])
    out = {"function": latex(expr), "grid": grid.tolist(), "true": [_f(v) for v in true], "degree": n}
    for name, nodes in (("equispaziati", equi), ("chebyshev", cheb)):
        vals = [F(v) for v in nodes]
        p = np.array([lagrange(nodes, vals, v) for v in grid])
        out[name] = {"nodes": nodes.tolist(), "values": vals, "poly": [_f(v) for v in p],
                     "max_error": _f(np.max(np.abs(p - true)))}
    out["code"] = source(lagrange)
    return out
