import type { Event } from "@kageko/node-sdk";
import type { SessionSummary } from "@kageko/node-sdk";
import { sanitizeTerminalText } from "@kageko/tui-kit";
import { processCliIO, type CliIO, writeLine } from "./io.js";

export function printTurnEvent(
	event: Event,
	output: "text" | "json" | "stream-json" = "text",
	write: (chunk: string) => unknown = (chunk) => process.stdout.write(chunk),
): void {
	if (output === "stream-json") {
		write(
			`${JSON.stringify({ schemaVersion: 1, sessionId: event.meta.sessionId, turnId: event.meta.turnId ?? null, activityId: event.meta.activityId ?? event.meta.turnId ?? null, event })}\n`,
		);
		return;
	}
	if (output === "json") {
		write(`${JSON.stringify(event)}\n`);
		return;
	}
	if (event.type === "assistant.text") {
		write(sanitizeTerminalText(event.data.content));
		return;
	}
	if (event.type === "tool.call") {
		write(
			`\n→ ${sanitizeTerminalText(event.data.call.name)}(${sanitizeTerminalText(JSON.stringify(event.data.call.arguments))})\n`,
		);
		return;
	}
	if (event.type === "tool.result") {
		write(
			`← ${event.data.result.isError ? "error" : "ok"}: ${sanitizeTerminalText(String(event.data.result.output ?? ""))}\n`,
		);
		return;
	}
	if (event.type === "turn.end") {
		// Text mode is a terminal-facing stream. Always terminate the final
		// response so a shell prompt or the next diagnostic cannot be appended to
		// model output when the provider omitted a trailing newline.
		write(event.data.result.content.endsWith("\n") ? "" : "\n");
	}
}

export function printSessionList(sessions: readonly SessionSummary[], io: CliIO = processCliIO): void {
	if (!sessions.length) {
		writeLine(io, "No sessions.");
		return;
	}
	writeLine(io, "SESSION ID\tSTATE\tTITLE\tWORKSPACE");
	for (const session of sessions) {
		writeLine(
			io,
			`${tableCell(session.sessionId)}\t${session.archived ? "archived" : "active"}\t${tableCell(session.title ?? "")}\t${tableCell(session.cwd)}`,
		);
	}
}

export function printValue(value: unknown, output: "text" | "json" = "text", io: CliIO = processCliIO): void {
	if (output === "json") writeLine(io, JSON.stringify(value, null, 2));
	else if (typeof value === "string") writeLine(io, value);
	else writeLine(io, JSON.stringify(value, null, 2));
}

function tableCell(value: string): string {
	return value
		.replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, "")
		.replace(/\x1b\[[0-?]*[ -/]*[@-~]/g, "")
		.replace(/[\u0000-\u001f\u007f-\u009f]+/g, " ")
		.trim();
}
