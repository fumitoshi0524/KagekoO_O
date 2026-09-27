import type { SessionSummary } from "@kageko/node-sdk";
export function sessionSearchLabel(session: SessionSummary): string {
	return `${session.title ?? ""} ${session.cwd} ${session.sessionId}`;
}
