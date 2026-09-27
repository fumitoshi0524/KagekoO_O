export type PermissionDecision = "allow" | "ask" | "deny";
export interface PermissionResult {
	readonly decision: PermissionDecision;
	readonly reason: string;
}
