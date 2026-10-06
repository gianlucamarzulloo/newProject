/* Funzioni comuni ai simulatori di fisica (girano solo nel browser). */
window.Sim = (function () {
  "use strict";

  function rk4(f, y, h) {
    const add = (a, b, s) => a.map((v, i) => v + s * b[i]);
    const k1 = f(y);
    const k2 = f(add(y, k1, h / 2));
    const k3 = f(add(y, k2, h / 2));
    const k4 = f(add(y, k3, h));
    return y.map((v, i) => v + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]));
  }

  function fmt(v, digits) {
    if (!isFinite(v)) return "–";
    return v.toLocaleString("it-IT", {maximumFractionDigits: digits == null ? 2 : digits});
  }

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function plot(div, traces, layout) {
    const axis = {gridcolor: css("--border"), zerolinecolor: css("--muted"), automargin: true};
    const lay = Object.assign({
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: {color: css("--text"), family: "inherit"}, margin: {l: 50, r: 16, t: 16, b: 40},
      legend: {orientation: "h", y: -0.2},
      colorway: ["#2357d9", "#e8590c", "#2b8a3e", "#ae3ec9", "#c92a2a", "#1098ad"],
    }, layout || {});
    lay.xaxis = Object.assign({}, axis, (layout || {}).xaxis);
    lay.yaxis = Object.assign({}, axis, (layout || {}).yaxis);
    Plotly.react(div, traces, lay, {responsive: true, displaylogo: false});
  }

  function bindSliders(onChange) {
    document.querySelectorAll('input[type="range"]').forEach((input) => {
      const out = document.querySelector(`output[data-for="${input.id}"]`);
      const show = () => { if (out) out.textContent = fmt(+input.value) + (input.dataset.unit || ""); };
      input.addEventListener("input", () => { show(); onChange(); });
      show();
    });
  }

  return {rk4, fmt, plot, bindSliders};
})();
