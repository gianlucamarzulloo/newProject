"""Registro degli strumenti del sito.

Ogni strumento definisce: pagina (titolo/descrizione SEO, testo di teoria),
campi del form, esempi, la funzione di calcolo e un "presenter" che trasforma
il risultato in una lista di blocchi generici renderizzati dal frontend
(vedi static/app.js). Aggiungere uno strumento = aggiungere una voce qui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .core.parsing import ParseError, parse_number
from .modules import algebra, analisi, chimica, numerico


# --------------------------------------------------------------------------- blocchi

def b_result(label: str, math: str, extra: str = "") -> dict:
    return {"t": "result", "label": label, "math": math, "extra": extra}


def b_math(items: list[str], label: str = "") -> dict:
    return {"t": "math", "label": label, "items": items}


def b_text(text: str, tone: str = "info") -> dict:
    return {"t": "text", "text": text, "tone": tone}


def b_tree(steps: list[dict], label: str = "Passaggi") -> dict:
    return {"t": "tree", "label": label, "steps": steps}


def b_matsteps(steps: list[dict], label: str = "Passaggi") -> dict:
    return {"t": "matsteps", "label": label, "steps": steps}


def b_table(cols: list[str], rows: list[list[Any]], label: str = "") -> dict:
    return {"t": "table", "label": label, "cols": cols, "rows": rows}


def b_plot(traces: list[dict], layout: dict | None = None, label: str = "") -> dict:
    return {"t": "plot", "label": label, "traces": traces, "layout": layout or {}}


def b_code(code: str, label: str = "Codice Python del metodo") -> dict:
    return {"t": "code", "label": label, "code": code}


def b_signs(items: list[dict], label: str) -> dict:
    return {"t": "signs", "label": label, "items": items}


def b_section(title: str, blocks: list[dict]) -> dict:
    return {"t": "section", "title": title, "blocks": blocks}


def m(tex: str) -> dict:
    """Cella di tabella da renderizzare come formula."""
    return {"m": tex}


def fmt(v: float | None, digits: int = 10) -> str:
    return "—" if v is None else f"{v:.{digits}g}"


# --------------------------------------------------------------------------- presenter

def p_derivata(r: dict) -> list[dict]:
    n, v = r["order"], r["var"]
    op = rf"\frac{{d}}{{d{v}}}" if n == 1 else rf"\frac{{d^{{{n}}}}}{{d{v}^{{{n}}}}}"
    blocks = [b_result("Risultato", rf"{op}\left[{r['input']}\right] = {r['result']}")]
    for i, tree in enumerate(r["steps"], 1):
        blocks.append(b_tree([tree], "Passaggi" if n == 1 else f"Derivata di ordine {i}"))
    return blocks


def p_integrale(r: dict) -> list[dict]:
    blocks = [b_result("Primitiva", rf"{r['input']} = {r['result']}")]
    if "definite" in r:
        d = r["definite"]
        blocks.append(b_result("Integrale definito", rf"{d['input']} = {d['fundamental']} = {d['result']}",
                               f"≈ {d['numeric']}" if d["numeric"] else ""))
    if r["steps"]:
        blocks.append(b_tree(r["steps"]))
    else:
        blocks.append(b_text("Per questo integrale non sono disponibili i passaggi dettagliati, "
                             "ma il risultato è verificato.", "warn"))
    return blocks


def p_limite(r: dict) -> list[dict]:
    blocks = [b_result("Risultato", rf"{r['input']} = {r['result']}",
                       f"≈ {r['numeric']}" if r["numeric"] and r["numeric"] not in r["result"] else "")]
    if r["steps"]:
        blocks.append(b_tree(r["steps"]))
    if not r["exists"]:
        blocks.append(b_text("Il limite non esiste: i limiti destro e sinistro sono diversi.", "warn"))
    return blocks


def p_studio(r: dict) -> list[dict]:
    blocks = [b_result("Funzione", r["input"])]
    traces = [{"x": r["plot"]["x"], "y": r["plot"]["y"], "mode": "lines", "name": "f(x)"}]
    if r["points"]:
        traces.append({"x": [p["x"] for p in r["points"]], "y": [p["y"] for p in r["points"]],
                       "mode": "markers+text", "name": "punti notevoli",
                       "text": [p["label"] for p in r["points"]], "textposition": "top center"})
    plot = r["plot"]
    lo, hi = plot["yrange"] or [None, None]
    for xv in plot["vertical"]:
        traces.append({"x": [xv, xv], "y": [lo, hi], "mode": "lines", "name": f"asintoto x = {fmt(xv, 4)}",
                       "line": {"dash": "dash", "width": 1}, "showlegend": False, "hoverinfo": "name"})
    layout = {"xaxis": {"zeroline": True}, "yaxis": {"zeroline": True}}
    if plot["yrange"]:
        layout["yaxis"]["range"] = plot["yrange"]
    blocks.append(b_plot(traces, layout, "Grafico"))
    for s in r["sections"]:
        inner = []
        if s.get("text"):
            inner.append(b_text(s["text"]))
        if s.get("items"):
            inner.append(b_math(s["items"]))
        if s.get("signs"):
            inner.append(b_signs(s["signs"], ""))
        blocks.append(b_section(s["title"], inner))
    return blocks


def p_riduzione(r: dict) -> list[dict]:
    return [b_result("Forma a scala ridotta", r["result"], f"Rango = {r['rank']}  ·  colonne pivot: {r['pivots']}"),
            b_matsteps(r["steps"], "Eliminazione di Gauss-Jordan")]


def p_determinante(r: dict) -> list[dict]:
    blocks = [b_result("Determinante", rf"\det {r['input']} = {r['result']}")]
    if r["invertible"] is not None:
        blocks.append(b_text("La matrice è invertibile." if r["invertible"]
                             else "Determinante nullo: la matrice NON è invertibile.",
                             "ok" if r["invertible"] else "warn"))
    if r["steps"]:
        blocks.append(b_matsteps(r["steps"], "Calcolo"))
    return blocks


def p_inversa(r: dict) -> list[dict]:
    if not r["invertible"]:
        return [b_result("Risultato", r["result"])]
    return [b_result("Matrice inversa", rf"A^{{-1}} = {r['result']}"),
            b_matsteps(r["steps"], "Gauss-Jordan su (A | I)")]


def p_sistema(r: dict) -> list[dict]:
    blocks = [b_math([r"\begin{cases}" + r" \\ ".join(r["equations"]) + r"\end{cases}"], "Sistema"),
              b_math([r["rouche"]], "Teorema di Rouché-Capelli"),
              b_text(r["verdict"], "ok" if r["solution"] else "warn")]
    if r["solution"]:
        blocks.insert(0, b_result("Soluzione", r",\quad ".join(r["solution"])))
    blocks.append(b_matsteps(r["steps"], "Riduzione della matrice completa"))
    return blocks


def p_autovalori(r: dict) -> list[dict]:
    rows = [[m(e["value"]), e["alg"], e["geo"], m(r",\ ".join(e["basis"]))] for e in r["eigen"]]
    blocks = [b_math([r["charpoly"]], "Polinomio caratteristico"),
              b_table(["Autovalore", "Molt. algebrica", "Molt. geometrica", "Base dell'autospazio"], rows, "Autovalori e autospazi")]
    if r["diagonalizable"]:
        blocks.append(b_text("La matrice è diagonalizzabile: per ogni autovalore la molteplicità "
                             "algebrica coincide con quella geometrica.", "ok"))
        blocks.append(b_result("Diagonalizzazione", rf"P = {r['P']},\quad D = {r['D']},\quad A = P D P^{{-1}}"))
    else:
        blocks.append(b_text("La matrice NON è diagonalizzabile: almeno un autovalore ha "
                             "molteplicità geometrica minore di quella algebrica.", "warn"))
    if r["symmetric"]:
        blocks.append(b_text("La matrice è simmetrica: per il teorema spettrale è diagonalizzabile "
                             "con una base ortonormale di autovettori.", "info"))
    return blocks


def p_discussione(r: dict) -> list[dict]:
    rows = [[m(c["cond"]), c["rank"], m(c.get("matrix", ""))] for c in r["cases"]]
    return [b_math([r["input"]], "Matrice"), b_math([r["head"]], "Valori critici del parametro"),
            b_table(["Caso", "Rango", "Matrice nel caso"], rows, "Discussione")]


METHOD_NAMES = {"bisezione": "Bisezione", "newton": "Newton (tangenti)", "secanti": "Secanti",
                "punto_fisso": "Punto fisso", "punto_medio": "Punto medio", "trapezi": "Trapezi",
                "simpson": "Cavalieri-Simpson", "eulero": "Eulero esplicito", "heun": "Heun",
                "runge_kutta4": "Runge-Kutta 4"}


def p_zeri(r: dict) -> list[dict]:
    name = METHOD_NAMES[r["method"]]
    extra = f"{r['iterations']} iterazioni"
    if r["order"]:
        extra += f"  ·  ordine di convergenza stimato p ≈ {r['order']}"
    blocks = [b_result(f"Radice ({name})", rf"x^* \approx {fmt(r['root'], 15)}", extra)]
    if not r["converged"]:
        blocks.append(b_text("Tolleranza non raggiunta entro il numero massimo di iterazioni.", "warn"))
    p = r["plot"]
    its = p["iterates"]
    blocks.append(b_plot([
        {"x": p["x"], "y": p["y"], "mode": "lines", "name": "f(x)"},
        {"x": its, "y": [0] * len(its), "mode": "markers+text", "name": "iterate",
         "text": [str(i + 1) for i in range(len(its))], "textposition": "top center"},
    ], {}, "Funzione e iterate"))
    errs = [row["err"] for row in r["rows"]]
    blocks.append(b_plot([{"x": list(range(1, len(errs) + 1)), "y": errs, "mode": "lines+markers", "name": "errore"}],
                         {"yaxis": {"type": "log", "title": "|x_k+1 - x_k|"}, "xaxis": {"title": "k"}},
                         "Convergenza (scala logaritmica)"))
    blocks.append(b_table(["k", "x_k", "f(x_k)", "errore"],
                          [[row["k"] + 1, fmt(row["x"], 15), fmt(row["fx"], 6), fmt(row["err"], 4)] for row in r["rows"]],
                          "Tabella delle iterazioni"))
    blocks.append(b_code(r["code"]))
    return blocks


def p_quadratura(r: dict) -> list[dict]:
    lo, hi = r["interval"]
    exact = rf"{r['exact_tex']} \approx {fmt(r['exact'], 12)}" if r["exact_tex"] else rf"\approx {fmt(r['exact'], 12)}"
    blocks = [b_result("Valore esatto", rf"\int_{{{fmt(lo)}}}^{{{fmt(hi)}}} {r['function']}\,dx = {exact}")]
    rows = [[METHOD_NAMES[k], fmt(v["value"], 12), fmt(v["error"], 3),
             r["convergence"]["orders"].get(k, "—")] for k, v in r["results"].items()]
    blocks.append(b_table(["Metodo", f"Valore (n = {r['n']})", "Errore", "Ordine stimato"], rows, "Confronto"))
    conv = r["convergence"]
    blocks.append(b_plot([{"x": conv["n"], "y": errs, "mode": "lines+markers", "name": METHOD_NAMES[k]}
                          for k, errs in conv["errors"].items()],
                         {"xaxis": {"type": "log", "title": "n (sottointervalli)"},
                          "yaxis": {"type": "log", "title": "errore"}},
                         "Errore al crescere di n (scala log-log: la pendenza è l'ordine)"))
    p = r["plot"]
    blocks.append(b_plot([{"x": p["x"], "y": p["y"], "mode": "lines", "fill": "tozeroy", "name": "f(x)"}], {}, "Area sotto la curva"))
    for k, code in r["code"].items():
        blocks.append(b_code(code, f"Codice: {METHOD_NAMES[k]}"))
    return blocks


def p_ode(r: dict) -> list[dict]:
    blocks = [b_math([r["equation"]], "Problema di Cauchy")]
    if r["exact"]:
        blocks.append(b_result("Soluzione esatta", rf"y(t) = {r['exact']}"))
    ref = r["reference"]
    traces = [{"x": ref["t"], "y": ref["y"], "mode": "lines", "name": ref["label"], "line": {"dash": "dot", "width": 3}}]
    traces += [{"x": d["t"], "y": d["y"], "mode": "lines+markers", "name": METHOD_NAMES[k], "marker": {"size": 4}}
               for k, d in r["methods"].items()]
    blocks.append(b_plot(traces, {"xaxis": {"title": "t"}, "yaxis": {"title": "y"}}, "Confronto dei metodi"))
    blocks.append(b_table(["Metodo", "Ordine teorico", f"Errore massimo ({r['steps']} passi)"],
                          [[METHOD_NAMES[k], {"eulero": 1, "heun": 2, "runge_kutta4": 4}[k], fmt(v, 3)]
                           for k, v in r["errors"].items()], "Errori"))
    for k, code in r["code"].items():
        blocks.append(b_code(code, f"Codice: {METHOD_NAMES[k]}"))
    return blocks


def p_interpolazione(r: dict) -> list[dict]:
    traces = [{"x": r["grid"], "y": r["true"], "mode": "lines", "name": "f(x)", "line": {"width": 3}}]
    for key, label in (("equispaziati", "nodi equispaziati"), ("chebyshev", "nodi di Chebyshev")):
        d = r[key]
        traces.append({"x": r["grid"], "y": d["poly"], "mode": "lines", "name": f"polinomio ({label})"})
        traces.append({"x": d["nodes"], "y": d["values"], "mode": "markers", "name": label, "showlegend": False})
    blocks = [b_plot(traces, {"yaxis": {"range": None}}, f"Interpolazione di grado {r['degree']}"),
              b_table(["Nodi", "Errore massimo"],
                      [["Equispaziati", fmt(r["equispaziati"]["max_error"], 4)],
                       ["Chebyshev", fmt(r["chebyshev"]["max_error"], 4)]], "Confronto")]
    if (r["equispaziati"]["max_error"] or 0) > 2 * (r["chebyshev"]["max_error"] or 0):
        blocks.append(b_text("Con nodi equispaziati l'errore cresce vicino agli estremi (fenomeno di Runge). "
                             "I nodi di Chebyshev, più fitti ai bordi, lo evitano.", "info"))
    blocks.append(b_code(r["code"], "Codice: polinomio di Lagrange"))
    return blocks


def p_massa(r: dict) -> list[dict]:
    return [b_result("Massa molare", rf"M(\mathrm{{{r['formula']}}}) = {r['molar_mass']}\ \mathrm{{g/mol}}"),
            b_table(["Elemento", "Atomi", "Massa atomica", "Contributo (g/mol)", "% in massa"],
                    [[x["el"], x["n"], x["mass"], x["subtotal"], f"{x['percent']} %"] for x in r["rows"]],
                    "Composizione")]


def p_bilancia(r: dict) -> list[dict]:
    return [b_result("Reazione bilanciata", rf"\mathrm{{{_ce(r['balanced'])}}}"),
            b_table(["Specie", "Ruolo", "Coefficiente", "Massa molare (g/mol)"],
                    [[s["formula"], s["role"], s["coeff"], s["molar_mass"]] for s in r["species"]]),
            b_table(["Elemento", "Atomi a sinistra", "Atomi a destra"],
                    [[c["el"], c["left"], c["right"]] for c in r["check"]], "Verifica conservazione degli atomi")]


def p_stechio(r: dict) -> list[dict]:
    blocks = [b_result("Reazione", rf"\mathrm{{{_ce(r['balanced'])}}}")]
    if r["limiting"]:
        blocks.append(b_text(f"Reagente limitante: {r['limiting']}", "ok"))
    rows = [[t["formula"], t["role"], t["molar_mass"], t["mol_reacting"], t["mass_reacting"],
             t.get("given", "—"), t.get("excess", "—")] for t in r["table"]]
    blocks.append(b_table(["Specie", "Ruolo", "M (g/mol)", "Moli che reagiscono/si formano",
                           "Massa (g)", "Massa iniziale (g)", "Eccesso (g)"], rows, "Bilancio di massa"))
    return blocks


def _ce(s: str) -> str:
    """Formula chimica -> LaTeX con pedici (H2O -> H_2O)."""
    s = re.sub(r"(?<=[A-Za-z)\]])(\d+)", r"_{\1}", s)
    return s.replace("→", r"\rightarrow ").replace(" ", r"\ ")


# --------------------------------------------------------------------------- adattatori input

def _stechio(reazione: str, masse: str) -> dict:
    values = {}
    for line in re.split(r"[\n;]+", masse or ""):
        if not line.strip():
            continue
        if "=" not in line:
            raise ParseError("Scrivi le masse come 'formula = grammi', una per riga.")
        k, v = line.split("=", 1)
        values[k.strip()] = parse_number(v.strip())
    return chimica.stechiometria(reazione, values)


# --------------------------------------------------------------------------- registro

@dataclass
class Field:
    name: str
    label: str
    kind: str = "text"  # text | textarea | select | number
    default: str = ""
    placeholder: str = ""
    help: str = ""
    options: list[tuple[str, str]] = field(default_factory=list)
    show_if: dict[str, list[str]] | None = None  # visibile solo per certi valori di un altro campo


@dataclass
class Tool:
    slug: str
    section: str
    name: str
    title: str
    description: str
    fields: list[Field]
    compute: Callable[..., dict]
    present: Callable[[dict], list[dict]]
    examples: list[dict[str, str]]
    theory: str  # HTML (con formule KaTeX tra $...$)

    @property
    def url(self) -> str:
        return f"/{self.section}/{self.slug}"

    def run(self, data: dict[str, Any]) -> dict:
        # argomenti passati per posizione, nell'ordine dei campi
        args = [str(data.get(f.name, f.default) or "")[:2000] for f in self.fields]
        return self.compute(*args)


SECTIONS = {
    "analisi": ("Analisi 1", "Derivate, integrali, limiti e studio di funzione con tutti i passaggi."),
    "algebra": ("Algebra lineare", "Gauss, sistemi, determinanti, inverse, autovalori e discussioni con parametro."),
    "numerico": ("Calcolo numerico", "Zeri, quadratura, ODE e interpolazione con grafici di convergenza e codice."),
    "chimica": ("Chimica", "Masse molari, bilanciamento delle reazioni e stechiometria."),
    "fisica": ("Fisica 1", "Simulatori interattivi di meccanica."),
}

VAR = Field("var", "Variabile", default="x")
MATRIX_HELP = "Una riga per linea, elementi separati da spazi. Ammesse frazioni (1/2) e radici (sqrt(2))."

TOOLS: list[Tool] = [
    Tool(
        "derivate", "analisi", "Derivate", "Calcolatore di derivate con passaggi",
        "Calcola derivate online con tutti i passaggi spiegati: regola del prodotto, del quoziente, della catena. Gratis.",
        [Field("expr", "Funzione f(x)", placeholder="es. x^2 sen(x)", default="x^2 sen(x)"), VAR,
         Field("ordine", "Ordine", kind="select", default="1", options=[(str(i), f"{i}ª") for i in range(1, 5)])],
        lambda expr, var, ordine: analisi.derivata(expr, var, int(ordine)), p_derivata,
        [{"expr": "x^2 sen(x)"}, {"expr": "e^(3x)/ln(x)"}, {"expr": "arctg(sqrt(x))"}, {"expr": "x^x"},
         {"expr": "sen(x)^2 cos(2x)", "ordine": "2"}],
        """<p>La derivata misura la velocità di variazione di una funzione. Le regole fondamentali sono:</p>
<ul><li>linearità: $(af + bg)' = af' + bg'$</li><li>prodotto: $(fg)' = f'g + fg'$</li>
<li>quoziente: $\\left(\\frac{f}{g}\\right)' = \\frac{f'g - fg'}{g^2}$</li>
<li>catena: $(f(g(x)))' = f'(g(x))\\,g'(x)$</li></ul>
<p>Il calcolatore mostra quale regola applica a ogni sotto-espressione, così puoi confrontare il tuo svolgimento passo per passo.</p>""",
    ),
    Tool(
        "integrali", "analisi", "Integrali", "Calcolatore di integrali con passaggi",
        "Risolvi integrali indefiniti e definiti con i passaggi: per parti, per sostituzione, fratti semplici.",
        [Field("expr", "Funzione integranda", placeholder="es. x e^x", default="x e^x"), VAR,
         Field("a", "Estremo inferiore (opzionale)", placeholder="es. 0"),
         Field("b", "Estremo superiore (opzionale)", placeholder="es. pi")],
        analisi.integrale, p_integrale,
        [{"expr": "x e^x"}, {"expr": "1/(x^2-1)"}, {"expr": "sen(x)^2", "a": "0", "b": "pi"},
         {"expr": "x/(1+x^2)"}, {"expr": "ln(x)"}, {"expr": "e^x cos(x)"}],
        """<p>Integrare significa trovare una primitiva $F$ tale che $F'(x) = f(x)$. Le tecniche principali sono:</p>
<ul><li><b>per parti</b>: $\\int f\\,g'\\,dx = fg - \\int f'g\\,dx$</li>
<li><b>per sostituzione</b>: $\\int f(g(x))g'(x)\\,dx = \\int f(u)\\,du$</li>
<li><b>fratti semplici</b> per le funzioni razionali.</li></ul>
<p>Per l'integrale definito si usa il teorema fondamentale: $\\int_a^b f(x)\\,dx = F(b) - F(a)$.</p>""",
    ),
    Tool(
        "limiti", "analisi", "Limiti", "Calcolatore di limiti con passaggi",
        "Calcola limiti online: forme indeterminate, de l'Hôpital, limiti destro e sinistro, limiti all'infinito.",
        [Field("expr", "Funzione", placeholder="es. sen(x)/x", default="sen(x)/x"),
         Field("punto", "x tende a", placeholder="es. 0, inf, -inf", default="0"), VAR,
         Field("direzione", "Direzione", kind="select", default="+-",
               options=[("+-", "bilatero"), ("+", "da destra (x→c⁺)"), ("-", "da sinistra (x→c⁻)")])],
        analisi.limite, p_limite,
        [{"expr": "sen(x)/x", "punto": "0"}, {"expr": "(1+1/x)^x", "punto": "inf"},
         {"expr": "(e^x-1-x)/x^2", "punto": "0"}, {"expr": "1/x", "punto": "0"},
         {"expr": "(x^2-4)/(x-2)", "punto": "2"}],
        """<p>Quando la sostituzione diretta da' una forma indeterminata ($\\frac{0}{0}$, $\\frac{\\infty}{\\infty}$, $0\\cdot\\infty$, $1^\\infty$, ...) servono tecniche come limiti notevoli, confronto tra infiniti o il teorema di de l'Hôpital:</p>
<p>$$\\lim_{x\\to c} \\frac{f(x)}{g(x)} = \\lim_{x\\to c} \\frac{f'(x)}{g'(x)}$$</p>
<p>Scrivi <code>inf</code> per $+\\infty$ e <code>-inf</code> per $-\\infty$.</p>""",
    ),
    Tool(
        "studio-di-funzione", "analisi", "Studio di funzione", "Studio di funzione completo online",
        "Studio di funzione completo: dominio, simmetrie, segno, asintoti, massimi e minimi, flessi e grafico.",
        [Field("expr", "Funzione f(x)", placeholder="es. (x^2-1)/(x-2)", default="x e^(-x)")],
        analisi.studio_funzione, p_studio,
        [{"expr": "x e^(-x)"}, {"expr": "(x^2-1)/(x-2)"}, {"expr": "ln(x)/x"}, {"expr": "x^3-3x"},
         {"expr": "e^(-x^2)"}],
        """<p>Lo schema classico dello studio di funzione è:</p>
<ol><li>dominio</li><li>simmetrie (pari/dispari)</li><li>intersezioni con gli assi e segno</li>
<li>limiti agli estremi del dominio e asintoti (verticali, orizzontali, obliqui)</li>
<li>derivata prima: monotonia, massimi e minimi</li><li>derivata seconda: concavità e flessi</li><li>grafico</li></ol>
<p>Usa questo strumento per <b>verificare</b> il tuo studio: all'esame devi saper giustificare ogni punto.</p>""",
    ),
    Tool(
        "riduzione-gauss", "algebra", "Riduzione di Gauss", "Riduzione a scala con Gauss-Jordan passo passo",
        "Riduci una matrice a scala con l'eliminazione di Gauss-Jordan: ogni operazione elementare sulle righe, rango e pivot.",
        [Field("matrice", "Matrice", kind="textarea", default="1 2 3\n4 5 6\n7 8 10", help=MATRIX_HELP)],
        lambda matrice: algebra.riduzione(matrice), p_riduzione,
        [{"matrice": "1 2 3\n4 5 6\n7 8 10"}, {"matrice": "2 4 -2\n1 3 0\n3 7 -2"},
         {"matrice": "1 1 1 1\n1 2 3 4\n2 3 4 5"}],
        """<p>L'eliminazione di Gauss usa tre operazioni elementari sulle righe, che non cambiano il rango:</p>
<ul><li>scambiare due righe $R_i \\leftrightarrow R_j$</li><li>moltiplicare una riga per $c \\neq 0$</li>
<li>sommare a una riga un multiplo di un'altra $R_i \\to R_i + cR_j$</li></ul>
<p>Il numero di pivot della forma a scala è il <b>rango</b> della matrice.</p>""",
    ),
    Tool(
        "sistemi-lineari", "algebra", "Sistemi lineari", "Risolutore di sistemi lineari con Rouché-Capelli",
        "Risolvi sistemi lineari passo passo: matrice completa, Gauss, teorema di Rouché-Capelli e soluzioni parametriche.",
        [Field("matrice", "Matrice completa (A | b)", kind="textarea", default="1 1 1 6\n0 2 5 -4\n2 5 -1 27",
               help="L'ultima colonna contiene i termini noti. " + MATRIX_HELP)],
        lambda matrice: algebra.sistema(matrice), p_sistema,
        [{"matrice": "1 1 1 6\n0 2 5 -4\n2 5 -1 27"}, {"matrice": "1 2 -1 3\n2 4 -2 6"},
         {"matrice": "1 1 2\n1 1 3"}],
        """<p>Per il <b>teorema di Rouché-Capelli</b> il sistema $Ax = b$ ammette soluzioni se e solo se $\\operatorname{rk}(A) = \\operatorname{rk}(A|b)$.
In tal caso le soluzioni sono $\\infty^{n-r}$, dove $n$ è il numero di incognite e $r$ il rango.</p>""",
    ),
    Tool(
        "determinante", "algebra", "Determinante", "Calcolo del determinante con Sarrus e Laplace",
        "Calcola il determinante di una matrice con i passaggi: formula 2x2, regola di Sarrus, sviluppo di Laplace. Anche con parametri.",
        [Field("matrice", "Matrice quadrata", kind="textarea", default="1 2 3\n4 5 6\n7 8 10", help=MATRIX_HELP)],
        lambda matrice: algebra.determinante(matrice), p_determinante,
        [{"matrice": "1 2 3\n4 5 6\n7 8 10"}, {"matrice": "k 1\n1 k"}, {"matrice": "1 2 0 1\n0 1 1 0\n2 0 1 1\n1 1 1 1"}],
        """<p>Una matrice quadrata è invertibile se e solo se $\\det A \\neq 0$. Per le 3x3 si usa la regola di Sarrus, per dimensioni maggiori lo sviluppo di Laplace:</p>
<p>$$\\det A = \\sum_j (-1)^{i+j} a_{ij} \\det A_{ij}$$</p>""",
    ),
    Tool(
        "matrice-inversa", "algebra", "Matrice inversa", "Calcolo della matrice inversa con Gauss-Jordan",
        "Calcola l'inversa di una matrice con il metodo di Gauss-Jordan su (A | I), mostrando ogni passaggio.",
        [Field("matrice", "Matrice quadrata", kind="textarea", default="2 1 1\n1 3 2\n1 0 0", help=MATRIX_HELP)],
        lambda matrice: algebra.inversa(matrice), p_inversa,
        [{"matrice": "2 1\n1 1"}, {"matrice": "2 1 1\n1 3 2\n1 0 0"}],
        """<p>Si affianca alla matrice $A$ l'identità e si riduce $(A\\,|\\,I)$ con Gauss-Jordan: quando a sinistra compare $I$, a destra c'è $A^{-1}$.</p>""",
    ),
    Tool(
        "autovalori", "algebra", "Autovalori e autovettori", "Autovalori, autovettori e diagonalizzazione",
        "Calcola autovalori, autovettori, molteplicità algebrica e geometrica e verifica se la matrice è diagonalizzabile.",
        [Field("matrice", "Matrice quadrata", kind="textarea", default="2 0 0\n0 3 4\n0 4 9", help=MATRIX_HELP)],
        lambda matrice: algebra.autovalori(matrice), p_autovalori,
        [{"matrice": "2 0 0\n0 3 4\n0 4 9"}, {"matrice": "1 1\n0 1"}, {"matrice": "0 -1\n1 0"},
         {"matrice": "4 1 1\n1 4 1\n1 1 4"}],
        """<p>Gli autovalori sono le radici del polinomio caratteristico $p(\\lambda) = \\det(A - \\lambda I)$.
Una matrice è <b>diagonalizzabile</b> se per ogni autovalore la molteplicità algebrica è uguale a quella geometrica ($\\dim \\ker(A - \\lambda I)$).</p>""",
    ),
    Tool(
        "discussione-parametro", "algebra", "Discussione con parametro", "Rango di una matrice al variare di un parametro",
        "Discuti il rango di una matrice al variare del parametro k: valori critici e rango in ogni caso, come negli esercizi d'esame.",
        [Field("matrice", "Matrice con parametro", kind="textarea", default="1 k 1\nk 1 1\n1 1 k",
               help="Usa una lettera (es. k) come parametro. " + MATRIX_HELP)],
        lambda matrice: algebra.discussione(matrice), p_discussione,
        [{"matrice": "1 k 1\nk 1 1\n1 1 k"}, {"matrice": "1 2 k\n2 4 1"}, {"matrice": "k 1\n4 k"}],
        """<p>Negli esercizi d'esame si chiede spesso di studiare il rango (o la risolubilità di un sistema) al variare di un parametro.
Si cercano i valori che annullano il determinante (o tutti i minori di ordine massimo), poi si studia ogni caso separatamente.</p>""",
    ),
    Tool(
        "zeri-di-funzione", "numerico", "Zeri di funzione", "Bisezione, Newton e secanti con grafici",
        "Trova gli zeri di una funzione con bisezione, Newton, secanti e punto fisso: tabella delle iterazioni, ordine di convergenza e codice Python.",
        [Field("f", "Funzione f(x)", default="x^3 - 2x - 5"),
         Field("metodo", "Metodo", kind="select", default="newton",
               options=[("bisezione", "Bisezione"), ("newton", "Newton"), ("secanti", "Secanti"), ("punto_fisso", "Punto fisso")]),
         Field("a", "a", default="2", show_if={"metodo": ["bisezione"]}),
         Field("b", "b", default="3", show_if={"metodo": ["bisezione"]}),
         Field("x0", "x₀", default="2", show_if={"metodo": ["newton", "secanti", "punto_fisso"]}),
         Field("x1", "x₁", default="3", show_if={"metodo": ["secanti"]}),
         Field("g", "g(x) per x = g(x)", placeholder="vuoto: g(x) = x - f(x)", show_if={"metodo": ["punto_fisso"]}),
         Field("tol", "Tolleranza", default="1e-10")],
        lambda f, metodo, a, b, x0, x1, g, tol: numerico.zeri(f, metodo, a, b, x0, x1, g, tol), p_zeri,
        [{"f": "x^3 - 2x - 5", "metodo": "newton", "x0": "2"},
         {"f": "cos(x) - x", "metodo": "bisezione", "a": "0", "b": "1"},
         {"f": "e^x - 3x", "metodo": "secanti", "x0": "0", "x1": "1"},
         {"f": "x^2 - x - 2", "metodo": "punto_fisso", "x0": "1", "g": "sqrt(x+2)"}],
        """<ul><li><b>Bisezione</b>: dimezza un intervallo $[a,b]$ con $f(a)f(b)<0$. Converge sempre, ma linearmente.</li>
<li><b>Newton</b>: $x_{k+1} = x_k - \\frac{f(x_k)}{f'(x_k)}$. Convergenza quadratica vicino a radici semplici.</li>
<li><b>Secanti</b>: come Newton ma approssima la derivata; ordine $\\frac{1+\\sqrt5}{2} \\approx 1.618$.</li>
<li><b>Punto fisso</b>: $x_{k+1} = g(x_k)$, converge se $|g'(x^*)| < 1$.</li></ul>""",
    ),
    Tool(
        "integrazione-numerica", "numerico", "Integrazione numerica", "Trapezi, Simpson e punto medio a confronto",
        "Confronta le formule di quadratura composite (punto medio, trapezi, Cavalieri-Simpson): errori, ordine di convergenza e codice.",
        [Field("f", "Funzione f(x)", default="e^(-x^2)"), Field("a", "a", default="0"),
         Field("b", "b", default="1"), Field("n", "Sottointervalli n", kind="number", default="8")],
        lambda f, a, b, n: numerico.quadratura(f, a, b, int(float(n))), p_quadratura,
        [{"f": "e^(-x^2)", "a": "0", "b": "1"}, {"f": "sen(x)", "a": "0", "b": "pi"},
         {"f": "sqrt(x)", "a": "0", "b": "1"}, {"f": "1/(1+x^2)", "a": "0", "b": "1", "n": "4"}],
        """<p>Le formule composite dividono $[a,b]$ in $n$ sottointervalli di ampiezza $h$:</p>
<ul><li>punto medio e trapezi: errore $O(h^2)$</li><li>Cavalieri-Simpson: errore $O(h^4)$ per funzioni regolari</li></ul>
<p>Nel grafico log-log la pendenza delle rette è l'ordine di convergenza. Prova con $\\sqrt{x}$ su $[0,1]$: la scarsa regolarità in 0 abbassa l'ordine.</p>""",
    ),
    Tool(
        "equazioni-differenziali", "numerico", "Equazioni differenziali", "Eulero, Heun e Runge-Kutta per ODE",
        "Risolvi numericamente un problema di Cauchy con Eulero, Heun e Runge-Kutta 4 e confronta con la soluzione esatta.",
        [Field("f", "y'(t) = f(t, y)", default="-2y + t"), Field("t0", "t₀", default="0"),
         Field("y0", "y(t₀)", default="1"), Field("T", "Tempo finale T", default="2"),
         Field("h", "Passo h", default="0.1")],
        numerico.ode, p_ode,
        [{"f": "-2y + t", "t0": "0", "y0": "1", "T": "2", "h": "0.1"},
         {"f": "y", "t0": "0", "y0": "1", "T": "3", "h": "0.25"},
         {"f": "y^2 + t", "t0": "0", "y0": "0", "T": "1", "h": "0.1"},
         {"f": "-15y", "t0": "0", "y0": "1", "T": "1", "h": "0.15"}],
        """<p>Dato il problema $y' = f(t,y),\\ y(t_0) = y_0$:</p>
<ul><li><b>Eulero esplicito</b>: $y_{k+1} = y_k + h f(t_k, y_k)$, ordine 1</li>
<li><b>Heun</b>: media di due pendenze, ordine 2</li><li><b>Runge-Kutta 4</b>: quattro pendenze, ordine 4</li></ul>
<p>Prova $y' = -15y$ con $h = 0.15$: Eulero diventa <b>instabile</b> (serve $h < 2/15$).</p>""",
    ),
    Tool(
        "interpolazione", "numerico", "Interpolazione", "Interpolazione polinomiale e fenomeno di Runge",
        "Interpolazione di Lagrange con nodi equispaziati e di Chebyshev: visualizza il fenomeno di Runge.",
        [Field("f", "Funzione f(x)", default="1/(1+25x^2)"), Field("a", "a", default="-1"),
         Field("b", "b", default="1"), Field("n", "Grado n", kind="number", default="10")],
        lambda f, a, b, n: numerico.interpolazione(f, a, b, int(float(n))), p_interpolazione,
        [{"f": "1/(1+25x^2)", "a": "-1", "b": "1", "n": "10"}, {"f": "sen(x)", "a": "0", "b": "6", "n": "5"},
         {"f": "abs(x)", "a": "-1", "b": "1", "n": "12"}],
        """<p>Il polinomio interpolante di Lagrange di grado $n$ passa per $n+1$ nodi. Con nodi equispaziati l'errore può <b>crescere</b> con $n$
(fenomeno di Runge, classico con $f(x) = \\frac{1}{1+25x^2}$). I nodi di Chebyshev $x_k = \\cos\\frac{(2k+1)\\pi}{2(n+1)}$ risolvono il problema.</p>""",
    ),
    Tool(
        "massa-molare", "chimica", "Massa molare", "Calcolatore di massa molare",
        "Calcola la massa molare di un composto e la composizione percentuale in massa. Supporta parentesi e idrati.",
        [Field("formula", "Formula", default="Ca(OH)2", help="Esempi: H2SO4, Ca(OH)2, CuSO4*5H2O")],
        lambda formula: chimica.massa_molare(formula), p_massa,
        [{"formula": "H2SO4"}, {"formula": "Ca(OH)2"}, {"formula": "CuSO4*5H2O"}, {"formula": "C6H12O6"}],
        """<p>La massa molare $M$ (g/mol) è la somma delle masse atomiche degli atomi della formula. Serve per passare da grammi a moli: $n = \\frac{m}{M}$.</p>""",
    ),
    Tool(
        "bilanciamento-reazioni", "chimica", "Bilanciamento", "Bilanciamento delle reazioni chimiche",
        "Bilancia automaticamente le reazioni chimiche con verifica della conservazione degli atomi.",
        [Field("reazione", "Reazione", default="C3H8 + O2 -> CO2 + H2O", help="Usa -> oppure = tra reagenti e prodotti.")],
        lambda reazione: chimica.bilancia(reazione), p_bilancia,
        [{"reazione": "C3H8 + O2 -> CO2 + H2O"}, {"reazione": "KMnO4 + HCl -> KCl + MnCl2 + H2O + Cl2"},
         {"reazione": "Fe2O3 + C -> Fe + CO2"}, {"reazione": "Al + O2 -> Al2O3"}],
        """<p>Bilanciare una reazione significa trovare i coefficienti che conservano il numero di atomi di ogni elemento.
Il calcolatore imposta un sistema lineare omogeneo (un'equazione per elemento) e ne cerca la soluzione intera minima: è algebra lineare applicata!</p>""",
    ),
    Tool(
        "stechiometria", "chimica", "Stechiometria", "Reagente limitante e stechiometria",
        "Trova il reagente limitante, le masse che reagiscono, i prodotti formati e l'eccesso.",
        [Field("reazione", "Reazione", default="H2 + O2 -> H2O"),
         Field("masse", "Masse dei reagenti (g)", kind="textarea", default="H2 = 4\nO2 = 16",
               help="Una per riga, nel formato formula = grammi.")],
        _stechio, p_stechio,
        [{"reazione": "H2 + O2 -> H2O", "masse": "H2 = 4\nO2 = 16"},
         {"reazione": "Fe2O3 + C -> Fe + CO2", "masse": "Fe2O3 = 100\nC = 10"}],
        """<p>Si convertono i grammi in moli, si divide per il coefficiente stechiometrico e il reagente con il rapporto minore è il <b>limitante</b>: determina quanto prodotto si forma.</p>""",
    ),
]

TOOLS_BY_KEY: dict[tuple[str, str], Tool] = {(t.section, t.slug): t for t in TOOLS}

# Strumenti che girano interamente nel browser (nessun calcolo lato server).
CLIENT_TOOLS: list[dict[str, str]] = [
    {"slug": "moto-del-proiettile", "section": "fisica", "name": "Moto del proiettile",
     "title": "Simulatore del moto del proiettile",
     "description": "Simula il moto parabolico: gittata, altezza massima, tempo di volo e traiettoria al variare di velocità e angolo.",
     "template": "fisica_proiettile.html"},
    {"slug": "oscillatore", "section": "fisica", "name": "Oscillatore armonico",
     "title": "Simulatore dell'oscillatore armonico smorzato",
     "description": "Molla con smorzamento: regimi sottosmorzato, critico e sovrasmorzato, energia e grafici in tempo reale.",
     "template": "fisica_oscillatore.html"},
]
CLIENT_BY_KEY = {(t["section"], t["slug"]): t for t in CLIENT_TOOLS}


def execute(section: str, slug: str, data: dict[str, Any]) -> list[dict]:
    """Punto d'ingresso eseguito nel processo sandbox (deve essere picklabile)."""
    tool = TOOLS_BY_KEY[(section, slug)]
    return tool.present(tool.run(data))
