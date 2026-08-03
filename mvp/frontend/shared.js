const LEVEL_LABEL = {1: "Direct evidence", 2: "Historical record", 3: "Contemporary account", 4: "AI inference"};

const SERIES_VARS = [
  "--series-1", "--series-2", "--series-3", "--series-4",
  "--series-5", "--series-6", "--series-7", "--series-8",
];

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function renderSources(sources) {
  if (!sources || !sources.length) return "";
  return `<div class="source-links">${sources
    .map(s => s.url
      ? `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener">${escapeHtml(s.title)} ↗</a>`
      : `<span>${escapeHtml(s.title)}</span>`)
    .join("")}</div>`;
}

function renderClaim(evidence, textOverride) {
  if (!evidence) return "";
  const lvl = evidence.evidence_level;
  return `
    <div class="claim">
      <p><span class="badge lvl-${lvl}">${LEVEL_LABEL[lvl] || "Unknown"}</span>${escapeHtml(textOverride ?? evidence.claim)}</p>
      ${evidence.uncertainty_note ? `<p class="note">${escapeHtml(evidence.uncertainty_note)}</p>` : ""}
      ${renderSources(evidence.sources)}
    </div>`;
}

function renderTrajectoryChart(trajectories) {
  const stageLabels = trajectories[0].points.map(pt => pt.date_range);
  const n = stageLabels.length;
  if (n < 2) return "<p class=\"note\">Not enough stages yet to show a trend.</p>";

  const W = 640, H = 220;
  const mLeft = 26, mRight = 12, mTop = 12, mBottom = 26;
  const plotW = W - mLeft - mRight;
  const plotH = H - mTop - mBottom;
  const xFor = i => mLeft + (plotW * i) / (n - 1);
  const yFor = score => mTop + plotH - (score / 10) * plotH;

  const gridSvg = [0, 2, 4, 6, 8, 10].map(t => {
    const y = yFor(t);
    return `<line class="traj-gridline" x1="${mLeft}" y1="${y}" x2="${W - mRight}" y2="${y}" />
            <text class="traj-axis-label" x="${mLeft - 6}" y="${y + 3}" text-anchor="end">${t}</text>`;
  }).join("");

  const xLabelsSvg = stageLabels.map((label, i) =>
    `<text class="traj-axis-label" x="${xFor(i)}" y="${H - 6}" text-anchor="middle">${escapeHtml(label)}</text>`
  ).join("");

  const linesSvg = trajectories.map((traj, si) => {
    const color = `var(${SERIES_VARS[si % SERIES_VARS.length]})`;
    const pts = traj.points.map((pt, i) => `${xFor(i)},${yFor(pt.score)}`).join(" ");
    const lastPt = traj.points[traj.points.length - 1];
    return `<polyline class="traj-line" points="${pts}" style="stroke:${color}" />
            <circle class="traj-dot" cx="${xFor(n - 1)}" cy="${yFor(lastPt.score)}" r="4" style="fill:${color}" />`;
  }).join("");

  const segW = plotW / n;
  const hitSvg = stageLabels.map((_, i) =>
    `<rect class="traj-hit" data-index="${i}" x="${mLeft + segW * i}" y="${mTop}" width="${segW}" height="${plotH}" />`
  ).join("");

  const legendSvg = trajectories.map((traj, si) => `
    <div class="traj-legend-item">
      <span class="traj-legend-key" style="background:var(${SERIES_VARS[si % SERIES_VARS.length]})"></span>
      <span>${escapeHtml(traj.dimension)}</span>
    </div>`).join("");

  const tableRows = trajectories.map(traj => `
    <tr>
      <td>${escapeHtml(traj.dimension)}</td>
      ${traj.points.map(pt => {
        const lvl = LEVEL_LABEL[pt.evidence.evidence_level] || "Unknown";
        const hoverText = `[${lvl}] ${pt.evidence.claim}${pt.evidence.uncertainty_note ? " — " + pt.evidence.uncertainty_note : ""}`;
        return `<td title="${escapeHtml(hoverText)}">${pt.score}/10</td>`;
      }).join("")}
    </tr>`).join("");

  const allSources = [];
  const seenKeys = new Set();
  trajectories.forEach(traj => traj.points.forEach(pt => (pt.evidence.sources || []).forEach(s => {
    const key = s.url || s.title;
    if (!seenKeys.has(key)) { seenKeys.add(key); allSources.push(s); }
  })));

  return `
    <div class="traj-wrap">
      <svg class="traj-svg" viewBox="0 0 ${W} ${H}" id="traj-svg-el">
        ${gridSvg}
        ${xLabelsSvg}
        ${linesSvg}
        <line class="traj-crosshair" id="traj-crosshair-el" x1="${xFor(0)}" y1="${mTop}" x2="${xFor(0)}" y2="${mTop + plotH}" />
        ${hitSvg}
      </svg>
      <div class="traj-tooltip" id="traj-tooltip-el"></div>
      <div class="traj-legend">${legendSvg}</div>
      <button class="traj-table-toggle" id="traj-table-toggle-el" type="button">View as table</button>
      <table class="traj-table" id="traj-table-el">
        <thead><tr><th>Pattern</th>${stageLabels.map(l => `<th>${escapeHtml(l)}</th>`).join("")}</tr></thead>
        <tbody>${tableRows}</tbody>
      </table>
      <p class="note" style="margin-top:0.5rem">
        Every score is the AI's inference from the decisions in Stage by Stage below, not a measurement — hover a chart point or table cell for the specific claim it rests on.
        ${allSources.length ? renderSources(allSources) : ""}
      </p>
    </div>`;
}

function attachTrajectoryInteractivity(trajectories) {
  const svg = document.getElementById("traj-svg-el");
  if (!svg) return;
  const crosshair = document.getElementById("traj-crosshair-el");
  const tooltip = document.getElementById("traj-tooltip-el");
  const tableToggle = document.getElementById("traj-table-toggle-el");
  const table = document.getElementById("traj-table-el");
  const hits = svg.querySelectorAll(".traj-hit");

  function showTooltip(i) {
    const hit = hits[i];
    const x = parseFloat(hit.getAttribute("x")) + parseFloat(hit.getAttribute("width")) / 2;
    crosshair.setAttribute("x1", x);
    crosshair.setAttribute("x2", x);
    crosshair.style.opacity = "1";

    const rows = trajectories.map((traj, si) => {
      const pt = traj.points[i];
      const color = `var(${SERIES_VARS[si % SERIES_VARS.length]})`;
      return `<div class="traj-tooltip-block">
        <div class="traj-tooltip-row">
          <span class="traj-tooltip-key" style="background:${color}"></span>
          <span class="traj-tooltip-score">${pt.score}/10</span>
          <span class="traj-tooltip-name">${escapeHtml(traj.dimension)}</span>
        </div>
        ${renderClaim(pt.evidence, pt.evidence.claim)}
      </div>`;
    }).join("");
    tooltip.innerHTML = `<div class="traj-tooltip-date">${escapeHtml(trajectories[0].points[i].date_range)}</div>${rows}`;
    tooltip.style.opacity = "1";

    const svgRect = svg.getBoundingClientRect();
    const scaleX = svgRect.width / 640;
    const pxX = x * scaleX;
    const wrapWidth = svg.parentElement.getBoundingClientRect().width;
    tooltip.style.left = Math.max(0, Math.min(pxX + 10, wrapWidth - 280)) + "px";
    tooltip.style.top = "4px";
  }

  function hideTooltip() {
    crosshair.style.opacity = "0";
    tooltip.style.opacity = "0";
  }

  hits.forEach((hit, i) => {
    hit.addEventListener("pointerenter", () => showTooltip(i));
    hit.addEventListener("pointermove", () => showTooltip(i));
    hit.addEventListener("pointerleave", hideTooltip);
  });

  if (tableToggle && table) {
    tableToggle.addEventListener("click", () => {
      const showing = table.style.display === "table";
      table.style.display = showing ? "none" : "table";
      tableToggle.textContent = showing ? "View as table" : "Hide table";
    });
  }
}

// Renders a PersonProfile-shaped object into `container` (a DOM element).
// Used by both the public-figure search page and the private family tool.
function renderProfile(p, container) {
  const parts = [];

  parts.push(`
    <div class="meta-line">
      ${p.birth ? `Born ${escapeHtml(p.birth)}` : ""}${p.death ? ` · Died ${escapeHtml(p.death)}` : ""}
      ${p.occupations && p.occupations.length ? ` · ${p.occupations.map(escapeHtml).join(", ")}` : ""}
    </div>
    <p>${escapeHtml(p.summary)}</p>
  `);

  if (p.pattern_profile && p.pattern_profile.overall_scores && p.pattern_profile.overall_scores.length) {
    const pp = p.pattern_profile;

    parts.push(`
      <section class="card">
        <h2>Thinking Pattern</h2>
        ${pp.overall_scores.map(s => `
          <div class="meter-row">
            <div class="meter-label">
              <strong>${escapeHtml(s.dimension)}</strong>
              <span class="meter-score">${s.score}/10</span>
            </div>
            <div class="meter-track"><div class="meter-fill" style="width:${s.score * 10}%"></div></div>
            <p class="meter-justification">
              <span class="badge lvl-${s.evidence.evidence_level}">${LEVEL_LABEL[s.evidence.evidence_level] || "Unknown"}</span>
              ${escapeHtml(s.justification)}
            </p>
            ${s.evidence.uncertainty_note ? `<p class="note">${escapeHtml(s.evidence.uncertainty_note)}</p>` : ""}
            ${renderSources(s.evidence.sources)}
          </div>`).join("")}
      </section>`);

    if (pp.trajectories && pp.trajectories.length) {
      parts.push(`
        <section class="card">
          <h2>Trajectory</h2>
          ${renderTrajectoryChart(pp.trajectories)}
        </section>`);
    }

    if (pp.stages && pp.stages.length) {
      parts.push(`
        <section class="card">
          <h2>Stage by Stage</h2>
          ${pp.stages.map(stage => `
            <div class="stage-card">
              <div class="stage-header">
                <strong>${escapeHtml(stage.stage_label)}</strong>
                <span class="stage-date">${escapeHtml(stage.date_range)}</span>
              </div>
              ${(stage.decisions || []).map(d => `
                <div class="decision-block">
                  <p class="decision-title">${escapeHtml(d.decision)}</p>
                  <p class="decision-situation">${escapeHtml(d.situation)}</p>
                  <div class="style-row">
                    <span class="style-label">Decided by</span>
                    <span>${escapeHtml(d.decision_making_style)}</span>
                  </div>
                  <div class="style-row">
                    <span class="style-label">Executed by</span>
                    <span>${escapeHtml(d.execution_style)}</span>
                  </div>
                  <div class="thinking-pattern-box">
                    <div class="meter-label">
                      <strong>Thinking pattern</strong>
                      <span class="meter-score">strength ${d.pattern_strength}/10</span>
                    </div>
                    <div class="meter-track" style="margin-bottom:0.5rem">
                      <div class="meter-fill" style="width:${d.pattern_strength * 10}%"></div>
                    </div>
                    ${escapeHtml(d.thinking_pattern)}
                  </div>
                  ${renderClaim(d.evidence)}
                </div>`).join("")}
            </div>`).join("")}
        </section>`);
    }
  }

  if (p.narrative && p.narrative.length) {
    parts.push(`<section class="card"><h2>Why</h2>${p.narrative.map(c => renderClaim(c)).join("")}</section>`);
  }

  if (p.environment) {
    const env = p.environment;
    const envText = [
      env.political_climate && `Political climate: ${env.political_climate}`,
      env.economic_conditions && `Economic conditions: ${env.economic_conditions}`,
      env.technology_available && `Available technology: ${env.technology_available}`,
      env.culture_and_norms && `Culture & norms: ${env.culture_and_norms}`,
    ].filter(Boolean).join(" — ");
    parts.push(`
      <section class="card">
        <h2>Environment — ${escapeHtml(env.place)}, ${escapeHtml(env.period)}</h2>
        ${renderClaim(env.evidence, envText || env.evidence.claim)}
      </section>`);
  }

  if (p.timeline && p.timeline.length) {
    parts.push(`
      <section class="card">
        <h2>Timeline</h2>
        ${p.timeline.map(ev => `
          <div class="timeline-item">
            <div class="timeline-date">${escapeHtml(ev.date_label)}</div>
            <div style="flex:1">
              <strong>${escapeHtml(ev.title)}</strong>
              ${renderClaim(ev.evidence, ev.description)}
            </div>
          </div>`).join("")}
      </section>`);
  }

  if (p.relationships && p.relationships.length) {
    parts.push(`
      <section class="card">
        <h2>Relationships</h2>
        ${p.relationships.map(r => `
          <div class="claim">
            <p><strong>${escapeHtml(r.name)}</strong> — ${escapeHtml(r.relation_type)}</p>
            ${renderClaim(r.evidence, r.description)}
          </div>`).join("")}
      </section>`);
  }

  container.innerHTML = `<h2 style="margin-bottom:0">${escapeHtml(p.name)}</h2>` + parts.join("");

  if (p.pattern_profile && p.pattern_profile.trajectories && p.pattern_profile.trajectories.length) {
    attachTrajectoryInteractivity(p.pattern_profile.trajectories);
  }
}
