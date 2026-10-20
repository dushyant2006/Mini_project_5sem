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
          Upstream dependency updates silently break downstream systems even when versions comply with SemVer.
          CodeDrift performs deep AST contract diffing, static call-graph reachability analysis, and generates
          autonomous codemod patches before broken dependencies reach production.
        </p>
        <div class="hero-actions">
          <button class="btn-primary" id="landing-cta-dashboard">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Launch Live Analysis Dashboard
          </button>
          <button class="btn-secondary" id="landing-cta-spec">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            Read Technical Specification
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
        <h2 class="spec-heading">Technical Specification & Algorithmic Rigor</h2>
        <p class="spec-subheading">
          Formal definitions, mathematical formulations, and engineering principles governing CodeDrift.
        </p>

        <div class="pane-card" style="margin-bottom: 24px;">
          <div class="pane-header">
            <span>Mathematical Blast Radius Formulation</span>
            <span class="badge badge-neutral">Formula Spec</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-secondary); margin-bottom: 12px;">
              The Normalized Blast Radius Score is computed over the set of all reachable downstream call-sites <code>S</code>:
            </p>
            <div class="terminal-box" style="font-size: 14px; margin-bottom: 14px;">
R(d) = &Sigma; [ w_severity(s) &times; C(s) &times; D(s) ]

Where:
  w_severity(s) &in; { CRITICAL: 1.0, HIGH: 0.6, MEDIUM: 0.3, LOW: 0.1 }
  C(s)          = Call-site reachability depth multiplier (Direct = 1.0, Indirect = 0.5)
  D(s)          = File critical path weight (Production worker = 1.0, Test fixture = 0.2)
            </div>
            <p style="color: var(--text-muted); font-size: 13px;">
              If any contract violation exceeds the maximum allowable threshold &theta; configured in <code>guard.yaml</code>,
              the policy engine flags a non-zero exit code (CI failure).
            </p>
          </div>
        </div>

        <div class="pane-card" style="margin-bottom: 24px;">
          <div class="pane-header">
            <span>SemVer 2.0 Invariant Matrix</span>
            <span class="badge badge-neutral">SemVer RFC Spec</span>
          </div>
          <div style="padding: 20px;">
            <table class="data-table">
              <thead>
                <tr>
                  <th>API Mutation Type</th>
                  <th>Permissible Release Type</th>
                  <th>CodeDrift Enforcement</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Removal of Public Function / Method</td>
                  <td>MAJOR Bump (x.0.0)</td>
                  <td><span class="badge badge-critical">FLAGGED AS BREAKING</span></td>
                </tr>
                <tr>
                  <td>Removal of Named Parameter</td>
                  <td>MAJOR Bump (x.0.0)</td>
                  <td><span class="badge badge-critical">FLAGGED AS BREAKING</span></td>
                </tr>
                <tr>
                  <td>Adding Required Parameter Without Default</td>
                  <td>MAJOR Bump (x.0.0)</td>
                  <td><span class="badge badge-critical">FLAGGED AS BREAKING</span></td>
                </tr>
                <tr>
                  <td>Return Type Modification</td>
                  <td>MAJOR Bump (x.0.0)</td>
                  <td><span class="badge badge-high">FLAGGED AS BREAKING</span></td>
                </tr>
                <tr>
                  <td>Adding Optional Parameter with Default</td>
                  <td>MINOR Bump (0.x.0)</td>
                  <td><span class="badge badge-safe">BACKWARD COMPATIBLE</span></td>
                </tr>
                <tr>
                  <td>Internal Implementation Bugfix</td>
                  <td>PATCH Bump (0.0.x)</td>
                  <td><span class="badge badge-safe">BACKWARD COMPATIBLE</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="pane-card">
          <div class="pane-header">
            <span>Autonomous Codemod Synthesis Engine</span>
            <span class="badge badge-neutral">Remediation Spec</span>
          </div>
          <div style="padding: 20px;">
            <p style="color: var(--text-secondary); margin-bottom: 12px;">
              When an upstream breaking change is identified and downstream call-sites are found,
              CodeDrift generates AST-guided unified diffs using standard patch formats:
            </p>
            <ul style="color: var(--text-secondary); padding-left: 20px; line-height: 1.8;">
              <li><strong>Adapter Shim Generation:</strong> Preserves previous signatures by injecting default argument bindings.</li>
              <li><strong>Caller Invocation Rewriting:</strong> Automates migration to new keyword arguments (e.g. adding idempotency keys or transaction tokens).</li>
              <li><strong>Zero External Lock-in:</strong> Output is standard <code>git apply</code> compatible unified patches.</li>
            </ul>
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
