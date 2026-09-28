"use strict";

const cases = JSON.parse(document.getElementById("chart-data").textContent);
cases.forEach((item, index) => { item.caseIndex = index; });
const metricKeys = [...new Set(cases.flatMap(item => Object.keys(item.metrics)))].sort();
const tagFilters = [...document.querySelectorAll("select[data-tag]")];
const categoryFilter = document.getElementById("category-filter");
const errorsOnly = document.getElementById("errors-only");
const colorTargetType = document.getElementById("color-target-type");
const colorTarget = document.getElementById("color-target");
const ruleColor = document.getElementById("rule-color");
const paletteButtons = [...document.querySelectorAll(".palette-color")];
const colorRules = new Map();
const charts = document.getElementById("charts");
const svgNamespace = "http://www.w3.org/2000/svg";
const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });
const defaultBlue = "#2866c9";
const defaultRed = "#c0392b";
const pieBlues = ["#2866c9", "#174ea6", "#4785db", "#345fb0", "#6a9ee4", "#244984"];
let highlightedDetail = null;
let highlightTimer = null;

function jumpToCase(index) {
  const detail = document.querySelector(`#case-details details[data-case-index="${index}"]`);
  if (!detail || detail.hidden) return;
  if (highlightedDetail) highlightedDetail.classList.remove("jump-highlight");
  clearTimeout(highlightTimer);
  highlightedDetail = detail;
  detail.open = true;
  detail.classList.add("jump-highlight");
  detail.scrollIntoView({ behavior: "smooth", block: "center" });
  detail.querySelector("summary").focus({ preventScroll: true });
  highlightTimer = setTimeout(() => {
    detail.classList.remove("jump-highlight");
    if (highlightedDetail === detail) highlightedDetail = null;
  }, 2200);
}

function makeCaseLink(element, point) {
  element.classList.add("chart-point");
  element.setAttribute("role", "button");
  element.setAttribute("tabindex", "0");
  element.setAttribute("aria-label", `View case ${point.id} in case details` +
    (point.errorCount ? `, ${point.errorCount} tool errors` : ""));
  element.addEventListener("click", () => jumpToCase(point.caseIndex));
  element.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      jumpToCase(point.caseIndex);
    }
  });
}

function labelForMetric(key) {
  return key.replaceAll(".", " / ").replaceAll("_", " ");
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNamespace, name);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, value);
  }
  return element;
}

function svgText(parent, value, attributes) {
  const element = svgElement("text", attributes);
  element.textContent = value;
  parent.append(element);
}

function selectedCases() {
  const included = tagFilters.filter(select => select.value === "include")
    .map(select => select.dataset.tag);
  const excluded = tagFilters.filter(select => select.value === "exclude")
    .map(select => select.dataset.tag);
  return cases.filter(item =>
    (!categoryFilter.value || item.category === categoryFilter.value) &&
    (!errorsOnly.checked || item.errorCount > 0) &&
    included.every(tag => item.tags.includes(tag)) &&
    excluded.every(tag => !item.tags.includes(tag))
  );
}

function caseColor(item) {
  let color = item.errorCount ? defaultRed : defaultBlue;
  let overridden = false;
  const allRule = colorRules.get("category:*");
  if (allRule) {
    color = allRule.color;
    overridden = true;
  }
  const categoryRule = colorRules.get(`category:${item.category}`);
  if (categoryRule) {
    color = categoryRule.color;
    overridden = true;
  }
  for (const rule of colorRules.values()) {
    if (rule.type === "tag" && item.tags.includes(rule.value)) {
      color = rule.color;
      overridden = true;
    }
  }
  return { color, overridden };
}

function populateColorTargets() {
  const values = colorTargetType.value === "category"
    ? [...new Set(cases.map(item => item.category).filter(Boolean))].sort()
    : [...new Set(cases.flatMap(item => item.tags))].sort();
  colorTarget.replaceChildren();
  if (colorTargetType.value === "category") colorTarget.add(new Option("All", "*"));
  values.forEach(value => colorTarget.add(new Option(value, value)));
  document.getElementById("add-color-rule").disabled = !colorTarget.options.length;
}

function updatePaletteSelection() {
  paletteButtons.forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.color === ruleColor.value));
  });
}

function showColorRules() {
  const list = document.getElementById("color-rules");
  list.replaceChildren();
  document.getElementById("clear-color-rules").disabled = colorRules.size === 0;
  if (!colorRules.size) {
    list.textContent = "No color overrides.";
    return;
  }
  for (const [key, rule] of colorRules) {
    const row = document.createElement("div");
    row.className = "color-rule";
    const label = document.createElement("strong");
    const targetName = rule.type === "category" && rule.value === "*" ? "All" : rule.value;
    label.textContent = `${rule.type}: ${targetName}`;
    const picker = document.createElement("input");
    picker.type = "color";
    picker.value = rule.color;
    picker.setAttribute("aria-label", `Color for ${rule.type} ${targetName}`);
    picker.addEventListener("input", () => {
      rule.color = picker.value;
      refresh();
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove color for ${rule.type} ${targetName}`);
    remove.addEventListener("click", () => {
      colorRules.delete(key);
      showColorRules();
      refresh();
    });
    row.append(label, picker, remove);
    list.append(row);
  }
}

function drawCartesian(container, points, type) {
  const width = Math.max(760, points.length * 90 + 100);
  const height = 390;
  const left = 76;
  const right = 24;
  const top = 24;
  const bottom = 105;
  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;
  let minimum = Math.min(0, ...points.map(point => point.value));
  let maximum = Math.max(0, ...points.map(point => point.value));
  if (minimum === maximum) maximum = minimum + 1;
  const y = value => top + (maximum - value) / (maximum - minimum) * plotHeight;
  const svg = svgElement("svg", {
    width, height, viewBox: `0 0 ${width} ${height}`,
    role: "group", "aria-label": `${type} chart of ${points.length} cases`
  });

  for (let tick = 0; tick <= 4; tick++) {
    const value = minimum + (maximum - minimum) * tick / 4;
    const yy = y(value);
    svg.append(svgElement("line", {
      x1: left, x2: width - right, y1: yy, y2: yy,
      stroke: "#dbe2ed", "stroke-width": 1
    }));
    svgText(svg, numberFormat.format(value), {
      x: left - 10, y: yy + 4, "text-anchor": "end", fill: "#52627a", "font-size": 12
    });
  }
  const step = plotWidth / points.length;
  const coordinates = [];
  points.forEach((point, index) => {
    const x = left + step * (index + 0.5);
    const yy = y(point.value);
    const tooltip = `${point.id}${point.name ? ` - ${point.name}` : ""}: ${numberFormat.format(point.value)}` +
      (point.errorCount ? ` (${point.errorCount} tool errors)` : "");
    if (type === "bar") {
      const baseline = y(0);
      const rect = svgElement("rect", {
        x: x - step * 0.34, y: Math.min(yy, baseline),
        width: step * 0.68, height: Math.max(2, Math.abs(baseline - yy)),
        fill: point.color, stroke: "#34445d", "stroke-width": 0.6
      });
      const title = svgElement("title");
      title.textContent = tooltip;
      rect.append(title);
      makeCaseLink(rect, point);
      svg.append(rect);
    } else {
      coordinates.push({ x, yy, tooltip, point });
    }
    svgText(svg, point.id, {
      x, y: height - bottom + 16, transform: `rotate(-45 ${x} ${height - bottom + 16})`,
      "text-anchor": "end", fill: "#34445d", "font-size": 12
    });
  });
  if (type === "line") {
    svg.append(svgElement("polyline", {
      points: coordinates.map(({ x, yy }) => `${x},${yy}`).join(" "),
      fill: "none", stroke: defaultBlue, "stroke-width": 3
    }));
    for (const { x, yy, tooltip, point } of coordinates) {
      const circle = svgElement("circle", {
        cx: x, cy: yy, r: 7, fill: point.color,
        stroke: "#34445d", "stroke-width": 1
      });
      const title = svgElement("title");
      title.textContent = tooltip;
      circle.append(title);
      makeCaseLink(circle, point);
      svg.append(circle);
    }
  }
  container.append(svg);
}

function drawPie(container, points) {
  const total = points.reduce((sum, point) => sum + point.value, 0);
  if (points.some(point => point.value < 0) || !Number.isFinite(total) || total <= 0) {
    container.textContent = "Pie charts need nonnegative values with a positive total. Choose another metric or chart type.";
    return;
  }
  const svg = svgElement("svg", {
    width: 460, height: 360, viewBox: "0 0 460 360",
    role: "group", "aria-label": `Pie chart of ${points.length} cases`
  });
  const legend = document.createElement("div");
  legend.className = "legend";
  let angle = -Math.PI / 2;
  points.forEach((point, index) => {
    const color = point.overridden || point.errorCount
      ? point.color : pieBlues[index % pieBlues.length];
    const sweep = point.value / total * Math.PI * 2;
    if (point.value > 0) {
      let slice;
      if (sweep >= Math.PI * 2 - 1e-10) {
        slice = svgElement("circle", {
          cx: 230, cy: 180, r: 145, fill: color,
          stroke: "#34445d", "stroke-width": 1
        });
      } else {
        const x1 = 230 + 145 * Math.cos(angle);
        const y1 = 180 + 145 * Math.sin(angle);
        const x2 = 230 + 145 * Math.cos(angle + sweep);
        const y2 = 180 + 145 * Math.sin(angle + sweep);
        slice = svgElement("path", {
          d: `M 230 180 L ${x1} ${y1} A 145 145 0 ${sweep > Math.PI ? 1 : 0} 1 ${x2} ${y2} Z`,
          fill: color, stroke: "white", "stroke-width": 1
        });
      }
      const title = svgElement("title");
      title.textContent = `${point.id}: ${numberFormat.format(point.value)} (${numberFormat.format(point.value / total * 100)}%)`;
      slice.append(title);
      makeCaseLink(slice, point);
      svg.append(slice);
    }
    angle += sweep;
    const item = document.createElement("div");
    item.className = "legend-item";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.backgroundColor = color;
    const text = document.createElement("span");
    text.textContent = `${point.id}: ${numberFormat.format(point.value)} (${numberFormat.format(point.value / total * 100)}%)` +
      (point.errorCount ? ` - ${point.errorCount} tool errors` : "");
    item.append(swatch, text);
    makeCaseLink(item, point);
    legend.append(item);
  });
  container.append(svg, legend);
}

function renderChart(card, filtered) {
  const metric = card.querySelector(".metric-select").value;
  const type = card.querySelector(".type-select").value;
  const canvas = card.querySelector(".chart-scroll");
  const note = card.querySelector(".chart-note");
  canvas.replaceChildren();
  const points = filtered.filter(item => Object.hasOwn(item.metrics, metric))
    .map(item => ({ id: item.id, name: item.name, caseIndex: item.caseIndex,
                    errorCount: item.errorCount, ...caseColor(item),
                    value: item.metrics[metric] }));
  note.textContent = `${points.length} of ${filtered.length} filtered cases have ${labelForMetric(metric)}.`;
  if (!points.length) {
    canvas.textContent = "No values to chart for this selection.";
  } else if (type === "pie") {
    drawPie(canvas, points);
  } else {
    drawCartesian(canvas, points, type);
  }
}

function refresh() {
  const filtered = selectedCases();
  document.getElementById("filter-count").textContent =
    `Showing ${filtered.length} of ${cases.length} cases`;
  const visible = new Set(filtered);
  document.querySelectorAll("#case-details details[data-case-index]").forEach(detail => {
    const item = cases[Number(detail.dataset.caseIndex)];
    detail.hidden = !visible.has(item);
    const { color } = caseColor(item);
    detail.style.setProperty("--case-color", color);
    detail.style.setProperty("--case-tint", `${color}22`);
  });
  charts.querySelectorAll(".chart-card").forEach(card => renderChart(card, filtered));
}

function addChart() {
  const card = document.createElement("div");
  card.className = "chart-card";
  card.innerHTML = '<div class="controls"><label>Metric <select class="metric-select"></select></label>' +
    '<label>Type <select class="type-select"><option value="bar">Bar</option>' +
    '<option value="line">Line</option><option value="pie">Pie</option></select></label>' +
    '<button class="remove-chart" type="button">Remove chart</button></div>' +
    '<p class="chart-note"></p><div class="chart-scroll"></div>';
  const metricSelect = card.querySelector(".metric-select");
  for (const key of metricKeys) {
    metricSelect.add(new Option(labelForMetric(key), key));
  }
  metricSelect.value = metricKeys.includes("latency_seconds") ? "latency_seconds" : metricKeys[0];
  card.querySelector(".remove-chart").addEventListener("click", () => card.remove());
  card.querySelectorAll("select").forEach(select => select.addEventListener("change", refresh));
  charts.append(card);
  refresh();
}

categoryFilter.addEventListener("change", refresh);
errorsOnly.addEventListener("change", refresh);
colorTargetType.addEventListener("change", populateColorTargets);
ruleColor.addEventListener("input", updatePaletteSelection);
paletteButtons.forEach(button => button.addEventListener("click", () => {
  ruleColor.value = button.dataset.color;
  updatePaletteSelection();
}));
document.getElementById("add-color-rule").addEventListener("click", () => {
  if (!colorTarget.value) return;
  const type = colorTargetType.value;
  const value = colorTarget.value;
  const key = `${type}:${value}`;
  colorRules.delete(key);
  colorRules.set(key, { type, value, color: ruleColor.value });
  showColorRules();
  refresh();
});
document.getElementById("clear-color-rules").addEventListener("click", () => {
  colorRules.clear();
  ruleColor.value = defaultBlue;
  updatePaletteSelection();
  showColorRules();
  refresh();
});
tagFilters.forEach(select => select.addEventListener("change", refresh));
document.getElementById("clear-filters").addEventListener("click", () => {
  categoryFilter.value = "";
  errorsOnly.checked = false;
  tagFilters.forEach(select => { select.value = ""; });
  refresh();
});
document.getElementById("add-chart").addEventListener("click", addChart);
populateColorTargets();
updatePaletteSelection();
showColorRules();
addChart();
