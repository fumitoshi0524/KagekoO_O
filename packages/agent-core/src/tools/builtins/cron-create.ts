import type { Tool, ToolContext } from "../types.js";

interface CronCreateArgs {
	cron: string;
	prompt: string;
	recurring?: boolean;
}

export const cronCreateTool: Tool<CronCreateArgs> = {
	name: "cron_create",
	description: "Schedule a recurring prompt to be enqueued for the agent at a later time.",
	parameters: {
		type: "object",
		properties: {
			cron: { type: "string", description: "Cron expression" },
			prompt: { type: "string", description: "Prompt text to enqueue" },
			recurring: {
				type: "boolean",
				description: "Whether the job should repeat (defaults to true)",
			},
		},
		required: ["cron", "prompt"],
	},
	async execute(args: CronCreateArgs, { session }: ToolContext) {
		if (!session?.cron) {
			return { output: "Cron manager is not available.", isError: true };
		}
		try {
			const result = session.cron.create(args);
			await session.cron.flushPersist();
			return {
				output: `Scheduled cron job ${result.id} (${result.humanSchedule}).`,
				id: result.id,
				cron: result.cron,
				humanSchedule: result.humanSchedule,
				recurring: result.recurring,
				nextFireAt: result.nextFireAt,
			};
		} catch (err) {
			return { output: String(err), isError: true };
		}
	},
};
