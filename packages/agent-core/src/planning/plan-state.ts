export type PlanStatus = "draft" | "active" | "completed" | "cancelled";
export interface PlanState {
	readonly planId: string;
	readonly status: PlanStatus;
	readonly steps: readonly string[];
}
