/**
 * CodeDrift Enterprise Web Platform - Autonomous Codemod Remediation & Patch Viewer
 * Renders unified diffs with line-level syntax highlighting, clipboard copy, and file download.
 * Strict constraints: No purple, no emojis, clean enterprise engineering aesthetics.
 */

window.CodeDriftRemediationView = (function() {

  let currentPatches = [];

  function render(containerId, patches) {
    const el = document.getElementById(containerId);
    if (!el) return;

    currentPatches = patches || [];

    if (!patches || patches.length === 0) {
      el.innerHTML = `
        <div class="pane-card" style="padding: 40px; text-align: center;">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
            No Codemod Patches Required
          </div>
          <div style="font-size: 13px; color: var(--text-muted);">
            No reachable breaking contracts were detected in the downstream codebase, or all breaking paths have identical adapter equivalents.
          </div>
        </div>
      `;
      return;
    }

    el.innerHTML = `
      <!-- Toolbar Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
        <div>
          <span style="font-weight: 700; color: var(--text-primary); font-size: 15px;">
            Autonomous AST Codemod Patches
          </span>
          <span style="color: var(--text-muted); font-size: 13px; margin-left: 8px;">
            ${patches.length} patch${patches.length === 1 ? "" : "es"} synthesized for downstream client repositories
          </span>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn-secondary" id="btn-download-all-patches">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download Combined .patch
          </button>
        </div>
      </div>

      <!-- Patch Cards Container -->
      <div id="patch-cards-list">
        ${patches.map((patch, idx) => renderPatchCard(patch, idx)).join("")}
      </div>
    `;

    // Bind action buttons
    bindPatchActions(el);
  }

  function renderPatchCard(patch, idx) {
    const rawDiff = patch.diff || "";
    const fileName = (patch.file_path || "unknown.py").split("/").pop();

    return `
      <div class="pane-card" style="margin-bottom: 24px;" id="patch-card-${idx}">
        <div class="pane-header">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span class="badge badge-safe">AST CODEMOD</span>
            <code style="color: var(--text-primary); font-weight: 700;">${CodeDriftDashboard.escapeHtml(fileName)}</code>
            <span style="color: var(--text-muted); font-size: 12px;">(${CodeDriftDashboard.escapeHtml(patch.file_path)})</span>
          </div>

          <div style="display: flex; gap: 8px;">
            <button class="nav-btn btn-copy-patch" data-idx="${idx}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              <span>Copy Patch</span>
            </button>
            <button class="nav-btn btn-download-single-patch" data-idx="${idx}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Download .patch
            </button>
          </div>
        </div>

        <div style="padding: 16px;">
          <!-- Remediation Justification -->
          <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-secondary); background-color: var(--bg-surface-elevated); padding: 10px 14px; border-radius: 4px; border: 1px solid var(--border-subtle);">
            <strong style="color: var(--text-primary);">Target Symbol:</strong> <code>${CodeDriftDashboard.escapeHtml(patch.target_symbol || "")}</code>
            <div style="margin-top: 4px; color: var(--text-muted);">
              <strong>Automated Fix:</strong> ${CodeDriftDashboard.escapeHtml(patch.reason || "Automatic AST caller argument rewrite")}
            </div>
          </div>

          <!-- Highlighted Unified Diff Block -->
          <div class="diff-view-block">
            ${highlightUnifiedDiff(rawDiff)}
          </div>
        </div>
      </div>
    `;
  }

  function highlightUnifiedDiff(diffText) {
    if (!diffText) {
      return '<div style="color: var(--text-muted);">No unified diff generated.</div>';
    }

    const lines = diffText.split("\n");
    return lines.map(line => {
      const escaped = CodeDriftDashboard.escapeHtml(line);
      if (line.startsWith("---") || line.startsWith("+++")) {
        return `<span style="color: #94a3b8; font-weight: 700;">${escaped}</span>`;
      } else if (line.startsWith("@@")) {
        return `<span style="color: #38bdf8; font-weight: 600; display: block; margin: 4px 0;">${escaped}</span>`;
      } else if (line.startsWith("-")) {
        return `<span class="diff-line-del">${escaped}</span>`;
      } else if (line.startsWith("+")) {
        return `<span class="diff-line-add">${escaped}</span>`;
      } else {
        return `<span class="diff-line-ctx">${escaped}</span>`;
      }
    }).join("\n");
  }

  function bindPatchActions(el) {
    // Copy patch button
    el.querySelectorAll(".btn-copy-patch").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-idx"), 10);
        const patch = currentPatches[idx];
        if (!patch) return;

        navigator.clipboard.writeText(patch.diff || "").then(() => {
          const span = btn.querySelector("span");
          const originalText = span ? span.textContent : "Copy Patch";
          if (span) span.textContent = "Copied to Clipboard";
          btn.style.borderColor = "var(--status-safe)";
          btn.style.color = "var(--status-safe)";
          setTimeout(() => {
            if (span) span.textContent = originalText;
            btn.style.borderColor = "";
            btn.style.color = "";
          }, 2000);
        });
      });
    });

    // Single download button
    el.querySelectorAll(".btn-download-single-patch").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-idx"), 10);
        const patch = currentPatches[idx];
        if (!patch) return;

        const fileName = (patch.file_path || "patch").split("/").pop() + ".patch";
        triggerDownload(fileName, patch.diff || "");
      });
    });

    // Combined download button
    const btnAll = el.querySelector("#btn-download-all-patches");
    if (btnAll) {
      btnAll.addEventListener("click", () => {
        if (currentPatches.length === 0) return;
        const combined = currentPatches.map(p => `# File: ${p.file_path}\n# Target: ${p.target_symbol}\n${p.diff}\n`).join("\n");
        triggerDownload("codedrift-remediation.patch", combined);
      });
    }
  }

  function triggerDownload(filename, text) {
    const element = document.createElement("a");
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(text));
    element.setAttribute("download", filename);
    element.style.display = "none";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  }

  return {
    render
  };
})();
