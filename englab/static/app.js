/* EngLab: form degli strumenti e rendering dei risultati.
 * Il server restituisce una lista di "blocchi" generici (vedi englab/tools.py);
 * qui ogni tipo di blocco ha il suo renderer. */
(function () {
  "use strict";

  const form = document.getElementById("tool-form");
  if (!form) return;
  const output = document.getElementById("output");
  const api = form.dataset.api;

  // ------------------------------------------------------------------ utilità

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    }
    for (const c of children.flat()) if (c != null) node.append(c);
    return node;
  }

  function tex(source, display) {
    const span = el("span", {class: display ? "math display" : "math"});
    try {
      katex.render(source, span, {displayMode: !!display, throwOnError: false, strict: "ignore"});
    } catch (e) {
      span.textContent = source;
    }
    return span;
  }

  function cell(v) {
    if (v && typeof v === "object" && "m" in v) return v.m ? tex(v.m, false) : "";
    return v == null ? "" : String(v);
  }

  function heading(label) {
    return label ? el("h3", {class: "block-title", text: label}) : null;
  }

  // ------------------------------------------------------------------ renderer dei blocchi

  function stepNode(step, depth) {
    const summary = el("summary", {},
      el("span", {class: "rule", text: step.rule}),
      el("span", {class: "step-eq"}, tex(step.expr + " = " + step.result, false)));
    const body = el("div", {class: "step-body"});
    if (step.note) body.append(el("div", {class: "step-note"}, tex(step.note, false)));
    if (step.substeps && step.substeps.length) {
      body.append(el("div", {class: "substeps"}, step.substeps.map((s) => stepNode(s, depth + 1))));
    }
    const details = el("details", {class: "step"}, summary, body);
    if (depth < 2) details.open = true;
    return details;
  }

  const renderers = {
    result(b) {
      return el("div", {class: "block result"},
        el("div", {class: "result-label", text: b.label}),
        el("div", {class: "result-math"}, tex(b.math, true)),
        b.extra ? el("div", {class: "result-extra", text: b.extra}) : null);
    },
    math(b) {
      return el("div", {class: "block"}, heading(b.label),
        b.items.map((m) => el("div", {class: "math-line"}, tex(m, true))));
    },
    text(b) {
      return el("p", {class: "block note " + (b.tone || "info"), text: b.text});
    },
    tree(b) {
      const toggle = el("button", {type: "button", class: "link-btn", text: "espandi tutto"});
      const wrap = el("div", {class: "tree"}, b.steps.map((s) => stepNode(s, 0)));
      toggle.addEventListener("click", () => {
        const open = toggle.textContent === "espandi tutto";
        wrap.querySelectorAll("details").forEach((d) => (d.open = open));
        toggle.textContent = open ? "comprimi" : "espandi tutto";
      });
      return el("div", {class: "block"}, el("div", {class: "block-head"}, heading(b.label), toggle), wrap);
    },
    matsteps(b) {
      return el("div", {class: "block"}, heading(b.label),
        el("ol", {class: "matsteps"}, b.steps.map((s) =>
          el("li", {}, el("div", {class: "op"}, s.op.includes("\\") || s.op.includes("_") ? tex(s.op, false) : s.op),
            el("div", {class: "mat"}, tex(s.matrix, true))))));
    },
    table(b) {
      const thead = el("thead", {}, el("tr", {}, b.cols.map((c) => el("th", {text: c}))));
      const tbody = el("tbody", {}, b.rows.map((r) => el("tr", {}, r.map((c) => el("td", {}, cell(c))))));
      return el("div", {class: "block"}, heading(b.label), el("div", {class: "table-wrap"}, el("table", {}, thead, tbody)));
    },
    plot(b) {
      const div = el("div", {class: "plot"});
      const block = el("div", {class: "block"}, heading(b.label), div);
      requestAnimationFrame(() => drawPlot(div, b.traces, b.layout));
      return block;
    },
    code(b) {
      const pre = el("pre", {}, el("code", {text: b.code}));
      const copy = el("button", {type: "button", class: "link-btn", text: "copia"});
      copy.addEventListener("click", () => {
        navigator.clipboard.writeText(b.code).then(() => { copy.textContent = "copiato ✓"; });
      });
      const details = el("details", {class: "code-block"},
        el("summary", {}, el("span", {text: b.label}), copy), pre);
      return el("div", {class: "block"}, details);
    },
    signs(b) {
      return el("div", {class: "block"}, heading(b.label),
        el("ul", {class: "signs"}, b.items.map((s) =>
          el("li", {}, el("span", {class: "sign " + (s.sign === "+" ? "pos" : "neg"), text: s.sign === "+" ? "> 0" : "< 0"}),
            tex(s.set, false), s.label ? el("span", {class: "muted", text: " → " + s.label}) : null))));
    },
    section(b) {
      return el("section", {class: "block subsection"}, el("h3", {class: "block-title", text: b.title}),
        b.blocks.map(renderBlock));
    },
  };

  function renderBlock(b) {
    const r = renderers[b.t];
    return r ? r(b) : el("pre", {text: JSON.stringify(b)});
  }

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function drawPlot(div, traces, layout) {
    if (!window.Plotly) {
      // Plotly è caricato con defer: riprova finché non è pronto
      setTimeout(() => drawPlot(div, traces, layout), 100);
      return;
    }
    const fg = css("--text"), grid = css("--border");
    const axis = {gridcolor: grid, zerolinecolor: css("--muted"), linecolor: grid, automargin: true};
    const base = {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {color: fg, family: "inherit"}, margin: {l: 50, r: 16, t: 16, b: 40},
      legend: {orientation: "h", y: -0.2}, hovermode: "closest",
      colorway: ["#2357d9", "#e8590c", "#2b8a3e", "#ae3ec9", "#c92a2a", "#1098ad"],
    };
    const lay = Object.assign({}, base, layout);
    lay.xaxis = Object.assign({}, axis, layout.xaxis || {});
    lay.yaxis = Object.assign({}, axis, layout.yaxis || {});
    if (lay.yaxis.range === null) delete lay.yaxis.range;
    Plotly.newPlot(div, traces, lay, {responsive: true, displaylogo: false,
      modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d"]});
  }

  // ------------------------------------------------------------------ form

  function values() {
    const data = {};
    new FormData(form).forEach((v, k) => (data[k] = v));
    return data;
  }

  function setValues(data) {
    for (const [k, v] of Object.entries(data)) {
      const input = form.elements.namedItem(k);
      if (input) input.value = v;
    }
    updateVisibility();
  }

  function updateVisibility() {
    form.querySelectorAll("[data-show-if]").forEach((label) => {
      const cond = JSON.parse(label.dataset.showIf);
      const visible = Object.entries(cond).every(([field, allowed]) => {
        const input = form.elements.namedItem(field);
        return input && allowed.includes(input.value);
      });
      label.hidden = !visible;
    });
  }

  function shareUrl() {
    const params = new URLSearchParams();
    const data = values();
    form.querySelectorAll("[data-field]").forEach((label) => {
      if (!label.hidden && data[label.dataset.field] !== "") params.set(label.dataset.field, data[label.dataset.field]);
    });
    return location.origin + location.pathname + "?" + params.toString();
  }

  let controller = null;
  async function compute() {
    if (controller) controller.abort();
    controller = new AbortController();
    output.replaceChildren(el("div", {class: "loading"}, el("span", {class: "spinner"}), "Calcolo in corso…"));
    output.scrollIntoView({behavior: "smooth", block: "nearest"});
    try {
      const res = await fetch(api, {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify(values()), signal: controller.signal,
      });
      const data = await res.json().catch(() => ({error: "Risposta del server non valida."}));
      if (!res.ok || data.error) {
        output.replaceChildren(el("p", {class: "block note warn", text: data.error || "Errore " + res.status}));
        return;
      }
      output.replaceChildren(...data.blocks.map(renderBlock));
      history.replaceState(null, "", shareUrl());
      if (window.plausible) window.plausible("Calcolo", {props: {tool: location.pathname}});
    } catch (e) {
      if (e.name !== "AbortError") {
        output.replaceChildren(el("p", {class: "block note warn", text: "Connessione non riuscita. Riprova."}));
      }
    }
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); compute(); });
  form.addEventListener("change", updateVisibility);
  form.querySelectorAll("textarea").forEach((t) =>
    t.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) compute(); }));

  document.querySelectorAll("[data-example]").forEach((chip) =>
    chip.addEventListener("click", () => {
      form.reset();
      setValues(JSON.parse(chip.dataset.example));
      compute();
    }));

  const share = document.getElementById("share-btn");
  share.addEventListener("click", async () => {
    const url = shareUrl();
    try {
      if (navigator.share && /Mobi/.test(navigator.userAgent)) {
        await navigator.share({title: document.title, url});
      } else {
        await navigator.clipboard.writeText(url);
        share.textContent = "Link copiato ✓";
        setTimeout(() => (share.textContent = "Condividi"), 2000);
      }
    } catch (e) { /* condivisione annullata */ }
  });

  // precompila dai parametri dell'URL (link condivisi) e calcola subito
  const params = new URLSearchParams(location.search);
  if ([...params.keys()].length) {
    const data = {};
    params.forEach((v, k) => (data[k] = v));
    setValues(data);
    compute();
  } else {
    updateVisibility();
  }
})();
