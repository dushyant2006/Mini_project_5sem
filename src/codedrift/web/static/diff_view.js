/**
 * CodeDrift Enterprise Web Platform - Semantic Contract Diff Explorer
 * Displays AST signature mutations, parameter alterations, and SemVer breaking flags.
 * Strict constraints: No purple, no emojis, clean enterprise engineering aesthetics.
 */

window.CodeDriftDiffView = (function() {

  let currentDiff = null;
  let activeFilter = "ALL";

  function render(containerId, diffData) {
    const el = document.getElementById(containerId);
    if (!el) return;

    currentDiff = diffData;
    activeFilter = "ALL";

    if (!diffData || !diffData.changes || diffData.changes.length === 0) {
      el.innerHTML = `
        <div class="pane-card" style="padding: 40px; text-align: center;">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
            No Contract Changes Detected
          </div>
          <div style="font-size: 13px; color: var(--text-muted);">
            The compared Python modules have identical public AST signatures.
          </div>
        </div>
      `;
      return;
    }

    const changes = diffData.changes;
    const breakingCount = changes.filter(c => c.is_breaking).length;
    const criticalCount = changes.filter(c => c.severity === "CRITICAL").length;
    const highCount = changes.filter(c => c.severity === "HIGH").length;
    const mediumCount = changes.filter(c => c.severity === "MEDIUM").length;

    el.innerHTML = `
      <!-- Filter Bar -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; gap: 8px;">
          <button class="nav-btn active filter-btn" data-filter="ALL">
            All Mutations (${changes.length})
          </button>
          <button class="nav-btn filter-btn" data-filter="BREAKING">
            Breaking Only (${breakingCount})
          </button>
          <button class="nav-btn filter-btn" data-filter="CRITICAL">
            Critical (${criticalCount})
          </button>
          <button class="nav-btn filter-btn" data-filter="HIGH">
            High (${highCount})
          </button>
          <button class="nav-btn filter-btn" data-filter="MEDIUM">
            Medium (${mediumCount})
          </button>
        </div>
        <div style="font-size: 12px; color: var(--text-muted);">
          Module: <code style="color: var(--text-primary);">${CodeDriftDashboard.escapeHtml(diffData.old_module || "v1")} &rarr; ${CodeDriftDashboard.escapeHtml(diffData.new_module || "v2")}</code>
        </div>
      </div>

      <!-- Diff Table -->
      <div class="comparison-table-wrapper">
        <table class="data-table" id="diff-data-table">
          <thead>
            <tr>
              <th style="width: 100px;">Severity</th>
              <th style="width: 100px;">Classification</th>
              <th style="width: 220px;">Target Symbol</th>
              <th style="width: 180px;">Category</th>
              <th>Impact Description & Contract Delta</th>
            </tr>
          </thead>
          <tbody id="diff-table-body">
            <!-- Populated by renderRows -->
          </tbody>
        </table>
      </div>
    `;

    renderRows();

    // Bind filters
    const filterBtns = el.querySelectorAll(".filter-btn");
    filterBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        filterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeFilter = btn.getAttribute("data-filter");
        renderRows();
      });
    });
  }

  function renderRows() {
    const tbody = document.getElementById("diff-table-body");
    if (!tbody || !currentDiff) return;

    let filtered = currentDiff.changes || [];
    if (activeFilter === "BREAKING") {
      filtered = filtered.filter(c => c.is_breaking);
    } else if (activeFilter === "CRITICAL") {
      filtered = filtered.filter(c => c.severity === "CRITICAL");
    } else if (activeFilter === "HIGH") {
      filtered = filtered.filter(c => c.severity === "HIGH");
    } else if (activeFilter === "MEDIUM") {
      filtered = filtered.filter(c => c.severity === "MEDIUM");
    }

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; padding: 24px; color: var(--text-muted);">
            No contract mutations match the selected filter criteria.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered.map(change => {
      const sevBadge = getSeverityBadge(change.severity);
      const isBreakingBadge = change.is_breaking
        ? '<span class="badge badge-critical">BREAKING</span>'
        : '<span class="badge badge-safe">COMPATIBLE</span>';

      let detailsHtml = "";
      if (change.old_val || change.new_val) {
        detailsHtml = `
          <div style="margin-top: 8px; font-size: 11px; font-family: var(--font-mono); background: var(--bg-canvas); padding: 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">
            ${change.old_val ? `<div style="color: #fda4af;">- ${CodeDriftDashboard.escapeHtml(change.old_val)}</div>` : ""}
            ${change.new_val ? `<div style="color: #6ee7b7;">+ ${CodeDriftDashboard.escapeHtml(change.new_val)}</div>` : ""}
          </div>
        `;
      }

      return `
        <tr>
          <td>${sevBadge}</td>
          <td>${isBreakingBadge}</td>
          <td>
            <code style="font-weight: 600; color: #38bdf8;">${CodeDriftDashboard.escapeHtml(change.symbol_name || "-")}</code>
          </td>
          <td>
            <span class="badge badge-neutral">${CodeDriftDashboard.escapeHtml(change.category || "-")}</span>
          </td>
          <td>
            <div style="font-size: 13px; color: var(--text-primary); font-weight: 500;">
              ${CodeDriftDashboard.escapeHtml(change.description || "")}
            </div>
            ${detailsHtml}
          </td>
        </tr>
      `;
    }).join("");
  }

  function getSeverityBadge(severity) {
    switch (severity) {
      case "CRITICAL":
        return '<span class="badge badge-critical">CRITICAL</span>';
      case "HIGH":
        return '<span class="badge badge-high">HIGH</span>';
      case "MEDIUM":
        return '<span class="badge badge-medium">MEDIUM</span>';
      case "LOW":
        return '<span class="badge badge-safe">LOW</span>';
      default:
        return `<span class="badge badge-neutral">${CodeDriftDashboard.escapeHtml(severity)}</span>`;
    }
  }

  return {
    render
  };
})();
