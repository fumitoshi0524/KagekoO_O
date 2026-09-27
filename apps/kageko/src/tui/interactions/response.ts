import type { ApprovalDecision } from "@kageko/node-sdk";

/** A dismissed permission prompt is always rejected. */
export function safeApprovalDecision(answer: string): ApprovalDecision {
	const value = answer.trim().toLowerCase();
	if (value === "1" || value === "once") return "once";
	if (value === "2" || value === "session") return "session";
	return "deny";
}
