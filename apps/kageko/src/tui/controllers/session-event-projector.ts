import type { Event } from "@kageko/node-sdk";
import { sanitizeTerminalText } from "@kageko/tui-kit";
import type { ActivityRecord, TranscriptRecord } from "../types.js";

export interface Projection {
	readonly records: readonly TranscriptRecord[];
	readonly activities?: readonly ActivityRecord[];
	readonly turnLive?: boolean;
	readonly finalizeLive?: boolean;
}
const identity = (event: Event, suffix = "") =>
	`${"sequence" in event.meta ? event.meta.sequence : event.meta.eventId}${suffix}`;
const content = (value: unknown) =>
	sanitizeTerminalText(typeof value === "string" ? value : value === undefined ? "" : JSON.stringify(value));
const activity = (
	id: string,
	kind: ActivityRecord["kind"],
	label: string,
	state: ActivityRecord["state"],
	detail?: string,
): ActivityRecord => ({ id, kind, label, state, detail });
const record = (
	event: Event,
	kind: TranscriptRecord["kind"],
	text: string,
	suffix = "",
	extra: Partial<TranscriptRecord> = {},
): TranscriptRecord => ({
	id: identity(event, suffix),
	kind,
	text: content(text),
	sequence: "sequence" in event.meta ? event.meta.sequence : undefined,
	eventId: event.meta.eventId,
	activityId: event.meta.activityId,
	...extra,
});
function toolPresentation(name: string, output = ""): "diff" | "code" | "text" | "subagent" | "plan" {
	const value = `${name}\n${output}`.toLowerCase();
	if (value.includes("diff") || output.includes("@@") || (output.includes("+ ") && output.includes("- ")))
		return "diff";
	if (value.includes("plan")) return "plan";
	if (value.includes("subagent") || value.includes("agent")) return "subagent";
	if (value.includes("code") || output.includes("```")) return "code";
	return "text";
}

/** Converts the SDK union once; rendering never has to inspect transport payloads. */
export function projectSessionEvent(event: Event): Projection {
	switch (event.type) {
		case "user.prompt":
			return event.data.origin === undefined || event.data.origin === "user"
				? { records: [record(event, "user", event.data.content)] }
				: { records: [] };
		case "text.delta":
			return { records: [record(event, "assistant", event.data.delta, ":live", { streaming: true })], turnLive: true };
		case "assistant.text":
			return { records: [record(event, "assistant", event.data.content)], finalizeLive: true };
		case "thinking.delta":
			return { records: [record(event, "thinking", event.data.delta, ":thinking-live", { streaming: true })] };
		case "assistant.thinking":
			return { records: [record(event, "thinking", event.data.content)], finalizeLive: true };
		case "tool.call.delta":
			return {
				records: [
					record(event, "tool", event.data.name, `:tool:${event.data.id}`, {
						streaming: true,
						tool: {
							callId: event.data.id,
							name: event.data.name,
							arguments: content(event.data.argumentsPartial),
							presentation: toolPresentation(event.data.name),
						},
					}),
				],
				activities: [activity(event.data.id, "tool", event.data.name, "running")],
			};
		case "tool.call":
			return {
				records: [
					record(event, "tool", event.data.call.name, `:tool:${event.data.call.id}`, {
						detail: content(event.data.call.arguments),
						tool: {
							callId: event.data.call.id,
							name: event.data.call.name,
							arguments: content(event.data.call.arguments),
							presentation: toolPresentation(event.data.call.name),
						},
					}),
				],
				activities: [activity(event.data.call.id, "tool", event.data.call.name, "running")],
			};
		case "tool.progress":
			return {
				records: [
					record(event, "tool", event.data.call.name, `:progress:${event.data.call.id}`, {
						tool: { callId: event.data.call.id, name: event.data.call.name, progress: content(event.data.progress) },
					}),
				],
				activities: [
					activity(event.data.call.id, "tool", event.data.call.name, "running", content(event.data.progress)),
				],
			};
		case "tool.result": {
			const failed = !!event.data.result.isError;
			const output = content(event.data.result.output);
			return {
				records: [
					record(event, "tool-result", event.data.call.name, `:result:${event.data.call.id}`, {
						detail: output,
						state: failed ? "failed" : "success",
						tool: {
							callId: event.data.call.id,
							name: event.data.call.name,
							output,
							presentation: toolPresentation(event.data.call.name, output),
							error: failed ? output : undefined,
						},
					}),
				],
				activities: [activity(event.data.call.id, "tool", event.data.call.name, failed ? "failed" : "success", output)],
			};
		}
		case "process.started":
		case "process.requested":
			return {
				records: [
					record(
						event,
						"process",
						`Process ${event.type === "process.started" ? "started" : "queued"} · ${event.data.task.taskId}`,
						"",
					),
				],
				activities: [
					activity(event.data.task.taskId, "process", `Process ${event.data.task.taskId.slice(0, 8)}`, "running"),
				],
			};
		case "process.terminated": {
			const failed = event.data.task.status !== "completed";
			return {
				records: [
					record(event, "process", `Process ${event.data.task.status} · ${event.data.task.taskId}`, "", {
						detail: event.data.task.stopReason,
						state: failed ? "failed" : "success",
					}),
				],
				activities: [
					activity(
						event.data.task.taskId,
						"process",
						`Process ${event.data.task.taskId.slice(0, 8)}`,
						failed ? "failed" : "success",
						event.data.task.stopReason,
					),
				],
			};
		}
		case "subagent.started": {
			const id = event.data.subagentId ?? event.meta.activityId ?? identity(event);
			return {
				records: [record(event, "subagent", `Subagent started · ${event.data.prompt}`)],
				activities: [activity(id, "subagent", "Subagent", "running", event.data.prompt)],
			};
		}
		case "subagent.completed":
		case "subagent.failed": {
			const id = event.data.subagentId ?? event.meta.activityId ?? identity(event);
			const failed = event.type === "subagent.failed";
			return {
				records: [
					record(
						event,
						"subagent",
						failed ? `Subagent failed · ${event.data.error.message}` : "Subagent complete",
						"",
						{
							detail: failed ? event.data.error.message : content(event.data.result),
							state: failed ? "failed" : "success",
						},
					),
				],
				activities: [activity(id, "subagent", "Subagent", failed ? "failed" : "success")],
			};
		}
		case "turn.started":
			return {
				records: [],
				turnLive: true,
			};
		case "turn.end":
			return {
				records: [],
				turnLive: false,
				finalizeLive: true,
			};
		case "turn.failed":
			return {
				records: [record(event, "error", userFacingTurnError(event.data.message), "", { state: "failed" })],
				turnLive: false,
				finalizeLive: true,
			};
		case "turn.interrupted":
			return {
				records: [],
				turnLive: false,
				finalizeLive: true,
			};
		case "session.status.changed":
			return {
				records: [],
				turnLive: event.data.status === "running",
			};
		case "step.retrying":
			return { records: [] };
		case "step.begin":
			return { records: [] };
		case "step.end":
			return { records: [] };
		default:
			return { records: [] };
	}
}

/** Lifecycle events are intentionally quiet; errors need a single actionable line. */
function userFacingTurnError(message: string): string {
	if (/re-login required|session expired|oauth_relogin_required/i.test(message)) {
		return "OpenAI Codex session expired or was revoked. Run `kageko auth login openai-codex` and try again.";
	}
	return message;
}
