import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("shows the approval gate and sends an explicit decision", async () => {
    const workflow = {
      id: "workflow-1",
      state: "awaiting_approval",
      attempts: 1,
      request: {
        account_event: {
          account_name: "Northwind Labs",
          contact_name: "Avery Morgan",
          contact_email: "avery@example.test",
          source: "test"
        },
        meeting_notes: { meeting_id: "meeting-1", transcript: "Needs approval." }
      },
      result: {
        account_summary: "A grounded summary.",
        needs: ["Approval"],
        risks: ["Timeline"],
        recommended_next_step: "Review.",
        citations: [
          { document_id: "approved", title: "Approved source", quote: "Approval is required." }
        ],
        proposed_action: {
          channel: "email",
          recipient: "avery@example.test",
          subject: "Follow-up",
          body: "A draft that has not been sent."
        }
      },
      policy: { passed: true, violations: [] },
      events: [
        {
          state: "awaiting_approval",
          at: "2026-10-26T14:00:00Z",
          detail: "Waiting for approval"
        }
      ]
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") {
        return new Response(JSON.stringify({ ...workflow, state: "completed" }), { status: 200 });
      }
      return new Response(JSON.stringify([workflow]), { status: 200 });
    });

    render(<App />);
    expect((await screen.findAllByText("Northwind Labs")).length).toBeGreaterThan(0);
    expect(screen.getByText("Proposed action · not sent")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Approve & run replay" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/workflows/workflow-1/decision",
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
