import type { Tool, ToolContext } from "../types.js";

interface AgentProfile {
	id?: string;
	systemPrompt?: string;
	system_prompt?: string;
	model?: string;
	permissionProfile?: "manual" | "workspace" | "unrestricted";
	interactionMode?: "interactive" | "unattended";
	tools?: string[];
	maxSteps?: number;
	max_steps?: number;
}

interface AgentArgs {
	prompt: string;
	system_prompt?: string;
	tools?: string[];
	profile?: AgentProfile;
	resume?: boolean;
	timeoutMs?: number;
}

export const agentTool: Tool<AgentArgs> = {
	name: "agent",
	description:
		"Delegate work to an internal child agent. It has isolated memory and reports its result to the coordinator; it never speaks directly to the end user.",
	parameters: {
		type: "object",
		properties: {
			prompt: {
				type: "string",
				description: "Task prompt for the subagent",
			},
			system_prompt: {
				type: "string",
				description: "Optional system prompt override for the subagent",
			},
			tools: {
				type: "array",
				items: { type: "string" },
				description: "Optional list of tool names to expose to the subagent",
			},
			profile: {
				type: "object",
				description:
					"Optional configured internal worker profile. Pass profile.id to select a declared worker; its declared route and policy are used as-is.",
				additionalProperties: true,
			},
			resume: {
				type: "boolean",
				description:
					"Return a matching prior subagent result from the session journal instead of re-running (default: false)",
			},
			timeoutMs: {
				type: "number",
				description: "Timeout in milliseconds for the subagent run (default: 30 minutes)",
			},
		},
		required: ["prompt"],
	},
	async execute(
		{ prompt, system_prompt, tools, profile, resume, timeoutMs }: AgentArgs,
		{ session, signal, subagentHost }: ToolContext,
	) {
		const host = subagentHost ?? session?.subagentHost;
		if (!host) {
			return { output: "Subagent host is not available.", isError: true };
		}

		const normalizedProfile = normalizeProfile(profile);
		const result = await host.run({
			prompt,
			profile: {
				...normalizedProfile,
				systemPrompt: system_prompt ?? normalizedProfile.systemPrompt,
				tools: tools ?? normalizedProfile.tools,
			},
			resume,
			timeoutMs,
			signal,
		});

		return { output: result.content };
	},
};

function normalizeProfile(profile: AgentProfile | undefined): AgentProfile {
	if (!profile || typeof profile !== "object") {
		return {};
	}
	return {
		id: profile.id,
		systemPrompt: profile.systemPrompt ?? profile.system_prompt,
		model: profile.model,
		permissionProfile: profile.permissionProfile,
		interactionMode: profile.interactionMode,
		tools: profile.tools,
		maxSteps: profile.maxSteps ?? profile.max_steps,
	};
}
