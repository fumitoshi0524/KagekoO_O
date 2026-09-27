/** Parses the headless `/goal` prompt prefix; creation runs through the SDK goal API. */
export interface GoalPrefixRequest {
	readonly objective: string;
	readonly replace: boolean;
}

export const goalExitCodes = { complete: 0, blocked: 3, paused: 6 } as const;

export function goalExitCode(status: string | undefined): number {
	return status === "blocked"
		? goalExitCodes.blocked
		: status === "paused"
			? goalExitCodes.paused
			: goalExitCodes.complete;
}

export function parseGoalPrefix(prompt: string): GoalPrefixRequest | undefined {
	const command = prompt.trim();
	if (!/^\/goal(?:\s|$)/.test(command)) return undefined;
	const tokens = command.slice(5).trim().split(/\s+/).filter(Boolean);
	if (!tokens.length || tokens[0] === "status" || ["pause", "resume", "cancel", "next"].includes(tokens[0]!))
		return undefined;
	const replace = tokens[0] === "replace";
	if (replace) tokens.shift();
	if (tokens[0] === "--") tokens.shift();
	if (!tokens.length || tokens[0]?.startsWith("/")) return undefined;
	const objective = tokens.join(" ");
	return objective.length <= 4000 ? { objective, replace } : undefined;
}
