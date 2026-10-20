/**
 * CodeDrift Enterprise Web Platform - Call-Graph Reachability Explorer
 * Connects upstream breaking changes directly to downstream caller lines of code.
 * Strict constraints: No purple, no emojis, clean enterprise engineering aesthetics.
 */

window.CodeDriftReachabilityView = (function() {

  let currentData = null;
  let selectedFile = null;

  function render(containerId, blastData) {
    const el = document.getElementById(containerId);
    if (!el) return;

    currentData = blastData;
    selectedFile = null;

    if (!blastData || !blastData.items || blastData.items.length === 0) {
      el.innerHTML = `
        <div class="pane-card" style="padding: 40px; text-align: center;">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
            No Downstream Client Scanned
          </div>
          <div style="font-size: 13px; color: var(--text-muted);">
            Provide a valid client codebase directory path in the toolbar to run static call-graph reachability analysis.
          </div>
        </div>
      `;
      return;
    }

    const reachableItems = blastData.items.filter(item => item.is_reachable);
    const unreachableItems = blastData.items.filter(item => !item.is_reachable);

    const affectedFiles = blastData.affected_files || [];
    if (affectedFiles.length > 0) {
      selectedFile = affectedFiles[0];
    }

    el.innerHTML = `
      <!-- Reachability Summary Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
        <div>
          <span style="font-weight: 700; color: var(--text-primary); font-size: 15px;">Static Call-Graph Reachability Tree</span>
          <span style="color: var(--text-muted); font-size: 13px; margin-left: 8px;">
            Client Root: <code>${CodeDriftDashboard.escapeHtml(blastData.client_dir || "client_app")}</code>
          </span>
        </div>
        <div style="display: flex; gap: 8px;">
          <span class="badge badge-critical">${reachableItems.length} Reachable Breaking Symbol(s)</span>
          <span class="badge badge-safe">${unreachableItems.length} Unreachable (False-Alarms Filtered)</span>
        </div>
      </div>

      <!-- Dual Pane Master-Detail -->
      <div class="dual-pane">
        <!-- Left Column: Impacted Consumer Files -->
        <div class="pane-card">
          <div class="pane-header">
            <span>Impacted Files (${affectedFiles.length})</span>
            <span class="badge badge-neutral">Client Repos</span>
          </div>
          <ul class="item-list" id="reachability-file-list">
            <!-- Populated by renderFileList -->
          </ul>
        </div>

        <!-- Right Column: Line-level Call Sites -->
        <div class="pane-card">
          <div class="pane-header" id="callsite-header">
            <span>Active Invocation Call-Sites</span>
            <span class="badge badge-critical" id="callsite-count-badge">0 Sites</span>
          </div>
          <div style="padding: 16px; max-height: 520px; overflow-y: auto;" id="callsite-detail-container">
            <!-- Populated by renderCallSites -->
          </div>
        </div>
      </div>

      <!-- Dead Code & Unreachable Invariants Section (Highlights CodeDrift Precision) -->
      ${renderUnreachableSection(unreachableItems)}
    `;

    renderFileList();
    renderCallSites();
  }

  function renderFileList() {
    const listEl = document.getElementById("reachability-file-list");
    if (!listEl || !currentData) return;

    const files = currentData.affected_files || [];
    if (files.length === 0) {
      listEl.innerHTML = `
        <li style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">
          No client files invoke any breaking contracts.
        </li>
      `;
      return;
    }

    listEl.innerHTML = files.map(file => {
      const isSelected = file === selectedFile;
      // Count total sites in this file
      let siteCount = 0;
      currentData.items.forEach(item => {
        (item.call_sites || []).forEach(cs => {
          if (cs.file_path === file) siteCount++;
        });
      });

      return `
        <li class="item-row ${isSelected ? "selected" : ""}" data-file="${CodeDriftDashboard.escapeHtml(file)}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <code style="font-weight: 700; color: var(--text-primary); font-size: 13px;">
              ${CodeDriftDashboard.escapeHtml(file.split("/").pop() || file)}
            </code>
            <span class="badge badge-critical">${siteCount} call-site${siteCount === 1 ? "" : "s"}</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${CodeDriftDashboard.escapeHtml(file)}
          </div>
        </li>
      `;
    }).join("");

    // Bind file row selection
    listEl.querySelectorAll(".item-row").forEach(row => {
      row.addEventListener("click", () => {
        selectedFile = row.getAttribute("data-file");
        renderFileList();
        renderCallSites();
      });
    });
  }

  function renderCallSites() {
    const detailEl = document.getElementById("callsite-detail-container");
    const headerBadge = document.getElementById("callsite-count-badge");
    if (!detailEl || !currentData) return;

    if (!selectedFile) {
      detailEl.innerHTML = `
        <div style="color: var(--text-muted); text-align: center; padding: 30px;">
          Select a consumer file on the left to inspect reachable call-sites.
        </div>
      `;
      if (headerBadge) headerBadge.textContent = "0 Sites";
      return;
    }

    // Gather all call sites in selectedFile
    const matchingSites = [];
    currentData.items.forEach(item => {
      (item.call_sites || []).forEach(cs => {
        if (cs.file_path === selectedFile) {
          matchingSites.push({
            site: cs,
            change: item.change,
            impact_score: item.impact_score
          });
        }
      });
    });

    if (headerBadge) {
      headerBadge.textContent = `${matchingSites.length} Site${matchingSites.length === 1 ? "" : "s"}`;
    }

    if (matchingSites.length === 0) {
      detailEl.innerHTML = `
        <div style="color: var(--text-muted); text-align: center; padding: 30px;">
          No active call-sites in this file.
        </div>
      `;
      return;
    }

    detailEl.innerHTML = matchingSites.map(m => {
      const cs = m.site;
      const change = m.change;

      return `
        <div style="background-color: var(--bg-surface-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 14px; margin-bottom: 16px;">
          <!-- Card Header -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <div>
              <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                <span class="badge badge-critical">BREAKING CALL</span>
                <span>Caller Function: <code>${CodeDriftDashboard.escapeHtml(cs.caller_function || "global scope")}</code></span>
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                Invokes Target: <strong style="color: #38bdf8;">${CodeDriftDashboard.escapeHtml(cs.callee_name)}</strong>
                &bull; Line <strong>${cs.line}</strong>, Col ${cs.column}
              </div>
            </div>
            <span class="badge badge-neutral">Impact Weight: ${m.impact_score || "1.0"}</span>
          </div>

          <!-- Contract Reason -->
          <div style="font-size: 12px; color: #fca5a5; background-color: var(--status-critical-bg); padding: 6px 10px; border-radius: 4px; border: 1px solid rgba(225, 29, 72, 0.2); margin-bottom: 10px;">
            <strong>Contract Violation:</strong> ${CodeDriftDashboard.escapeHtml(change.description || "Signature mismatch")}
          </div>

          <!-- Code Snippet Viewer -->
          <div class="diff-view-block" style="padding: 10px 14px; font-size: 12px;">
            <div style="color: var(--text-muted); font-size: 11px; margin-bottom: 4px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px;">
              ${CodeDriftDashboard.escapeHtml(cs.file_path)} : Line ${cs.line}
            </div>
            <div style="color: #fda4af;">
              <span style="color: var(--text-muted); user-select: none; margin-right: 8px;">${cs.line} |</span>${CodeDriftDashboard.escapeHtml(cs.code_snippet || "")}
            </div>
          </div>

          <!-- Arguments Breakdown -->
          ${cs.arguments_passed && cs.arguments_passed.length > 0 ? `
            <div style="margin-top: 10px; font-size: 11px; color: var(--text-muted);">
              Passed Arguments:
              ${cs.arguments_passed.map(arg => `<code style="margin-left: 4px; color: #94a3b8;">${CodeDriftDashboard.escapeHtml(arg)}</code>`).join("")}
            </div>
          ` : ""}
        </div>
      `;
    }).join("");
  }

  function renderUnreachableSection(unreachableItems) {
    if (!unreachableItems || unreachableItems.length === 0) return "";

    return `
      <div class="pane-card" style="margin-top: 24px;">
        <div class="pane-header">
          <span>False-Alarm Suppression: Unreachable Upstream Mutations (${unreachableItems.length})</span>
          <span class="badge badge-safe">Zero Impact</span>
        </div>
        <div style="padding: 16px;">
          <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
            The following upstream breaking mutations were detected by the AST parser, but <strong>no downstream call-sites</strong> invoke them in this repository.
            Unlike naive lockfile bots, CodeDrift does not block pull requests for dead-code or uncalled symbols.
          </p>
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 100px;">Status</th>
                <th style="width: 240px;">Symbol Name</th>
                <th>AST Mutation</th>
                <th>Downstream Invocations</th>
              </tr>
            </thead>
            <tbody>
              ${unreachableItems.map(item => `
                <tr>
                  <td><span class="badge badge-safe">IGNORED</span></td>
                  <td><code>${CodeDriftDashboard.escapeHtml(item.change.symbol_name || "-")}</code></td>
                  <td style="color: var(--text-secondary);">${CodeDriftDashboard.escapeHtml(item.change.description || "")}</td>
                  <td><strong style="color: var(--status-safe);">0 call sites (Unused)</strong></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  return {
    render
  };
})();
