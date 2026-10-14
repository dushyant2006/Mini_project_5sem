"""
Interactive Web Dashboard for CodeDrift (powered by Streamlit).
Run with: `codedrift ui` or `streamlit run src/codedrift/dashboard.py`
"""
from pathlib import Path
import streamlit as st

from codedrift.parser import PythonParser
from codedrift.detection import DiffEngine, SemVerAuditor
from codedrift.impact import BlastRadiusAnalyzer
from codedrift.guard import PolicyEngine
from codedrift.remediation import PatchGenerator, MigrationGuideSynthesizer
from codedrift.core.config import GuardPolicy
from codedrift.core.enums import GateDecision


st.set_page_config(
    page_title="CodeDrift Guard Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ CodeDrift: Autonomous API Breaking-Change & Degradation Guard")
st.markdown("### *Continuous Semantic Contract & Call-Graph Reachability Engine*")

# Sidebar
st.sidebar.header("⚙️ Analysis Configuration")
default_base = Path("data/fixtures/v1/payment_gateway.py")
default_new = Path("data/fixtures/v2/payment_gateway.py")
default_client = Path("data/fixtures/client_app")

old_file = st.sidebar.text_input("Upstream Base Version (v1):", value=str(default_base))
new_file = st.sidebar.text_input("Upstream Upgraded Version (v2):", value=str(default_new))
client_dir = st.sidebar.text_input("Downstream Client Application Directory:", value=str(default_client))

max_score = st.sidebar.slider("Maximum Allowable Blast Radius Score:", min_value=0.0, max_value=100.0, value=0.0, step=5.0)

run_button = st.sidebar.button("🚀 Run CodeDrift Analysis", use_container_width=True)

if run_button or "analyzed" in st.session_state:
    st.session_state["analyzed"] = True

    try:
        parser = PythonParser()
        old_mod = parser.parse_file(old_file)
        new_mod = parser.parse_file(new_file)

        engine = DiffEngine()
        diff = engine.compare(old_mod, new_mod)

        analyzer = BlastRadiusAnalyzer()
        report = analyzer.analyze(diff, client_dir=client_dir)

        policy = GuardPolicy(max_allowable_blast_radius=max_score)
        gate_res = PolicyEngine(policy).evaluate(diff, blast_report=report)

        auditor = SemVerAuditor()
        semver_res = auditor.audit_bump("1.0.0", "2.0.0", diff)

        # Top metric cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Upstream Changes", len(diff.changes))
        col2.metric("Breaking Changes", len(diff.breaking_changes))
        col3.metric("Reachable in Client Code", report.reachable_breaking_count, delta=f"{report.reachable_breaking_count} danger points" if report.reachable_breaking_count > 0 else "0 (Safe)", delta_color="inverse")
        col4.metric("Blast Radius Score", f"{report.blast_radius_score} / 100", delta=f"{'High' if report.blast_radius_score > 30 else 'Safe'}", delta_color="inverse")

        st.divider()

        # Gate decision banner
        if gate_res.decision == GateDecision.PASSED:
            st.success(f"### ✅ CI/CD Quality Gate: PASSED\n{gate_res.summary}")
        else:
            st.error(f"### ❌ CI/CD Quality Gate: BLOCKED (Exit Code 1)\n{gate_res.summary}")
            with st.expander("🚨 Policy Violations", expanded=True):
                for v in gate_res.violations:
                    st.write(f"- 🔴 **{v}**")

        st.divider()

        # Tab layout
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Semantic API Diff",
            "🧭 Call Graph & Reachability",
            "🛠️ Autonomous Codemod Patches",
            "📜 SemVer & Rules Auditor"
        ])

        with tab1:
            st.subheader("Upstream API Contract Shifts")
            filter_sev = st.multiselect("Filter by Severity:", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
            
            rows = []
            for c in diff.changes:
                if c.severity in filter_sev:
                    rows.append({
                        "Severity": c.severity,
                        "Type": c.change_type,
                        "Target Symbol": c.qualified_name,
                        "Breaking?": "🚨 YES" if c.is_breaking else "🟢 NO",
                        "Description": c.description,
                    })
            if rows:
                st.dataframe(rows, use_container_width=True)
            else:
                st.info("No changes matching the selected filter.")

        with tab2:
            st.subheader("Downstream Client Blast Radius Impact")
            st.write(f"Analyzed Client Source Files: `{', '.join(report.affected_files) if report.affected_files else 'None'}`")

            for item in report.items:
                if item.is_reachable:
                    with st.expander(f"🚨 REACHABLE: {item.change.change_type} on `{item.change.qualified_name}` (Impact: {item.impact_score})", expanded=True):
                        st.markdown(f"**Severity:** `{item.change.severity}` | **Description:** {item.change.description}")
                        if item.change.suggested_migration:
                            st.info(f"💡 **Suggested Fix:** {item.change.suggested_migration}")
                        st.markdown("**Exact Call Sites Found in Client Code:**")
                        for cs in item.call_sites:
                            st.code(f"# File: {cs.file_path}:{cs.line} (inside '{cs.caller_function}')\n{cs.code_snippet}", language="python")
                else:
                    with st.expander(f"🟢 UNREACHABLE (Dead/Unused in Client): `{item.change.qualified_name}`", expanded=False):
                        st.caption("This breaking change exists upstream, but client code does NOT execute it. Reachability = 0.")

        with tab3:
            st.subheader("Synthesized Automated Codemod Patches")
            patcher = PatchGenerator()
            patches = patcher.generate_patches(report)

            if patches:
                for idx, p in enumerate(patches, 1):
                    st.markdown(f"#### Patch #{idx}: `{Path(p.file_path).name}`")
                    st.caption(f"Target: {p.target_symbol} | Reason: {p.reason}")
                    st.code(p.diff, language="diff")
            else:
                st.info("No automated syntactic replacements required.")

            st.divider()
            st.subheader("Developer Upgrade Migration Guide")
            guide = MigrationGuideSynthesizer().generate_markdown(report)
            st.markdown(guide)

        with tab4:
            st.subheader("SemVer 2.0.0 Rule Auditor")
            if semver_res["valid"]:
                st.success(f"✔ Bump type **{semver_res['bump_type']}** conforms to Semantic Versioning specifications.")
            else:
                st.error("✘ SemVer Violation Detected!")
                for v in semver_res["violations"]:
                    st.write(f"- {v}")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        st.exception(e)
else:
    st.info("👈 Click **Run CodeDrift Analysis** in the sidebar to start!")
