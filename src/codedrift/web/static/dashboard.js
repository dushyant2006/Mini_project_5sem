/**
 * CodeDrift Enterprise Web Platform - Operational Dashboard Shell & Gate Status
 * Strict constraints: No purple, no emojis, clean enterprise engineering aesthetics.
 */

window.CodeDriftDashboard = (function() {

  function renderShell(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    el.innerHTML = `
      <!-- Operational Control Toolbar -->
      <div class="dashboard-toolbar">
        <div class="toolbar-controls">
          <div class="form-group">
            <label class="form-label">Pre-configured Scenario</label>
            <select class="form-select" id="scenario-select">
              <option value="payment_gateway_v2">Payment Gateway v1 -> v2 (Breaking Parameter Churn)</option>
              <option value="custom">Custom Files Ingestion</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Old Module (v1)</label>
            <input type="text" class="form-input" id="input-old-file" value="data/fixtures/v1/payment_gateway.py" style="min-width: 260px;" />
          </div>

          <div class="form-group">
            <label class="form-label">New Module (v2)</label>
            <input type="text" class="form-input" id="input-new-file" value="data/fixtures/v2/payment_gateway.py" style="min-width: 260px;" />
          </div>

          <div class="form-group">
            <label class="form-label">Client Codebase Root</label>
            <input type="text" class="form-input" id="input-client-dir" value="data/fixtures/client_app" style="min-width: 220px;" />
          </div>

          <div class="form-group">
            <label class="form-label">Max Blast Threshold</label>
            <input type="number" step="0.05" class="form-input" id="input-max-score" value="0.00" style="min-width: 100px; max-width: 100px;" />
          </div>
        </div>

        <div style="margin-top: 14px;">
          <button class="btn-primary" id="btn-run-analysis">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Execute AST Invariant Analysis
          </button>
        </div>
      </div>

      <!-- Quality Gate Status Banner -->
      <div id="gate-banner-container">
        <!-- Rendered by updateGateBanner -->
      </div>

      <!-- 4 Core Metrics Ribbon -->
      <div class="metrics-ribbon" id="metrics-ribbon">
        <div class="metric-tile">
          <div class="metric-label">API Mutations</div>
          <div class="metric-number" id="metric-total-diffs">-</div>
          <div class="metric-sub">AST Signature Delta</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Breaking Contracts</div>
          <div class="metric-number" id="metric-breaking-diffs" style="color: var(--status-critical);">-</div>
          <div class="metric-sub">SemVer Invariant Violations</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Reachable Call-Sites</div>
          <div class="metric-number" id="metric-reachable-sites" style="color: var(--status-high);">-</div>
          <div class="metric-sub">Impacted Client Invocations</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Blast Radius Score R(d)</div>
          <div class="metric-number" id="metric-blast-score" style="color: var(--text-primary);">-</div>
          <div class="metric-sub" id="metric-blast-sub">Impact Severity Metric</div>
        </div>
      </div>

      <!-- Dashboard Sub-View Tabs -->
      <div class="pane-tabs">
        <button class="pane-tab-btn active-tab" data-tab="pane-diff">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
          Contract Diffs
        </button>
        <button class="pane-tab-btn" data-tab="pane-reachability">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="18" cy="5" r="3"/>
            <circle cx="6" cy="12" r="3"/>
            <circle cx="18" cy="19" r="3"/>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
          </svg>
          Call-Graph Reachability
        </button>
        <button class="pane-tab-btn" data-tab="pane-remediation">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="16 18 22 12 16 6"/>
            <polyline points="8 6 2 12 8 18"/>
          </svg>
          Codemod Patches
        </button>
        <button class="pane-tab-btn" data-tab="pane-ml">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
          ML Degradation Predictor
        </button>
        <button class="pane-tab-btn" data-tab="pane-guide">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          Migration Guide
        </button>
      </div>

      <!-- Tab Panes -->
      <div id="pane-diff" class="tab-pane active-pane">
        <!-- Rendered by diff_view.js -->
      </div>
      <div id="pane-reachability" class="tab-pane">
        <!-- Rendered by reachability_view.js -->
      </div>
      <div id="pane-remediation" class="tab-pane">
        <!-- Rendered by remediation_view.js -->
      </div>
      <div id="pane-ml" class="tab-pane">
        <!-- Rendered by app.js / ml view -->
      </div>
      <div id="pane-guide" class="tab-pane">
        <!-- Rendered by app.js / guide view -->
      </div>
    `;

    // Bind sub-tabs
    const tabs = el.querySelectorAll(".pane-tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active-tab"));
        tab.classList.add("active-tab");

        const targetPaneId = tab.getAttribute("data-tab");
        el.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active-pane"));
        const targetPane = document.getElementById(targetPaneId);
        if (targetPane) targetPane.classList.add("active-pane");
      });
    });
  }

  function updateGateBanner(policyResult, semverResult, blastRadius) {
    const container = document.getElementById("gate-banner-container");
    if (!container) return;

    if (!policyResult) {
      container.innerHTML = `
        <div class="gate-banner gate-passed">
          <div>
            <div class="gate-title">
              <span class="badge badge-safe">READY</span>
              <span>Awaiting AST Analysis Run</span>
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">
              Select parameters and click "Execute AST Invariant Analysis" to evaluate contract changes.
            </div>
          </div>
        </div>
      `;
      return;
    }

    const isPassed = policyResult.passed;
    const bannerClass = isPassed ? "gate-passed" : "gate-blocked";
    const statusBadge = isPassed
      ? '<span class="badge badge-safe">CI GATE PASSED</span>'
      : '<span class="badge badge-critical">CI GATE BLOCKED (EXIT CODE 1)</span>';

    let violationsHtml = "";
    if (policyResult.violations && policyResult.violations.length > 0) {
      violationsHtml = `
        <div style="margin-top: 10px;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #fca5a5; letter-spacing: 0.04em;">
            Enforcement Policy Violations:
          </div>
          <ul class="gate-violations-list">
            ${policyResult.violations.map(v => `<li>&bull; ${escapeHtml(v)}</li>`).join("")}
          </ul>
        </div>
      `;
    }

    let semverHtml = "";
    if (semverResult) {
      const isSemVerOk = semverResult.is_compliant !== false;
      const semBadge = isSemVerOk
        ? '<span class="badge badge-safe">SEMVER COMPLIANT</span>'
        : '<span class="badge badge-critical">SEMVER VIOLATION</span>';
      
      semverHtml = `
        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border-subtle); display: flex; align-items: center; gap: 12px; font-size: 12px;">
          ${semBadge}
          <span style="color: var(--text-secondary);">
            Evaluated Release: <strong>v${escapeHtml(semverResult.old_version || "1.0.0")} &rarr; v${escapeHtml(semverResult.new_version || "2.0.0")}</strong>
          </span>
          <span style="color: var(--text-muted);">&bull;</span>
          <span style="color: var(--text-secondary);">
            Required Bump: <strong style="color: var(--text-primary);">${escapeHtml(semverResult.required_bump || "MAJOR")}</strong>
          </span>
        </div>
      `;
    }

    container.innerHTML = `
      <div class="gate-banner ${bannerClass}">
        <div style="flex: 1;">
          <div class="gate-title">
            ${statusBadge}
            <span style="font-size: 14px; font-weight: 700;">
              ${isPassed ? "Downstream dependencies are safe from breaking contract regressions" : "Downstream consumers will experience fatal runtime exceptions"}
            </span>
          </div>
          ${violationsHtml}
          ${semverHtml}
        </div>
      </div>
    `;
  }

  function updateMetrics(diff, blastRadius) {
    const totalEl = document.getElementById("metric-total-diffs");
    const breakingEl = document.getElementById("metric-breaking-diffs");
    const reachableEl = document.getElementById("metric-reachable-sites");
    const blastEl = document.getElementById("metric-blast-score");
    const blastSub = document.getElementById("metric-blast-sub");

    if (!diff) {
      if (totalEl) totalEl.textContent = "0";
      if (breakingEl) breakingEl.textContent = "0";
      if (reachableEl) reachableEl.textContent = "0";
      if (blastEl) blastEl.textContent = "0.00";
      return;
    }

    const changes = diff.changes || [];
    const breakingChanges = changes.filter(c => c.is_breaking);
    const reachableCount = blastRadius ? (blastRadius.total_reachable_call_sites || 0) : 0;
    const score = blastRadius ? (blastRadius.blast_radius_score || 0.0) : 0.0;

    if (totalEl) totalEl.textContent = `${changes.length}`;
    if (breakingEl) {
      breakingEl.textContent = `${breakingChanges.length}`;
      breakingEl.style.color = breakingChanges.length > 0 ? "var(--status-critical)" : "var(--status-safe)";
    }
    if (reachableEl) {
      reachableEl.textContent = `${reachableCount}`;
      reachableEl.style.color = reachableCount > 0 ? "var(--status-high)" : "var(--status-safe)";
    }
    if (blastEl) {
      blastEl.textContent = score.toFixed(2);
      blastEl.style.color = score > 0 ? "var(--status-critical)" : "var(--status-safe)";
    }
    if (blastSub) {
      blastSub.textContent = score > 0.5 ? "HIGH CRITICAL PATH RISK" : (score > 0 ? "MODERATE RISK" : "ZERO DOWNSTREAM RISK");
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  return {
    renderShell,
    updateGateBanner,
    updateMetrics,
    escapeHtml
  };
})();
