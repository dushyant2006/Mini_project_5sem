/**
 * CodeDrift Enterprise Web Platform - Main Application Controller
 * Coordinates views, API requests, ML panel, Migration guide, and top navigation.
 */

(function () {
  let latestAnalysisData = null;

  document.addEventListener("DOMContentLoaded", function () {
    initNavigation();
    renderInitialViews();
    bindDashboardControls();
    loadDefaultScenarioAndRun();
  });

  function initNavigation() {
    const navButtons = document.querySelectorAll(".nav-btn[data-target]");
    const sectionViews = document.querySelectorAll(".section-view");

    navButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        navButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        sectionViews.forEach((view) => {
          if (view.id === targetId) {
            view.classList.add("active-view");
          } else {
            view.classList.remove("active-view");
          }
        });
      });
    });

    const brandLink = document.getElementById("brand-link");
    if (brandLink) {
      brandLink.addEventListener("click", (e) => {
        e.preventDefault();
        const landingBtn = document.getElementById("nav-btn-landing");
        if (landingBtn) landingBtn.click();
      });
    }
  }

  function renderInitialViews() {
    if (window.CodeDriftLanding) {
      window.CodeDriftLanding.renderLanding("landing-container");
      window.CodeDriftLanding.renderArchitecture("architecture-container");
    }

    if (window.CodeDriftDashboard) {
      window.CodeDriftDashboard.renderShell("dashboard-container");
    }
  }

  function bindDashboardControls() {
    const scenarioSelect = document.getElementById("scenario-select");
    const inputOld = document.getElementById("input-old-file");
    const inputNew = document.getElementById("input-new-file");
    const inputClient = document.getElementById("input-client-dir");
    const btnRun = document.getElementById("btn-run-analysis");
    const descText = document.getElementById("scenario-desc-text");

    const scenarioDescriptions = {
      payment_gateway_v2: "Scenario 1: Parameter Removed. The payment library removed 'currency'. Our checkout code crashes because it still passes currency='USD'.",
      auth_service_v2: "Scenario 2: Required Parameter Added. The authentication library now requires 'mfa_code'. Our login page crashes because it does not pass MFA.",
      notification_service_v2: "Scenario 3: Function Deleted. The email library deleted send_email(). Our alerting module crashes with an AttributeError.",
      storage_lib_v1_1: "Scenario 4: Safe Minor Update. Cloud storage added optional 'encryption' parameter with a safe default. Our code runs normally. Quality Gate passes!",
    };

    if (scenarioSelect) {
      scenarioSelect.addEventListener("change", () => {
        const val = scenarioSelect.value;
        if (val === "payment_gateway_v2") {
          if (inputOld) inputOld.value = "data/fixtures/v1/payment_gateway.py";
          if (inputNew) inputNew.value = "data/fixtures/v2/payment_gateway.py";
          if (inputClient) inputClient.value = "data/fixtures/client_app";
        } else if (val === "auth_service_v2") {
          if (inputOld) inputOld.value = "data/fixtures/v1/auth_service.py";
          if (inputNew) inputNew.value = "data/fixtures/v2/auth_service.py";
          if (inputClient) inputClient.value = "data/fixtures/client_app";
        } else if (val === "notification_service_v2") {
          if (inputOld) inputOld.value = "data/fixtures/v1/notification_service.py";
          if (inputNew) inputNew.value = "data/fixtures/v2/notification_service.py";
          if (inputClient) inputClient.value = "data/fixtures/client_app";
        } else if (val === "storage_lib_v1_1") {
          if (inputOld) inputOld.value = "data/fixtures/v1/storage_lib.py";
          if (inputNew) inputNew.value = "data/fixtures/v2/storage_lib.py";
          if (inputClient) inputClient.value = "data/fixtures/client_app";
        }

        if (descText && scenarioDescriptions[val]) {
          descText.textContent = scenarioDescriptions[val];
        }

        // Auto-run on scenario change for instant presentation response
        executeAnalysis();
      });
    }

    if (btnRun) {
      btnRun.addEventListener("click", () => {
        executeAnalysis();
      });
    }
  }

  function loadDefaultScenarioAndRun() {
    // Initial automated load
    executeAnalysis();
  }

  async function executeAnalysis() {
    const btnRun = document.getElementById("btn-run-analysis");
    const inputOld = document.getElementById("input-old-file");
    const inputNew = document.getElementById("input-new-file");
    const inputClient = document.getElementById("input-client-dir");
    const inputMax = document.getElementById("input-max-score");

    const payload = {
      old_file: inputOld ? inputOld.value.trim() : "data/fixtures/v1/payment_gateway.py",
      new_file: inputNew ? inputNew.value.trim() : "data/fixtures/v2/payment_gateway.py",
      client_dir: inputClient ? inputClient.value.trim() : "data/fixtures/client_app",
      max_score: inputMax ? parseFloat(inputMax.value) || 0.0 : 0.0,
    };

    if (btnRun) {
      btnRun.disabled = true;
      btnRun.textContent = "Analyzing AST...";
    }

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed with HTTP status ${response.status}`);
      }

      const data = await response.json();
      latestAnalysisData = data;
      renderAnalysisResults(data);
    } catch (err) {
      console.error("CodeDrift Analysis Error:", err);
      if (window.CodeDriftDashboard) {
        window.CodeDriftDashboard.updateGateBanner({
          passed: false,
          violations: [`API Error: ${err.message}`],
        });
      }
    } finally {
      if (btnRun) {
        btnRun.disabled = false;
        btnRun.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Execute AST Invariant Analysis
        `;
      }
    }
  }

  function renderAnalysisResults(data) {
    if (!data) return;

    // 1. Quality Gate & Metrics
    if (window.CodeDriftDashboard) {
      window.CodeDriftDashboard.updateGateBanner(data.policy, data.semver, data.blast_radius);
      window.CodeDriftDashboard.updateMetrics(data.diff, data.blast_radius);
    }

    // 2. Contract Diffs View
    if (window.CodeDriftDiffView) {
      window.CodeDriftDiffView.render("pane-diff", data.diff);
    }

    // 3. Reachability View
    if (window.CodeDriftReachabilityView) {
      window.CodeDriftReachabilityView.render("pane-reachability", data.blast_radius);
    }

    // 4. Remediation View
    if (window.CodeDriftRemediationView) {
      window.CodeDriftRemediationView.render("pane-remediation", data.patches, data.remediation_actions);
    }

    // 5. Database History View
    renderDatabaseHistory(data.database_stats);

    // 6. ML Degradation Predictor View
    renderMLPredictor(data.ml_prediction);

    // 7. Migration Guide View
    renderMigrationGuide(data.migration_guide);
  }

  async function renderDatabaseHistory(stats) {
    const pane = document.getElementById("pane-history");
    if (!pane) return;

    pane.innerHTML = `
      <div class="pane-card" style="margin-bottom: 24px;">
        <div class="pane-header">
          <span>Embedded SQLite Audit Repository</span>
          <span class="badge badge-safe">SQLite Active</span>
        </div>
        <div style="padding: 20px;">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Total Audits Logged</div>
              <div class="metric-number" style="color: var(--text-primary); font-size: 24px;" id="db-total-runs">${stats ? stats.total_runs : '-'}</div>
              <div class="metric-sub">Stored in codedrift_audit.db</div>
            </div>

            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Blocked Upgrades</div>
              <div class="metric-number" style="color: var(--status-critical); font-size: 24px;" id="db-blocked-runs">${stats ? stats.blocked_runs : '-'}</div>
              <div class="metric-sub">Production crashes prevented</div>
            </div>

            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Passed Upgrades</div>
              <div class="metric-number" style="color: var(--status-safe); font-size: 24px;" id="db-passed-runs">${stats ? stats.passed_runs : '-'}</div>
              <div class="metric-sub">Safe dependency updates</div>
            </div>

            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Remediation Tasks</div>
              <div class="metric-number" style="color: #38bdf8; font-size: 24px;" id="db-tasks-count">${stats ? stats.total_remediation_tasks : '-'}</div>
              <div class="metric-sub">Auto-synthesized repair tasks</div>
            </div>
          </div>

          <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">Recent Audit History Records</h3>
          <div id="db-history-table-container">Loading audit logs...</div>
        </div>
      </div>
    `;

    try {
      const res = await fetch("/api/history");
      if (res.ok) {
        const histData = await res.json();
        const runs = histData.history || [];
        const container = document.getElementById("db-history-table-container");
        if (container) {
          if (runs.length === 0) {
            container.innerHTML = `<div style="color: var(--text-muted); font-size: 13px;">No runs recorded yet.</div>`;
          } else {
            container.innerHTML = `
              <div class="comparison-table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Timestamp</th>
                      <th>Scenario</th>
                      <th>Gate Decision</th>
                      <th>Blast Score</th>
                      <th>Broken Lines</th>
                      <th>Risk Tier</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${runs.map(r => `
                      <tr>
                        <td><code>#${r.id}</code></td>
                        <td style="color: var(--text-muted); font-size: 12px;">${r.timestamp}</td>
                        <td style="font-weight: 600; color: var(--text-primary);">${CodeDriftDashboard.escapeHtml(r.scenario_name)}</td>
                        <td>
                          <span class="badge ${r.decision === 'PASSED' ? 'badge-safe' : 'badge-critical'}">
                            ${r.decision}
                          </span>
                        </td>
                        <td><strong>${r.blast_radius_score.toFixed(1)}</strong></td>
                        <td>${r.reachable_sites}</td>
                        <td><span class="badge badge-neutral">${CodeDriftDashboard.escapeHtml(r.risk_tier)}</span></td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            `;
          }
        }
      }
    } catch (e) {
      console.warn("Could not load history:", e);
    }
  }

  function renderMLPredictor(mlData) {
    const pane = document.getElementById("pane-ml");
    if (!pane) return;

    if (!mlData) {
      pane.innerHTML = `
        <div class="pane-card" style="padding: 32px; text-align: center; color: var(--text-muted);">
          No Machine Learning degradation prediction available.
        </div>
      `;
      return;
    }

    const probPct = Math.round((mlData.degradation_probability || 0) * 100);
    const confPct = Math.round((mlData.confidence_score || 0) * 100);
    const tier = mlData.risk_tier || "UNKNOWN";
    const hours = (mlData.estimated_remediation_hours || 0).toFixed(1);

    let badgeClass = "badge-safe";
    if (tier === "SEVERE_REGRESSION") badgeClass = "badge-critical";
    else if (tier === "MODERATE_RISK") badgeClass = "badge-high";
    else if (tier === "LOW_RISK") badgeClass = "badge-medium";

    const drivers = mlData.key_risk_drivers || [];

    pane.innerHTML = `
      <div class="pane-card" style="margin-bottom: 24px;">
        <div class="pane-header">
          <span>ML Regression Model Assessment</span>
          <span class="badge ${badgeClass}">${CodeDriftDashboard.escapeHtml(tier)}</span>
        </div>
        <div style="padding: 24px;">
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Degradation Probability</div>
              <div class="metric-number" style="color: ${probPct > 50 ? 'var(--status-critical)' : 'var(--status-safe)'};">${probPct}%</div>
              <div class="metric-sub">Calculated via feature vector dot-product</div>
            </div>

            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Estimated Developer Effort</div>
              <div class="metric-number" style="color: #38bdf8;">${hours} hrs</div>
              <div class="metric-sub">Migration & refactoring workload</div>
            </div>

            <div style="background-color: var(--bg-surface-elevated); padding: 16px; border-radius: 6px; border: 1px solid var(--border-subtle);">
              <div class="metric-label">Model Confidence</div>
              <div class="metric-number" style="color: var(--text-primary);">${confPct}%</div>
              <div class="metric-sub">Calibrated feature coverage score</div>
            </div>
          </div>

          <h3 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">Key Empirical Risk Drivers</h3>
          ${
            drivers.length > 0
              ? `<ul style="list-style-type: none; padding-left: 0;">
                  ${drivers.map((d) => `<li style="padding: 6px 0; color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
                    <span style="color: var(--accent-blue); font-weight: 700;">&bull;</span>
                    ${CodeDriftDashboard.escapeHtml(d)}
                  </li>`).join("")}
                </ul>`
              : `<p style="color: var(--text-muted); font-size: 13px;">No significant risk anomalies detected in upstream module.</p>`
          }
        </div>
      </div>
    `;
  }

  function renderMigrationGuide(guideText) {
    const pane = document.getElementById("pane-guide");
    if (!pane) return;

    if (!guideText) {
      pane.innerHTML = `
        <div class="pane-card" style="padding: 32px; text-align: center; color: var(--text-muted);">
          No migration guide generated for this module delta.
        </div>
      `;
      return;
    }

    pane.innerHTML = `
      <div class="pane-card">
        <div class="pane-header">
          <span>Synthesized Markdown Migration Manual</span>
          <button class="nav-btn" id="btn-copy-guide" style="font-size: 11px; padding: 4px 8px;">
            Copy Markdown Guide
          </button>
        </div>
        <div style="padding: 20px;">
          <div class="terminal-box" style="white-space: pre-wrap; word-break: break-word; font-size: 13px;">${CodeDriftDashboard.escapeHtml(guideText)}</div>
        </div>
      </div>
    `;

    const btnCopy = document.getElementById("btn-copy-guide");
    if (btnCopy) {
      btnCopy.addEventListener("click", () => {
        navigator.clipboard.writeText(guideText).then(() => {
          btnCopy.textContent = "Copied!";
          setTimeout(() => {
            btnCopy.textContent = "Copy Markdown Guide";
          }, 2000);
        });
      });
    }
  }
})();
