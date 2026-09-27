import type { Tool, ToolContext } from "../../types.js";
import type { ProcessTaskInfo } from "../../../ports/process.js";

export const taskListTool: Tool<{ active_only?: boolean; limit?: number }> = {
	name: "task_list",
	description: "List background tasks tracked by the session.",
	parameters: {
		type: "object",
		properties: {
			active_only: { type: "boolean", description: "List only non-terminal tasks (default true)" },
			limit: { type: "number", description: "Maximum number of tasks (default 20)" },
		},
	},
	execute({ active_only = true, limit = 20 }: { active_only?: boolean; limit?: number }, { session }: ToolContext) {
		if (!session?.tracker) {
			return { output: "Process tracker is not available.", isError: true };
		}
		const parsedLimit = Number(limit);
		const safeLimit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(Math.floor(parsedLimit), 1000) : 20;
		const tasks = session.tracker.list(active_only, safeLimit);
		if (tasks.length === 0) {
			return { output: active_only ? "No active background tasks." : "No background tasks." };
		}
		const lines = tasks.map((t: ProcessTaskInfo) =>
			[
				`task_id: ${t.taskId}`,
				`status: ${t.status}`,
				`pid: ${t.pid ?? "?"}`,
				`exitCode: ${t.exitCode ?? "?"}`,
				`startedAt: ${new Date(t.startedAt).toISOString()}`,
				...(t.endedAt === undefined ? [] : [`endedAt: ${new Date(t.endedAt).toISOString()}`]),
				`command: ${t.command}`,
			].join("\n"),
		);
		return { output: lines.join("\n---\n") };
	},
};
