import type { Workflow } from "./types";

const TOKEN = import.meta.env.VITE_API_TOKEN ?? "local-demo-token";
const headers = {
  Authorization: `Bearer ${TOKEN}`,
  "Content-Type": "application/json"
};

async function parse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? "Request failed");
  }
  return response.json() as Promise<T>;
}

export async function listWorkflows(): Promise<Workflow[]> {
  return parse(await fetch("/api/workflows", { headers }));
}

export async function createDemoWorkflow(): Promise<Workflow> {
  const timestamp = Date.now();
  return parse(
    await fetch("/api/workflows", {
      method: "POST",
      headers: { ...headers, "Idempotency-Key": `ui-demo-${timestamp}` },
      body: JSON.stringify({
        account_event: {
          event_type: "meeting_completed",
          account_id: `acct-${timestamp}`,
          account_name: "Northwind Labs",
          contact_name: "Avery Morgan",
          contact_email: "avery@example.test",
          source: "portfolio-ui",
          attributes: { region: "EMEA" }
        },
        meeting_notes: {
          meeting_id: `meeting-${timestamp}`,
          transcript:
            "The team needs an integration that reduces manual follow-up. Security review and a human approval step are required before messages can be sent. The timeline is still being discussed.",
          occurred_at: new Date().toISOString()
        }
      })
    })
  );
}

export async function decide(
  workflowId: string,
  decision: "approve" | "reject"
): Promise<Workflow> {
  return parse(
    await fetch(`/api/workflows/${workflowId}/decision`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        decision,
        reviewer: "Portfolio Reviewer",
        reason:
          decision === "approve"
            ? "Evidence, claims, and recipient reviewed"
            : "Draft requires revision before external action"
      })
    })
  );
}

