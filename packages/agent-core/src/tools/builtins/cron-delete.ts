import type { Tool, ToolContext } from "../types.js";

export const cronDeleteTool: Tool<{ id: string }> = {
	name: "cron_delete",
	description: "Delete a scheduled cron prompt job.",
	parameters: {
		type: "object",
		properties: {
			id: { type: "string", description: "Job id" },
		},
		required: ["id"],
	},
	execute({ id }: { id: string }, { session }: ToolContext) {
		if (!session?.cron) {
			return { output: "Cron manager is not available.", isError: true };
		}
		const removed = session.cron.remove(id);
		return {
			output: removed ? `Deleted cron job ${id}` : `Cron job not found: ${id}`,
			isError: !removed,
		};
	},
};
