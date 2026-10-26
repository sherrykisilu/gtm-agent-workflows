export type WorkflowState =
  | "received"
  | "queued"
  | "retrieving"
  | "generating"
  | "policy_check"
  | "awaiting_approval"
  | "approved"
  | "rejected"
  | "executing"
  | "completed"
  | "retrying"
  | "failed";

export interface Citation {
  document_id: string;
  title: string;
  quote: string;
}

export interface Workflow {
  id: string;
  state: WorkflowState;
  attempts: number;
  error?: string;
  request: {
    account_event: {
      account_name: string;
      contact_name: string;
      contact_email: string;
      source: string;
    };
    meeting_notes: {
      meeting_id: string;
      transcript: string;
    };
  };
  result?: {
    account_summary: string;
    needs: string[];
    risks: string[];
    recommended_next_step: string;
    citations: Citation[];
    proposed_action: {
      channel: "email" | "crm_task";
      recipient: string;
      subject: string;
      body: string;
    };
  };
  policy?: {
    passed: boolean;
    violations: string[];
  };
  events: Array<{
    state: WorkflowState;
    at: string;
    detail: string;
  }>;
}

