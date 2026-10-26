import type { Workflow } from "../types";
import { StatePill } from "./StatePill";

interface Props {
  workflow: Workflow;
  busy: boolean;
  onDecision: (decision: "approve" | "reject") => void;
}

export function WorkflowDetail({ workflow, busy, onDecision }: Props) {
  const brief = workflow.result;
  return (
    <section className="detail-panel">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Account workflow</p>
          <h2>{workflow.request.account_event.account_name}</h2>
          <p>
            {workflow.request.account_event.contact_name} ·{" "}
            {workflow.request.account_event.source}
          </p>
        </div>
        <StatePill state={workflow.state} />
      </header>

      <div className="trust-strip">
        <span>Deterministic replay</span>
        <span>{workflow.attempts} attempt{workflow.attempts === 1 ? "" : "s"}</span>
        <span>{brief?.citations.length ?? 0} citations</span>
        <span>{workflow.policy?.passed ? "Policy passed" : "Policy pending"}</span>
      </div>

      {workflow.error && <div className="error-card">{workflow.error}</div>}

      {brief ? (
        <div className="detail-grid">
          <article className="card span-two">
            <p className="eyebrow">Grounded account brief</p>
            <h3>What we know</h3>
            <p className="summary">{brief.account_summary}</p>
            <div className="columns">
              <div>
                <h4>Needs</h4>
                <ul>{brief.needs.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              <div>
                <h4>Risks</h4>
                <ul>{brief.risks.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            </div>
          </article>

          <article className="card">
            <p className="eyebrow">Evidence</p>
            <h3>Approved sources</h3>
            <div className="citations">
              {brief.citations.map((citation) => (
                <blockquote key={citation.document_id}>
                  <strong>{citation.title}</strong>
                  <p>“{citation.quote}”</p>
                </blockquote>
              ))}
            </div>
          </article>

          <article className="card action-card">
            <p className="eyebrow">Proposed action · not sent</p>
            <h3>{brief.proposed_action.subject}</h3>
            <p className="recipient">To: {brief.proposed_action.recipient}</p>
            <pre>{brief.proposed_action.body}</pre>
            {workflow.state === "awaiting_approval" && (
              <div className="decision-row">
                <button className="button secondary" disabled={busy} onClick={() => onDecision("reject")}>
                  Reject
                </button>
                <button className="button primary" disabled={busy} onClick={() => onDecision("approve")}>
                  Approve &amp; run replay
                </button>
              </div>
            )}
          </article>
        </div>
      ) : (
        <article className="card empty-card">
          <div className="spinner" />
          <h3>Building the grounded brief</h3>
          <p>The workflow is retrieving approved evidence and validating a structured draft.</p>
        </article>
      )}

      <article className="card timeline-card">
        <p className="eyebrow">Audit timeline</p>
        <h3>Lifecycle events</h3>
        <ol className="timeline">
          {[...workflow.events].reverse().map((event, index) => (
            <li key={`${event.at}-${index}`}>
              <StatePill state={event.state} />
              <div>
                <p>{event.detail}</p>
                <time>{new Date(event.at).toLocaleString()}</time>
              </div>
            </li>
          ))}
        </ol>
      </article>
    </section>
  );
}

