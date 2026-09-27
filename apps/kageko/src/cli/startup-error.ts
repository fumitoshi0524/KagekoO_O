export function formatStartupError(error: unknown): string {
	const message = safeTerminalMessage(describeError(error));
	if (error instanceof Error && error.name === "WorkspaceTrustError") {
		return `kageko: ${message} Run \`kageko trust grant\` after reviewing the workspace, or start the TUI and grant trust there.`;
	}
	if (/api[- ]?key|credential|unauthorized|401/i.test(message)) {
		return `kageko: ${message} Run \`kageko setup\` or \`kageko auth set <provider> <key>\`.`;
	}
	return `kageko: ${message}`;
}

function describeError(error: unknown, depth = 0): string {
	if (!(error instanceof Error) || depth > 4) return String(error ?? "Unknown error");
	const parts = [error.message];
	const causes = error instanceof AggregateError ? error.errors : error.cause instanceof Error ? [error.cause] : [];
	for (const cause of causes) {
		const description = describeError(cause, depth + 1);
		if (description && description !== error.message) parts.push(description);
	}
	return parts.join("; caused by: ");
}

function safeTerminalMessage(value: string): string {
	return value
		.replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, "")
		.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
		.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g, "");
}
