import type { Tool, ToolContext } from "../types.js";

export const cronListTool: Tool = {
	name: "cron_list",
	description: "List scheduled cron prompt jobs.",
	parameters: {
		type: "object",
		properties: {},
	},
	execute(_args: Record<string, unknown>, { session }: ToolContext) {
		if (!session?.cron) {
			return { output: "Cron manager is not available.", isError: true };
		}
		const jobs = session.cron.list();
		return { output: JSON.stringify(jobs) };
	},
};
