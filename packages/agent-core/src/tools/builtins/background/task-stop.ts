import type { Tool, ToolContext } from "../../types.js";

export const taskStopTool: Tool<{ task_id: string; reason?: string }> = {
	name: "task_stop",
	description: "Stop a running background task.",
	parameters: {
		type: "object",
		properties: {
			task_id: { type: "string", description: "Task id" },
			reason: { type: "string", description: "Reason recorded for the stop" },
		},
		required: ["task_id"],
	},
	async execute({ task_id, reason }: { task_id: string; reason?: string }, { session }: ToolContext) {
		if (!session?.tracker) {
			return { output: "Process tracker is not available.", isError: true };
		}
		const info = session.tracker.getTask(task_id);
		if (!info) {
			return { output: `Task not found: ${task_id}`, isError: true };
		}
		if (info.status !== "running") {
			return {
				output: `task_id: ${info.taskId}\nstatus: ${info.status}\nreason: Task is not running.`,
			};
		}
		const result = await session.tracker.stop(task_id, reason || "Stopped by task_stop");
		if (!result) {
			return { output: `Task not found after stop: ${task_id}`, isError: true };
		}
		return {
			output: `task_id: ${result.taskId}\nstatus: ${result.status}\nreason: ${result.stopReason}`,
		};
	},
};
