"""Analisi 1: derivate, integrali, limiti e studio di funzione con i passaggi.

Ogni funzione pubblica riceve stringhe (input utente) e restituisce dizionari
serializzabili in JSON, con le formule già in LaTeX.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import sympy as sp
from sympy.integrals import manualintegrate as mi

from ..core.parsing import ParseError, latex, nice, parse, parse_point, x
from ..core.sandbox import soft_limit


def _var(name: str) -> sp.Symbol:
    v = parse(name or "x")
    if not isinstance(v, sp.Symbol):
        raise ParseError("La variabile deve essere una sola lettera, es. x.")
    return v


def _step(rule: str, expr_tex: str, result_tex: str, substeps=None, note: str = "") -> dict:
    return {"rule": rule, "expr": expr_tex, "result": result_tex, "note": note,
            "substeps": substeps or []}


# --------------------------------------------------------------------------- derivate

# derivata della funzione esterna f'(u), come lambda su u
_KNOWN_DERIVATIVES = {
    sp.sin: (lambda u: sp.cos(u), r"(\sin u)' = \cos u"),
    sp.cos: (lambda u: -sp.sin(u), r"(\cos u)' = -\sin u"),
    sp.tan: (lambda u: 1 + sp.tan(u) ** 2, r"(\tan u)' = 1 + \tan^2 u = \frac{1}{\cos^2 u}"),
    sp.cot: (lambda u: -1 - sp.cot(u) ** 2, r"(\cot u)' = -\frac{1}{\sin^2 u}"),
    sp.exp: (lambda u: sp.exp(u), r"(e^u)' = e^u"),
    sp.log: (lambda u: 1 / u, r"(\ln u)' = \frac{1}{u}"),
    sp.asin: (lambda u: 1 / sp.sqrt(1 - u ** 2), r"(\arcsin u)' = \frac{1}{\sqrt{1-u^2}}"),
    sp.acos: (lambda u: -1 / sp.sqrt(1 - u ** 2), r"(\arccos u)' = -\frac{1}{\sqrt{1-u^2}}"),
    sp.atan: (lambda u: 1 / (1 + u ** 2), r"(\arctan u)' = \frac{1}{1+u^2}"),
    sp.sinh: (lambda u: sp.cosh(u), r"(\sinh u)' = \cosh u"),
    sp.cosh: (lambda u: sp.sinh(u), r"(\cosh u)' = \sinh u"),
    sp.tanh: (lambda u: 1 - sp.tanh(u) ** 2, r"(\tanh u)' = 1 - \tanh^2 u"),
    sp.Abs: (lambda u: sp.sign(u), r"(|u|)' = \operatorname{sgn}(u),\ u \neq 0"),
}


def _d(expr: sp.Expr, var: sp.Symbol) -> tuple[sp.Expr, dict]:
    """Deriva expr restituendo (derivata, albero dei passaggi)."""
    tex = rf"\frac{{d}}{{d{latex(var)}}}\left[{latex(expr)}\right]"

    if not expr.has(var):
        return sp.Integer(0), _step("Derivata di una costante", tex, "0")
    if expr == var:
        return sp.Integer(1), _step("Derivata della variabile", tex, "1")

    if isinstance(expr, sp.Add):
        parts = [_d(t, var) for t in expr.args]
        res = sp.Add(*[p[0] for p in parts])
        return res, _step("Linearità: derivata della somma", tex, latex(res),
                          [p[1] for p in parts], r"(f+g)' = f' + g'")

    if isinstance(expr, sp.Mul):
        const, rest = expr.as_independent(var, as_Add=False)
        if const != 1:
            dr, s = _d(rest, var)
            res = const * dr
            return res, _step("Costante moltiplicativa", tex, latex(res), [s], r"(c\,f)' = c\,f'")
        num, den = sp.fraction(expr)
        if den.has(var) and num != expr:
            dn, sn = _d(num, var)
            dd, sd = _d(den, var)
            res = (dn * den - num * dd) / den ** 2
            return res, _step("Regola del quoziente", tex, latex(res), [sn, sd],
                              r"\left(\frac{f}{g}\right)' = \frac{f'g - fg'}{g^2}")
        f, g = expr.args[0], sp.Mul(*expr.args[1:])
        df, sf = _d(f, var)
        dg, sg = _d(g, var)
        res = df * g + f * dg
        return res, _step("Regola del prodotto", tex, latex(res), [sf, sg], r"(fg)' = f'g + fg'")

    if isinstance(expr, sp.Pow):
        base, ex = expr.args
        if not ex.has(var):
            outer = ex * base ** (ex - 1)
            if base == var:
                return outer, _step("Derivata della potenza", tex, latex(outer),
                                    note=r"(x^n)' = n\,x^{n-1}")
            db, sb = _d(base, var)
            res = outer * db
            return res, _step("Potenza di funzione (regola della catena)", tex, latex(res), [sb],
                              r"(u^n)' = n\,u^{n-1}\,u'")
        if not base.has(var):
            de, se = _d(ex, var)
            res = expr * sp.log(base) * de
            return res, _step("Esponenziale di base costante", tex, latex(res), [se],
                              r"(a^u)' = a^u \ln a \; u'")
        rewritten = sp.exp(ex * sp.log(base))
        dres, s = _d(rewritten, var)
        res = expr * sp.simplify(dres / rewritten)
        return res, _step("Base ed esponente variabili", tex, latex(res), [s],
                          r"f^g = e^{g \ln f}")

    if isinstance(expr, sp.Function) and len(expr.args) == 1 and expr.func in _KNOWN_DERIVATIVES:
        fn, rule_tex = _KNOWN_DERIVATIVES[expr.func]
        u = expr.args[0]
        outer = fn(u)
        if u == var:
            return outer, _step("Derivata elementare", tex, latex(outer), note=rule_tex)
        du, su = _d(u, var)
        res = outer * du
        return res, _step("Regola della catena", tex, latex(res), [su],
                          rule_tex + r"\quad\Rightarrow\quad (f(u))' = f'(u)\,u'")

    res = sp.diff(expr, var)
    return res, _step("Calcolo diretto", tex, latex(res))


def derivata(expr_text: str, var_text: str = "x", ordine: int = 1) -> dict:
    var = _var(var_text)
    expr = parse(expr_text)
    ordine = int(ordine)
    if not 1 <= ordine <= 5:
        raise ParseError("L'ordine della derivata deve essere tra 1 e 5.")
    current, trees = expr, []
    for _ in range(ordine):
        raw, tree = _d(current, var)
        current = nice(raw)
        trees.append(tree)
    return {
        "input": latex(expr),
        "result": latex(current),
        "result_plain": str(current),
        "steps": trees,
        "order": ordine,
        "var": latex(var),
    }


# --------------------------------------------------------------------------- integrali

_RULE_NAMES = {
    "ConstantRule": "Integrale di una costante",
    "ConstantTimesRule": "Porto fuori la costante",
    "PowerRule": "Integrale della potenza",
    "AddRule": "Linearità: integrale della somma",
    "URule": "Sostituzione",
    "PartsRule": "Integrazione per parti",
    "CyclicPartsRule": "Per parti ciclico (l'integrale ricompare)",
    "ExpRule": "Integrale dell'esponenziale",
    "ReciprocalRule": "Integrale di 1/u: logaritmo",
    "ArctanRule": "Riconduzione all'arcotangente",
    "ArcsinRule": "Riconduzione all'arcoseno",
    "ArcsinhRule": "Riconduzione al settore seno iperbolico",
    "SinRule": "Integrale del seno",
    "CosRule": "Integrale del coseno",
    "Sec2Rule": "Integrale di 1/cos^2",
    "Csc2Rule": "Integrale di 1/sin^2",
    "SecTanRule": "Integrale noto (sec tan)",
    "CscCotRule": "Integrale noto (csc cot)",
    "SinhRule": "Integrale del seno iperbolico",
    "CoshRule": "Integrale del coseno iperbolico",
    "RewriteRule": "Riscrivo l'integranda",
    "CompleteSquareRule": "Completamento del quadrato",
    "TrigSubstitutionRule": "Sostituzione trigonometrica",
    "AlternativeRule": "Metodo scelto",
    "PiecewiseRule": "Integrale definito a tratti",
    "NestedPowRule": "Potenza annidata",
    "SqrtQuadraticRule": "Radice di un polinomio di secondo grado",
    "ReciprocalSqrtQuadraticRule": "1 / radice di un polinomio di secondo grado",
    "DontKnowRule": "Integrale non elementare",
}

_RULE_NOTES = {
    "PowerRule": r"\int u^n\,du = \frac{u^{n+1}}{n+1} + c,\quad n \neq -1",
    "PartsRule": r"\int f\,g'\,dx = f\,g - \int f'\,g\,dx",
    "ReciprocalRule": r"\int \frac{1}{u}\,du = \ln|u| + c",
    "ExpRule": r"\int e^u\,du = e^u + c",
    "SinRule": r"\int \sin u\,du = -\cos u + c",
    "CosRule": r"\int \cos u\,du = \sin u + c",
    "ArctanRule": r"\int \frac{1}{1+u^2}\,du = \arctan u + c",
    "URule": r"\int f(g(x))\,g'(x)\,dx = \int f(u)\,du",
}


def _integral_tree(rule) -> dict:
    name = type(rule).__name__
    integrand, var = rule.integrand, rule.variable
    expr_tex = rf"\int {latex(integrand)}\,d{latex(var)}"
    try:
        result_tex = latex(sp.simplify(rule.eval()))
    except Exception:
        result_tex = r"\text{(non esprimibile in forma elementare)}"
    note = _RULE_NOTES.get(name, "")
    if name == "URule":
        note = rf"\text{{pongo }} {latex(rule.u_var)} = {latex(rule.u_func)}"
    elif name == "PartsRule":
        note = rf"f = {latex(rule.u)},\quad g' = {latex(rule.dv)}"
    elif name in ("RewriteRule", "CompleteSquareRule"):
        note = rf"{latex(integrand)} = {latex(rule.rewritten)}"

    children = []
    if name == "AlternativeRule":
        children = [_integral_tree(rule.alternatives[0])]
    else:
        for field in dataclasses.fields(rule):
            value = getattr(rule, field.name)
            if isinstance(value, mi.Rule):
                children.append(_integral_tree(value))
            elif isinstance(value, (list, tuple)):
                children.extend(_integral_tree(v) for v in value if isinstance(v, mi.Rule))
    return _step(_RULE_NAMES.get(name, name), expr_tex, result_tex, children, note)


def integrale(expr_text: str, var_text: str = "x", a: str = "", b: str = "") -> dict:
    var = _var(var_text)
    expr = parse(expr_text)
    steps = []
    with soft_limit(4):
        try:
            steps = [_integral_tree(mi.integral_steps(expr, var))]
        except Exception:
            steps = []
    primitive = sp.integrate(expr, var)
    if primitive.has(sp.Integral):
        raise ParseError("Non esiste una primitiva in forma elementare per questa funzione.")
    primitive = sp.simplify(primitive)
    out = {
        "input": rf"\int {latex(expr)}\,d{latex(var)}",
        "result": latex(primitive) + " + c",
        "result_plain": str(primitive),
        "steps": steps,
    }
    if a.strip() and b.strip():
        lo, hi = parse_point(a), parse_point(b)
        value = sp.simplify(sp.integrate(expr, (var, lo, hi)))
        out["definite"] = {
            "input": rf"\int_{{{latex(lo)}}}^{{{latex(hi)}}} {latex(expr)}\,d{latex(var)}",
            "result": latex(value),
            "numeric": _num(value),
            "fundamental": rf"\Big[{latex(primitive)}\Big]_{{{latex(lo)}}}^{{{latex(hi)}}}",
        }
    return out


# --------------------------------------------------------------------------- limiti

def _num(value) -> str | None:
    try:
        v = complex(sp.N(value))
    except (TypeError, ValueError):
        return None
    if abs(v.imag) > 1e-12 or not math.isfinite(v.real):
        return None
    return f"{v.real:.10g}"


def _classify(value: sp.Expr) -> str:
    if value in (sp.oo, -sp.oo, sp.zoo):
        return "inf"
    if value == 0:
        return "0"
    if value is sp.nan or value.has(sp.nan):
        return "nan"
    return "finite"


def limite(expr_text: str, punto_text: str, var_text: str = "x", direzione: str = "+-") -> dict:
    var = _var(var_text)
    expr = parse(expr_text)
    point = parse_point(punto_text)
    if direzione not in ("+", "-", "+-"):
        raise ParseError("Direzione non valida.")
    if point in (sp.oo, -sp.oo):
        direzione = "-" if point == sp.oo else "+"

    steps = []
    sub_tex = rf"{latex(var)} \to {latex(point)}"

    # 1) sostituzione diretta (solo per punti finiti)
    form = None
    num, den = sp.fraction(sp.together(expr))
    if point.is_finite:
        try:
            direct = expr.subs(var, point)
            if direct.is_finite and not direct.has(sp.nan, sp.zoo):
                steps.append(_step("Sostituzione diretta", sub_tex, latex(direct),
                                   note="La funzione è continua nel punto: basta sostituire."))
        except Exception:
            pass
    if not steps and den.has(var):
        ln = sp.limit(num, var, point, dir=direzione if direzione != "+-" else "+")
        ld = sp.limit(den, var, point, dir=direzione if direzione != "+-" else "+")
        cn, cd = _classify(ln), _classify(ld)
        if (cn, cd) == ("0", "0"):
            form = r"\frac{0}{0}"
        elif (cn, cd) == ("inf", "inf"):
            form = r"\frac{\infty}{\infty}"
        if form:
            steps.append(_step("Forma indeterminata", sub_tex, form,
                               note=rf"\lim N = {latex(ln)},\quad \lim D = {latex(ld)}"))
            dn, dd = sp.diff(num, var), sp.diff(den, var)
            steps.append(_step(
                "Teorema di de l'Hôpital", rf"\lim \frac{{{latex(num)}}}{{{latex(den)}}}",
                rf"\lim \frac{{{latex(sp.simplify(dn))}}}{{{latex(sp.simplify(dd))}}}",
                note=r"\lim \frac{f}{g} = \lim \frac{f'}{g'} \text{ se il secondo limite esiste}",
            ))

    if direzione == "+-":
        right = sp.limit(expr, var, point, dir="+")
        left = sp.limit(expr, var, point, dir="-")
        if right == left:
            result = right
        else:
            result = None
            steps.append(_step("Limiti destro e sinistro diversi", sub_tex,
                               rf"\lim_{{{latex(var)}\to {latex(point)}^-}} = {latex(left)},\quad "
                               rf"\lim_{{{latex(var)}\to {latex(point)}^+}} = {latex(right)}",
                               note="Il limite non esiste."))
    else:
        result = sp.limit(expr, var, point, dir=direzione)

    arrow = latex(point) + ("" if direzione == "+-" or not point.is_finite else f"^{direzione}")
    return {
        "input": rf"\lim_{{{latex(var)} \to {arrow}}} {latex(expr)}",
        "result": latex(result) if result is not None else r"\nexists",
        "exists": result is not None,
        "numeric": _num(result) if result is not None else None,
        "form": form,
        "steps": steps,
    }


# --------------------------------------------------------------------------- studio di funzione

def _real_roots(expr: sp.Expr, var: sp.Symbol, domain) -> list[sp.Expr]:
    try:
        sol = sp.solveset(expr, var, domain=domain)
    except Exception:
        return []
    if isinstance(sol, sp.FiniteSet):
        return sorted((s for s in sol if s.is_real), key=lambda s: float(s))
    return []


def _fmt_set(s) -> str:
    return latex(s).replace(r"\mathbb{R}", r"\mathbb{R}")


def _sign_intervals(expr: sp.Expr, var: sp.Symbol, domain) -> list[dict]:
    """Intervalli del dominio in cui expr è positiva o negativa."""
    out = []
    try:
        pos = sp.solveset(expr > 0, var, domain=domain)
        neg = sp.solveset(expr < 0, var, domain=domain)
    except Exception:
        return out
    if pos is not sp.EmptySet:
        out.append({"sign": "+", "set": _fmt_set(pos)})
    if neg is not sp.EmptySet:
        out.append({"sign": "-", "set": _fmt_set(neg)})
    return out


def _sample(expr: sp.Expr, var: sp.Symbol, lo: float, hi: float, n: int = 1200) -> dict:
    f = sp.lambdify(var, expr, modules=["numpy"])
    xs = np.linspace(lo, hi, n)
    with np.errstate(all="ignore"):
        ys = np.asarray(f(xs), dtype=complex) * np.ones_like(xs)
    real = np.where(np.abs(ys.imag) < 1e-9, ys.real, np.nan)
    real[~np.isfinite(real)] = np.nan
    finite = real[np.isfinite(real)]
    yrange = None
    if finite.size:
        # finestra verticale robusta: ignora i valori enormi vicino agli asintoti
        p_lo, p_hi = np.percentile(finite, [8, 92])
        span = max(p_hi - p_lo, 1.0)
        yrange = [float(p_lo - 0.6 * span), float(p_hi + 0.6 * span)]
        # spezza la linea dove la funzione salta da +inf a -inf
        jumps = np.abs(np.diff(real)) > 4 * span
        real[1:][jumps] = np.nan
    return {"x": xs.round(6).tolist(),
            "y": [None if not np.isfinite(v) else round(float(v), 6) for v in real],
            "yrange": yrange}


def studio_funzione(expr_text: str) -> dict:
    var = x
    expr = parse(expr_text)
    if expr.free_symbols - {var}:
        raise ParseError("Lo studio di funzione accetta solo la variabile x.")
    reals = sp.S.Reals
    domain = sp.calculus.util.continuous_domain(expr, var, reals)
    sections = []

    sections.append({"title": "Dominio", "items": [rf"D = {_fmt_set(domain)}"]})

    # simmetrie
    neg = sp.simplify(expr.subs(var, -var))
    if sp.simplify(neg - expr) == 0:
        parity = "La funzione è pari: simmetrica rispetto all'asse y."
    elif sp.simplify(neg + expr) == 0:
        parity = "La funzione è dispari: simmetrica rispetto all'origine."
    else:
        parity = "La funzione non è né pari né dispari."
    sections.append({"title": "Simmetrie", "text": parity, "items": [rf"f(-x) = {latex(neg)}"]})

    # intersezioni con gli assi
    inter = []
    if domain.contains(0) == sp.true:
        inter.append(rf"\text{{asse }} y:\ (0,\ {latex(sp.simplify(expr.subs(var, 0)))})")
    zeros = _real_roots(expr, var, domain)
    for z in zeros:
        inter.append(rf"\text{{asse }} x:\ ({latex(z)},\ 0)")
    sections.append({"title": "Intersezioni con gli assi",
                     "items": inter or [r"\text{nessuna intersezione trovata}"]})

    sections.append({"title": "Segno", "signs": _sign_intervals(expr, var, domain)})

    # asintoti
    asym = []
    vertical: set[float] = set()
    try:
        boundary = sorted({p for p in domain.boundary if p.is_finite and p.is_real},
                          key=lambda p: float(p))
    except TypeError:  # frontiera infinita (es. funzioni periodiche come tan x)
        boundary = []
    for p in boundary:
        for d in ("-", "+"):
            try:
                L = sp.limit(expr, var, p, dir=d)
            except Exception:
                continue
            if L in (sp.oo, -sp.oo):
                vertical.add(float(p))
                asym.append(rf"x = {latex(p)} \text{{ verticale }}"
                            rf"\left(\lim_{{x\to {latex(p)}^{d}}} f = {latex(L)}\right)")
    for inf in (sp.oo, -sp.oo):
        if (domain.sup if inf == sp.oo else domain.inf) == inf:
            try:
                L = sp.limit(expr, var, inf)
            except Exception:
                continue
            side = r"+\infty" if inf == sp.oo else r"-\infty"
            if L.is_finite:
                asym.append(rf"y = {latex(L)} \text{{ orizzontale per }} x \to {side}")
            elif L in (sp.oo, -sp.oo):
                m = sp.limit(expr / var, var, inf)
                if m.is_finite and m != 0:
                    q = sp.limit(expr - m * var, var, inf)
                    if q.is_finite:
                        asym.append(rf"y = {latex(m * var + q)} \text{{ obliquo per }} x \to {side}")
    # rimuove duplicati mantenendo l'ordine
    asym = list(dict.fromkeys(asym))
    sections.append({"title": "Asintoti", "items": asym or [r"\text{nessun asintoto}"]})

    # derivata prima
    d1 = nice(sp.diff(expr, var))
    crit = _real_roots(d1, var, domain)
    mono = _sign_intervals(d1, var, domain)
    extrema = []
    for c in crit:
        d2c = sp.simplify(sp.diff(d1, var).subs(var, c))
        kind = "minimo relativo" if d2c.is_positive else "massimo relativo" if d2c.is_negative else "punto stazionario"
        extrema.append(rf"x = {latex(c)}:\ \text{{{kind}}},\ f({latex(c)}) = {latex(sp.simplify(expr.subs(var, c)))}")
    sections.append({
        "title": "Derivata prima e monotonia",
        "items": [rf"f'(x) = {latex(d1)}"] + extrema,
        "signs": [{"sign": s["sign"], "set": s["set"],
                   "label": "crescente" if s["sign"] == "+" else "decrescente"} for s in mono],
    })

    # derivata seconda
    d2 = nice(sp.diff(d1, var))
    flex = _real_roots(d2, var, domain)
    conc = _sign_intervals(d2, var, domain)
    sections.append({
        "title": "Derivata seconda e concavità",
        "items": [rf"f''(x) = {latex(d2)}"]
        + [rf"\text{{flesso candidato in }} x = {latex(p)}" for p in flex],
        "signs": [{"sign": s["sign"], "set": s["set"],
                   "label": "convessa" if s["sign"] == "+" else "concava"} for s in conc],
    })

    # finestra del grafico centrata sui punti notevoli
    notable = [float(p) for p in [*zeros, *crit, *flex, *boundary] if p.is_real]
    lo, hi = (min(notable), max(notable)) if notable else (-5.0, 5.0)
    pad = max(3.0, (hi - lo) * 0.6)
    plot = _sample(expr, var, lo - pad, hi + pad)
    points = [{"x": float(c), "y": float(sp.N(expr.subs(var, c))), "label": "estremo"} for c in crit]
    points += [{"x": float(p), "y": float(sp.N(expr.subs(var, p))), "label": "flesso"} for p in flex]
    points = [p for p in points if math.isfinite(p["y"])]

    plot["vertical"] = sorted(vertical)
    return {"input": rf"f(x) = {latex(expr)}", "sections": sections, "plot": plot, "points": points}
