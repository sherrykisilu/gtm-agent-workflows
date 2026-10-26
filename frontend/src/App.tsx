import { useCallback, useEffect, useMemo, useState } from "react";
import { createDemoWorkflow, decide, listWorkflows } from "./api";
import { StatePill } from "./components/StatePill";
import { WorkflowDetail } from "./components/WorkflowDetail";
import type { Workflow } from "./types";

export default function App() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    try {
      const data = await listWorkflows();
      setWorkflows(data);
      setSelectedId((current) => current ?? data[0]?.id);
      setError(undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load workflows");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const selected = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedId) ?? workflows[0],
    [selectedId, workflows]
  );

  async function createDemo() {
    setBusy(true);
    try {
      const workflow = await createDemoWorkflow();
      setSelectedId(workflow.id);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create demo");
    } finally {
      setBusy(false);
    }
  }

  async function handleDecision(decision: "approve" | "reject") {
    if (!selected) return;
    setBusy(true);
    try {
      await decide(selected.id, decision);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">G</div>
          <div>
            <strong>Grounded GTM</strong>
            <span>Human-approved workflow lab</span>
          </div>
        </div>
        <div className="environment"><span /> Local replay mode</div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">AI where it helps. Humans where it matters.</p>
          <h1>Turn account signals into safe, evidence-backed action.</h1>
          <p>
            A complete portfolio implementation of grounded retrieval, structured generation,
            policy checks, durable orchestration, and mandatory approval.
          </p>
        </div>
        <button className="button primary hero-button" disabled={busy} onClick={createDemo}>
          + Run demo workflow
        </button>
      </section>

      {error && <div className="page-error">{error}</div>}

      <div className="workspace">
        <aside>
          <div className="aside-heading">
            <div>
              <p className="eyebrow">Queue</p>
              <h2>Workflows</h2>
            </div>
            <span className="count">{workflows.length}</span>
          </div>
          <div className="workflow-list">
            {workflows.map((workflow) => (
              <button
                key={workflow.id}
                className={`workflow-row ${workflow.id === selected?.id ? "selected" : ""}`}
                onClick={() => setSelectedId(workflow.id)}
              >
                <div>
                  <strong>{workflow.request.account_event.account_name}</strong>
                  <span>{workflow.request.account_event.contact_name}</span>
                </div>
                <StatePill state={workflow.state} />
              </button>
            ))}
            {!workflows.length && (
              <div className="empty-list">
                <p>No workflows yet.</p>
                <span>Run the demo to create a grounded brief.</span>
              </div>
            )}
          </div>
        </aside>
        {selected ? (
          <WorkflowDetail workflow={selected} busy={busy} onDecision={handleDecision} />
        ) : (
          <section className="welcome-panel">
            <div className="welcome-icon">✓</div>
            <h2>Ready for a safe demo</h2>
            <p>Create a replay workflow. No external systems or paid AI accounts are used.</p>
          </section>
        )}
      </div>
    </main>
  );
}

