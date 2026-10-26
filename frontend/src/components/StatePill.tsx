import type { WorkflowState } from "../types";

export function StatePill({ state }: { state: WorkflowState }) {
  return <span className={`state-pill state-${state}`}>{state.replaceAll("_", " ")}</span>;
}

