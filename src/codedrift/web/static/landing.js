/**
 * CodeDrift Enterprise Web Platform - Technical Landing Page
 * Strict constraints: No purple, no emojis, clean enterprise engineering aesthetics.
 */

window.CodeDriftLanding = (function() {
  function renderLanding(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    el.innerHTML = `
      <!-- Hero Section -->
      <section class="hero-container">
        <div class="hero-tagline">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          Deterministic AST Contract Analysis & CI/CD Gate
        </div>
        <h1 class="hero-title">
          Autonomous API Breaking-Change & Dependency Degradation Guard
        </h1>
        <p class="hero-desc">
          When software packages update, they often remove parameters, delete functions, or change return types.
          Standard package tools cannot catch this, causing production apps to crash.
          CodeDrift automatically checks your code against the new package, tells you exactly what will break,
          and generates one-click fixes.
        </p>
        <div class="hero-actions">
          <button class="btn-primary" id="landing-cta-dashboard">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Open Interactive Dashboard
          </button>
          <button class="btn-secondary" id="landing-cta-spec">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            How Does It Work?
          </button>
        </div>
      </section>

      <!-- Key Engineering Metrics Banner -->
      <div class="metrics-ribbon" style="margin-bottom: 48px;">
        <div class="metric-tile">
          <div class="metric-label">Parser Strategy</div>
          <div class="metric-number" style="font-size: 18px; color: #38bdf8;">Full Python AST</div>
          <div class="metric-sub">Zero-execution, sandboxed static analysis</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Reachability Analysis</div>
          <div class="metric-number" style="font-size: 18px; color: #34d399;">Static Call-Graph</div>
          <div class="metric-sub">Eliminates false alarms from unused symbols</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Remediation Engine</div>
          <div class="metric-number" style="font-size: 18px; color: #fbbf24;">Autonomous Codemod</div>
          <div class="metric-sub">Generates backward-compatible unified diffs</div>
        </div>
        <div class="metric-tile">
          <div class="metric-label">Policy Gate Enforcement</div>
          <div class="metric-number" style="font-size: 18px; color: #f87171;">Exit Code Blocking</div>
          <div class="metric-sub">CI/CD pull-request fail-safe pipeline gate</div>
        </div>
      </div>

      <!-- Problem Statement & Comparison Table -->
      <section class="spec-section">
        <h2 class="spec-heading">The Semantic Blind Spot in Modern Package Ecosystems</h2>
        <p class="spec-subheading">
          Package managers like pip and lockfile checkers only guarantee version resolution—not semantic API integrity.
          Here is how CodeDrift bridges the gap between lockfiles and runtime crashes.
        </p>

        <div class="comparison-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 25%;">Capability / Vector</th>
                <th style="width: 25%;">Lockfiles (pip / poetry)</th>
                <th style="width: 25%;">Unit / Integration Tests</th>
                <th style="width: 25%;">CodeDrift Autonomous Guard</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Parameter Removal Detection</strong></td>
                <td><span class="badge badge-critical">Blind</span></td>
                <td><span class="badge badge-medium">Partial (Only if test hits path)</span></td>
                <td><span class="badge badge-safe">100% AST Invariant Analysis</span></td>
              </tr>
              <tr>
                <td><strong>Reachability Verification</strong></td>
                <td><span class="badge badge-critical">None</span></td>
                <td><span class="badge badge-critical">None (Runtime only)</span></td>
                <td><span class="badge badge-safe">Static Call-Graph Tracing</span></td>
              </tr>
              <tr>
                <td><strong>SemVer Honesty Audit</strong></td>
                <td><span class="badge badge-critical">Blindly trusts tags</span></td>
                <td><span class="badge badge-critical">None</span></td>
                <td><span class="badge badge-safe">Enforces SemVer 2.0 Invariants</span></td>
              </tr>
              <tr>
                <td><strong>Quantitative Blast Radius</strong></td>
                <td><span class="badge badge-critical">None</span></td>
                <td><span class="badge badge-critical">None</span></td>
                <td><span class="badge badge-safe">Mathematical Impact Scoring</span></td>
              </tr>
              <tr>
                <td><strong>Autonomous Codemod Patches</strong></td>
                <td><span class="badge badge-critical">Manual human triage</span></td>
                <td><span class="badge badge-critical">Manual human rewrite</span></td>
                <td><span class="badge badge-safe">Automated AST Patch Synthesis</span></td>
              </tr>
              <tr>
                <td><strong>CI/CD Pull-Request Blocker</strong></td>
                <td><span class="badge badge-medium">Only on resolve failure</span></td>
                <td><span class="badge badge-medium">Slow (minutes/hours)</span></td>
                <td><span class="badge badge-safe">Instant (sub-second AST diff)</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Architecture Pipeline Overview -->
      <section class="spec-section">
        <h2 class="spec-heading">System Pipeline & Analysis Lifecycle</h2>
        <p class="spec-subheading">
          Deterministic 5-stage pipeline executed in isolated sandbox environments with zero arbitrary code execution.
        </p>

        <div class="terminal-box" style="margin-bottom: 24px;">
[01] UPSTREAM V1 & V2 SOURCES
        |
        +---> Python AST Parser (NodeVisitor) ===> Signature Models (Function, Class, Param)
        |
[02] SEMANTIC DIFF ENGINE
        |
        +---> Set-Theoretic Diff & Type Invariant Checks ===> ContractDiff (CRITICAL, HIGH, MEDIUM)
        +---> SemVer Auditor (Flags Breaking changes in Minor/Patch releases)
        |
[03] CALL-GRAPH REACHABILITY ANALYZER
        |
        +---> Client Codebase Ingestion ===> Static Call-Graph Builder
        +---> Reachability Filtering ===> Separates Unused Changes from Real Outages
        +---> Mathematical Blast Radius Metric R(d)
        |
[04] ML DEGRADATION & REMEDIATION ENGINE
        |
        +---> Regression Estimator ===> Predicted Developer Migration Hours & Risk Index
        +---> Patch Generator ===> Synthesizes Backward-Compatible Codemod Patches
        +---> Migration Guide Synthesizer ===> Step-by-Step Developer Documentation
        |
[05] ENTERPRISE QUALITY GATE
        |
        +---> Policy Evaluation: Passed / Blocked (Exit code 0 or 1 in CI/CD)
        </div>
      </section>
    `;

    // Bind navigation buttons
    const ctaDashboard = document.getElementById("landing-cta-dashboard");
    if (ctaDashboard) {
      ctaDashboard.addEventListener("click", () => {
        const dashBtn = document.getElementById("nav-btn-dashboard");
        if (dashBtn) dashBtn.click();
      });
    }

    const ctaSpec = document.getElementById("landing-cta-spec");
    if (ctaSpec) {
      ctaSpec.addEventListener("click", () => {
        const specBtn = document.getElementById("nav-btn-architecture");
        if (specBtn) specBtn.click();
      });
    }
  }

  function renderArchitecture(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;

    el.innerHTML = `
      <section class="spec-section">
        <h2 class="spec-heading">Simple Guide: Why Do Library Updates Crash Code?</h2>
        <p class="spec-subheading">
          Whenever you run <code>pip install --upgrade package</code>, here are the exact 4 ways things can break, why they cause errors, and how CodeDrift solves each one:
        </p>

        <!-- Card 1: Parameter Removed -->
        <div class="pane-card" style="margin-bottom: 20px;">
          <div class="pane-header">
            <span style="font-size: 13px; font-weight: 700; color: var(--status-critical);">1. Parameter Removed (e.g., Scenario 1)</span>
            <span class="badge badge-critical">TypeError</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">What happened?</p>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
              The library authors decided that an argument (like <code>currency="USD"</code>) is no longer needed and deleted it from their function definition.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">Why does your app crash?</p>
            <p style="color: #fca5a5; font-size: 13px; margin-bottom: 12px;">
              Python throws a fatal <code>TypeError: got an unexpected keyword argument 'currency'</code> the moment a user clicks checkout.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">How CodeDrift solves it:</p>
            <p style="color: var(--status-safe); font-size: 13px;">
              CodeDrift finds the exact file and line number in your codebase and creates a one-click <code>.patch</code> file that cleanly deletes the removed parameter from your function call.
            </p>
          </div>
        </div>

        <!-- Card 2: Required Parameter Added -->
        <div class="pane-card" style="margin-bottom: 20px;">
          <div class="pane-header">
            <span style="font-size: 13px; font-weight: 700; color: var(--status-critical);">2. Required Parameter Added (e.g., Scenario 2)</span>
            <span class="badge badge-critical">Missing Argument</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">What happened?</p>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
              The new version of a library added a mandatory argument (like <code>mfa_code</code> or <code>idempotency_key</code>) without providing a default value.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">Why does your app crash?</p>
            <p style="color: #fca5a5; font-size: 13px; margin-bottom: 12px;">
              Python throws <code>TypeError: missing 1 required positional argument: 'mfa_code'</code> because your existing code did not pass it.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">How CodeDrift solves it:</p>
            <p style="color: var(--status-safe); font-size: 13px;">
              CodeDrift flags this as an immediate blocker, shows your team the exact missing parameter in the Remediation Checklist, and drafts the updated signature.
            </p>
          </div>
        </div>

        <!-- Card 3: Function Deleted -->
        <div class="pane-card" style="margin-bottom: 20px;">
          <div class="pane-header">
            <span style="font-size: 13px; font-weight: 700; color: var(--status-critical);">3. Whole Function Deleted (e.g., Scenario 3)</span>
            <span class="badge badge-critical">AttributeError</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">What happened?</p>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
              The library authors renamed or completely deleted an old function (like <code>send_email()</code>) in favor of a new mechanism.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">Why does your app crash?</p>
            <p style="color: #fca5a5; font-size: 13px; margin-bottom: 12px;">
              Python throws <code>AttributeError: module has no attribute 'send_email'</code> or an <code>ImportError</code> upon startup.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">How CodeDrift solves it:</p>
            <p style="color: var(--status-safe); font-size: 13px;">
              CodeDrift detects the missing function, traces every file in your project that imported it, and points you to the new replacement in the Migration Manual.
            </p>
          </div>
        </div>

        <!-- Card 4: Return Type Changed -->
        <div class="pane-card" style="margin-bottom: 20px;">
          <div class="pane-header">
            <span style="font-size: 13px; font-weight: 700; color: var(--status-high);">4. Return Type Changed (e.g., bool to Dict)</span>
            <span class="badge badge-high">Silent Bug</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">What happened?</p>
            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 12px;">
              The function used to return a simple True/False boolean, but now returns a Dictionary with data: <code>{"status": "success"}</code>.
            </p>
            <p style="color: var(--text-primary); font-weight: 600; margin-bottom: 6px;">Why does your app crash?</p>
            <p style="color: #fca5a5; font-size: 13px; margin-bottom: 12px;">
              Any checks like <code>if is_success:</code> evaluate truthy even on errors, or code expecting a boolean fails when treating a dictionary like a primitive value.
            </p>
            <p style="color: var(--status-safe); font-size: 13px;">
              CodeDrift flags the type change in the Diff Explorer so developers know to update their response handling logic before deploying.
            </p>
          </div>
        </div>
      </section>
    `;
  }

  return {
    renderLanding,
    renderArchitecture
  };
})();
