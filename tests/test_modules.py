import math

import pytest
import sympy as sp

from englab.core.parsing import ParseError, parse, x
from englab.modules import algebra, analisi, chimica, numerico


# ------------------------------------------------------------------ analisi

@pytest.mark.parametrize("expr", [
    "x^2 sen(x)", "e^(3x)/ln(x)", "arctg(sqrt(x))", "x^x", "sen(cos(x^2))", "2^x", "ln(abs(x))",
    "(x+1)/(x-1)", "tg(x)", "arcsen(x)^2", "sqrt(1-x^2)", "cosh(x) sinh(x)",
])
def test_derivative_matches_sympy(expr):
    f = parse(expr)
    raw, tree = analisi._d(f, x)
    assert sp.simplify(raw - sp.diff(f, x)) == 0
    assert tree["rule"]


def test_derivative_rules_are_explained():
    r = analisi.derivata("x^2 sen(x)")
    assert r["steps"][0]["rule"] == "Regola del prodotto"
    r = analisi.derivata("sen(x)/x")
    assert r["steps"][0]["rule"] == "Regola del quoziente"
    r = analisi.derivata("sen(x^2)")
    assert r["steps"][0]["rule"] == "Regola della catena"


def test_higher_order_derivative():
    r = analisi.derivata("x^4", "x", 3)
    assert r["result"] == "24 x"
    assert len(r["steps"]) == 3


@pytest.mark.parametrize("expr", ["x e^x", "1/(x^2-1)", "x/(1+x^2)", "ln(x)", "e^x cos(x)", "sen(x)^2"])
def test_integral_is_a_primitive(expr):
    f = parse(expr)
    r = analisi.integrale(expr)
    F = sp.sympify(r["result_plain"], locals={"x": x})
    assert sp.simplify(sp.diff(F, x) - f) == 0
    assert r["steps"], "dovrebbero esserci i passaggi"


def test_definite_integral():
    r = analisi.integrale("1/(1+x^2)", "x", "0", "1")
    assert float(r["definite"]["numeric"]) == pytest.approx(math.pi / 4)


def test_parts_rule_is_detected():
    r = analisi.integrale("x e^x")
    assert r["steps"][0]["rule"] == "Integrazione per parti"


def test_non_elementary_integral():
    with pytest.raises(ParseError):
        analisi.integrale("e^(-x^2)/ln(x)")


@pytest.mark.parametrize("expr, point, expected", [
    ("sen(x)/x", "0", "1"), ("(1+1/x)^x", "inf", "e"), ("(x^2-4)/(x-2)", "2", "4"),
    ("(e^x-1-x)/x^2", "0", r"\frac{1}{2}"),
])
def test_limits(expr, point, expected):
    assert analisi.limite(expr, point)["result"] == expected


def test_limit_does_not_exist():
    r = analisi.limite("1/x", "0")
    assert not r["exists"]
    assert analisi.limite("1/x", "0", "x", "+")["result"] == r"\infty"


def test_hopital_step():
    rules = [s["rule"] for s in analisi.limite("sen(x)/x", "0")["steps"]]
    assert "Forma indeterminata" in rules


def test_function_study():
    r = analisi.studio_funzione("(x^2-1)/(x-2)")
    titles = [s["title"] for s in r["sections"]]
    assert titles[0] == "Dominio"
    asym = " ".join(next(s for s in r["sections"] if s["title"] == "Asintoti")["items"])
    assert "verticale" in asym and "obliquo" in asym
    assert r["plot"]["vertical"] == [2.0]
    assert len(r["points"]) == 2


def test_function_study_parity():
    r = analisi.studio_funzione("e^(-x^2)")
    assert "pari" in r["sections"][1]["text"] and "né" not in r["sections"][1]["text"]


# ------------------------------------------------------------------ algebra

def test_matrix_parsing():
    m = algebra.parse_matrix("1 2\n1/2 sqrt(2)")
    assert m == sp.Matrix([[1, 2], [sp.Rational(1, 2), sp.sqrt(2)]])
    with pytest.raises(ParseError):
        algebra.parse_matrix("1 2\n3")


def test_gauss_rref():
    m = sp.Matrix([[1, 2, 3], [4, 5, 6], [7, 8, 10]])
    final, steps, pivots = algebra.gauss_steps(m)
    assert final == m.rref()[0]
    assert len(pivots) == 3
    assert len(steps) > 1


def test_determinant_and_inverse():
    assert algebra.determinante("1 2 3\n4 5 6\n7 8 10")["result"] == "-3"
    assert algebra.determinante("k 1\n1 k")["result"] in ("k^{2} - 1", r"\left(k - 1\right) \left(k + 1\right)")
    assert algebra.inversa("1 2\n2 4")["invertible"] is False
    r = algebra.inversa("2 1\n1 1")
    assert "-1" in r["result"]


def test_linear_system_cases():
    assert algebra.sistema("1 1 1 6\n0 2 5 -4\n2 5 -1 27")["solution"] == ["x_{1} = 5", "x_{2} = 3", "x_{3} = -2"]
    assert "infinite" in algebra.sistema("1 1 2\n2 2 4")["verdict"]
    assert algebra.sistema("1 1 2\n1 1 3")["solution"] is None


def test_eigen():
    r = algebra.autovalori("2 0 0\n0 3 4\n0 4 9")
    assert sorted(e["value"] for e in r["eigen"]) == ["1", "11", "2"]
    assert r["diagonalizable"] and r["symmetric"]
    assert not algebra.autovalori("1 1\n0 1")["diagonalizable"]


def test_parameter_discussion():
    r = algebra.discussione("1 k 1\nk 1 1\n1 1 k")
    ranks = {c["cond"]: c["rank"] for c in r["cases"]}
    assert ranks["k = -2"] == 2
    assert ranks["k = 1"] == 1


# ------------------------------------------------------------------ numerico

@pytest.mark.parametrize("metodo, kw", [
    ("bisezione", {"a": "1", "b": "2"}),
    ("newton", {"x0": "1"}),
    ("secanti", {"x0": "1", "x1": "2"}),
])
def test_root_finding(metodo, kw):
    r = numerico.zeri("x^2-2", metodo, **kw, tol="1e-10")
    assert r["converged"]
    assert r["root"] == pytest.approx(math.sqrt(2), abs=1e-8)


def test_newton_is_quadratic():
    assert numerico.zeri("x^3-2x-5", "newton", x0="2")["order"] == pytest.approx(2, abs=0.3)


def test_bisection_needs_sign_change():
    with pytest.raises(ParseError):
        numerico.zeri("x^2+1", "bisezione", a="0", b="1")


def test_quadrature_orders():
    r = numerico.quadratura("sen(x)", "0", "pi", 8)
    assert r["exact"] == pytest.approx(2)
    orders = r["convergence"]["orders"]
    assert orders["trapezi"] == pytest.approx(2, abs=0.2)
    assert orders["simpson"] == pytest.approx(4, abs=0.3)


def test_ode_methods_order():
    r = numerico.ode("-2y + t", "0", "1", "2", "0.1")
    assert r["exact"] is not None
    e = r["errors"]
    assert e["runge_kutta4"] < e["heun"] < e["eulero"]


def test_runge_phenomenon():
    r = numerico.interpolazione("1/(1+25x^2)", "-1", "1", 10)
    assert r["equispaziati"]["max_error"] > 10 * r["chebyshev"]["max_error"]


# ------------------------------------------------------------------ chimica

@pytest.mark.parametrize("formula, mass", [("H2O", 18.015), ("Ca(OH)2", 74.092), ("CuSO4*5H2O", 249.677)])
def test_molar_mass(formula, mass):
    assert chimica.massa_molare(formula)["molar_mass"] == pytest.approx(mass, abs=0.01)


@pytest.mark.parametrize("reaction, balanced", [
    ("H2 + O2 -> H2O", "2H2 + O2 → 2H2O"),
    ("C3H8 + O2 -> CO2 + H2O", "C3H8 + 5O2 → 3CO2 + 4H2O"),
    ("KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2", "2KMnO4 + 16HCl → 2KCl + 2MnCl2 + 8H2O + 5Cl2"),
])
def test_balance(reaction, balanced):
    r = chimica.bilancia(reaction)
    assert r["balanced"] == balanced
    assert all(c["left"] == c["right"] for c in r["check"])


def test_bad_formula():
    with pytest.raises(ParseError):
        chimica.massa_molare("Xx2")
    with pytest.raises(ParseError):
        chimica.massa_molare("Ca(OH")


def test_limiting_reagent():
    r = chimica.stechiometria("H2 + O2 -> H2O", {"H2": 4, "O2": 16})
    assert r["limiting"] == "O2"
    water = next(t for t in r["table"] if t["formula"] == "H2O")
    assert water["mass_reacting"] == pytest.approx(18.0, abs=0.05)
