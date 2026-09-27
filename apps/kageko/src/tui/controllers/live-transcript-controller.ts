import type { Event } from "@kageko/node-sdk";
import type { TuiAction } from "../tui-state.js";
import type { Projection } from "./session-event-projector.js";
import type { TranscriptRecord } from "../types.js";

export interface LiveTranscriptControllerHost {
	dispatch(action: TuiAction): void;
	addRecord(record: TranscriptRecord): void;
}

/**
 * Reconciles transport-level streaming records with their durable counterparts.
 *
 * The SDK may emit a live text delta followed by a complete assistant event, and
 * tool calls follow the same pattern with partial JSON arguments. Keeping that
 * protocol knowledge outside the TUI coordinator makes session switching and
 * rendering independent from event ordering details.
 */
export class LiveTranscriptController {
	private activeAssistant: TranscriptRecord | undefined;
	private activeThinking: TranscriptRecord | undefined;
	private readonly activeTools = new Map<string, TranscriptRecord>();

	constructor(private readonly host: LiveTranscriptControllerHost) {}

	apply(event: Event, projection: Projection): void {
		const durableContent = projection.records.some((item) => item.kind === "assistant" || item.kind === "thinking");
		if (projection.finalizeLive && !durableContent) this.finish();

		for (const item of projection.records) {
			if (event.type === "tool.call.delta" && item.kind === "tool") {
				this.appendToolDelta(event.data.id, item);
			} else if (event.type === "tool.call" && item.kind === "tool") {
				this.reconcileToolCall(event.data.call.id, item);
			} else if (event.type === "tool.progress" && item.kind === "tool") {
				this.updateToolProgress(event.data.call.id, item);
			} else if (item.kind === "assistant" && item.streaming) {
				this.appendLive("assistant", item);
			} else if (item.kind === "thinking" && item.streaming) {
				this.appendLive("thinking", item);
			} else if (item.kind === "assistant" && this.activeAssistant) {
				this.host.dispatch({
					type: "replace",
					id: this.activeAssistant.id,
					patch: { text: item.text, streaming: false, sequence: item.sequence, eventId: item.eventId },
				});
				this.activeAssistant = undefined;
			} else if (item.kind === "thinking" && this.activeThinking) {
				this.host.dispatch({
					type: "replace",
					id: this.activeThinking.id,
					patch: { text: item.text, streaming: false },
				});
				this.activeThinking = undefined;
			} else {
				this.host.addRecord(item);
			}
		}
	}

	finish(): void {
		for (const live of [this.activeAssistant, this.activeThinking, ...this.activeTools.values()]) {
			if (live) this.host.dispatch({ type: "replace", id: live.id, patch: { streaming: false } });
		}
		this.clear();
	}

	clear(): void {
		this.activeAssistant = undefined;
		this.activeThinking = undefined;
		this.activeTools.clear();
	}

	private appendLive(kind: "assistant" | "thinking", template: TranscriptRecord): void {
		const current = kind === "assistant" ? this.activeAssistant : this.activeThinking;
		if (current?.streaming) {
			const text = current.text + template.text;
			this.host.dispatch({ type: "replace", id: current.id, patch: { text } });
			const next = { ...current, text };
			if (kind === "assistant") this.activeAssistant = next;
			else this.activeThinking = next;
			return;
		}

		this.host.addRecord(template);
		if (kind === "assistant") this.activeAssistant = { ...template };
		else this.activeThinking = { ...template };
	}

	private appendToolDelta(callId: string, template: TranscriptRecord): void {
		const current = this.activeTools.get(callId);
		if (!current) {
			this.host.addRecord(template);
			this.activeTools.set(callId, { ...template });
			return;
		}

		const tool = {
			...current.tool,
			...template.tool,
			callId: template.tool?.callId ?? current.tool?.callId ?? callId,
			name: template.tool?.name ?? current.tool?.name ?? template.text,
			arguments: `${current.tool?.arguments ?? ""}${template.tool?.arguments ?? ""}`,
		};
		this.host.dispatch({ type: "replace", id: current.id, patch: { text: template.text, tool, streaming: true } });
		this.activeTools.set(callId, { ...current, text: template.text, tool, streaming: true });
	}

	private reconcileToolCall(callId: string, durable: TranscriptRecord): void {
		const current = this.activeTools.get(callId);
		if (!current) {
			this.host.addRecord(durable);
			this.activeTools.set(callId, { ...durable });
			return;
		}

		this.host.dispatch({
			type: "replace",
			id: current.id,
			patch: {
				text: durable.text,
				detail: durable.detail,
				tool: durable.tool,
				streaming: false,
				sequence: durable.sequence,
				eventId: durable.eventId,
				activityId: durable.activityId,
			},
		});
		this.activeTools.set(callId, { ...durable, id: current.id });
	}

	private updateToolProgress(callId: string, progress: TranscriptRecord): void {
		const current = this.activeTools.get(callId);
		if (!current) {
			const stable = { ...progress, id: `tool:${callId}` };
			this.host.addRecord(stable);
			this.activeTools.set(callId, stable);
			return;
		}
		const tool = {
			...current.tool,
			...progress.tool,
			callId,
			name: progress.tool?.name ?? current.tool?.name ?? progress.text,
		};
		this.host.dispatch({ type: "replace", id: current.id, patch: { text: progress.text, tool } });
		this.activeTools.set(callId, { ...current, text: progress.text, tool });
	}
}
