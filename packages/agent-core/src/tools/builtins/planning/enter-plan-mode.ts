import type { Tool, ToolContext } from "../../types.js";

export const enterPlanModeTool: Tool = {
	name: "enter_plan_mode",
	description:
		"Enter plan mode. All subsequent writes must go to the generated plan file until exit_plan_mode is called.",
	parameters: {
		type: "object",
		properties: {},
	},
	async execute(_args: Record<string, unknown>, { session }: ToolContext) {
		if (!session?.planMode) {
			return { output: "Session does not support plan mode", isError: true };
		}
		const planFilePath = await session.planMode.enter();
		return { output: `Entered plan mode. Edit the plan at ${planFilePath}` };
	},
};
