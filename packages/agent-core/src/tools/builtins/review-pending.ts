import type { Tool, ToolContext } from "../types.js";
import type { PendingEntry } from "../../memory/learning/types.js";

interface ReviewPendingArgs {
	action: "list" | "approve" | "reject" | "clear";
	id?: string;
}

export const reviewPendingTool: Tool<ReviewPendingArgs> = {
	name: "review_pending",
	description: "List, approve, or reject pending learning outputs (skills, profile corrections, preferences).",
	parameters: {
		type: "object",
		properties: {
			action: {
				type: "string",
				enum: ["list", "approve", "reject", "clear"],
				description: "Action to perform",
			},
			id: { type: "string", description: "Pending entry id (required for approve/reject)" },
		},
		required: ["action"],
	},
	async execute({ action, id }: ReviewPendingArgs, { session }: ToolContext) {
		if (!session?.learningProcessor) {
			return { output: "Learning processor is not available.", isError: true };
		}

		const processor = session.learningProcessor;
		// This is the agent-facing synchronization point for the resident branch.
		// A list immediately after need_capability must not claim the queue is empty
		// while synthesis is still running, otherwise the coordinator may create a
		// redundant skill or capability to compensate for a stale read.
		await session.learningBus?.flush();
		await processor.flush();

		if (action === "list") {
			const pending = await processor.listPending();
			if (pending.length === 0) {
				return { output: "No pending learning outputs." };
			}
			const lines = pending.map((entry: PendingEntry, i: number) => {
				const { event, decision, output } = entry;
				const outputRecord = output as Record<string, unknown> | undefined;
				const capabilityKind =
					outputRecord?.["kind"] === "tool" || outputRecord?.["kind"] === "mcp"
						? String(outputRecord["kind"])
						: "skill";
				const preview = outputRecord?.["failure"]
					? `failed: ${outputRecord["failure"]}`
					: outputRecord?.["name"]
						? `${capabilityKind} "${outputRecord["name"]}"`
						: outputRecord?.["fact"]
							? `${outputRecord["scope"]}: ${outputRecord["fact"]}`
							: decision.target;
				return `${i + 1}. ${event.id} [${decision.target}] ${preview}`;
			});
			return { output: lines.join("\n") };
		}

		if (action === "approve") {
			if (!id) {
				return { output: "approve requires an id.", isError: true };
			}
			const pending = await processor.listPending();
			const candidate = pending.find((entry) => entry.event.id === id);
			if (candidate?.decision.target === "capability_gap") {
				return {
					output:
						"Executable capability approval requires the external validation/user approval surface. The proposal remains pending; do not replace it with a prompt skill.",
					isError: true,
				};
			}
			const result = await processor.approvePending(id);
			if (!result.resolved) {
				return { output: `Could not approve: ${result.reason}`, isError: true };
			}
			const detail = result["name"] ? ` "${result["name"]}"` : "";
			return { output: `Approved ${id}${detail}.` };
		}

		if (action === "reject") {
			if (!id) {
				return { output: "reject requires an id.", isError: true };
			}
			const result = await processor.rejectPending(id);
			if (!result.resolved) {
				return { output: `Could not reject: ${result.reason}`, isError: true };
			}
			return { output: `Rejected ${id}.` };
		}

		if (action === "clear") {
			await processor.clearPending();
			return { output: "Cleared all pending learning outputs." };
		}

		return { output: "Unknown action", isError: true };
	},
};
