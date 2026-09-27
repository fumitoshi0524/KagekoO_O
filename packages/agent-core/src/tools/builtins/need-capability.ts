import { createCapabilityGapEvent, type RequiredCapabilityContract } from "../../memory/learning/event.js";
import type { Tool, ToolContext } from "../types.js";

interface NeedCapabilityArgs {
	description: string;
	context?: string;
	proposedKind?: "tool" | "mcp";
	requiredContracts?: Array<{
		name?: string;
		inputSchema?: Record<string, unknown>;
		/** Accepted as an alias for inputSchema, mirroring the marker parser. */
		input_schema?: Record<string, unknown>;
	}>;
	evidence: {
		scope: "workflow" | "local_operation" | "external_service";
		futureTasks: string[];
		alternativesChecked: string[];
	};
}

export const needCapabilityTool: Tool<NeedCapabilityArgs> = {
	name: "need_capability",
	description:
		"Tell Kageko about a capability you need that it does not currently have. This feeds the learning pipeline so it can design a persistent tool or MCP server.",
	parameters: {
		type: "object",
		properties: {
			description: { type: "string", description: "What do you need the agent to be able to do?" },
			context: { type: "string", description: "Optional context, e.g. file types, apps, or workflows involved" },
			proposedKind: {
				type: "string",
				enum: ["tool", "mcp"],
				description: "Whether you think this should be a local tool or an MCP server",
			},
			requiredContracts: {
				type: "array",
				description:
					"Exact public tool contracts the capability must expose. When present, these names and input schemas are authoritative and outrank any free-text contract marker in the conversation.",
				items: {
					type: "object",
					properties: {
						name: { type: "string", description: "Exact public tool name" },
						inputSchema: { type: "object", description: "Exact JSON Schema for the tool input" },
						input_schema: { type: "object", description: "Alias for inputSchema" },
					},
					required: ["name"],
				},
			},
			evidence: {
				type: "object",
				description: "Evidence that this is a coherent reusable capability, not a one-off helper.",
				properties: {
					scope: { type: "string", enum: ["workflow", "local_operation", "external_service"] },
					futureTasks: { type: "array", items: { type: "string" }, minItems: 2 },
					alternativesChecked: { type: "array", items: { type: "string" }, minItems: 1 },
				},
				required: ["scope", "futureTasks", "alternativesChecked"],
			},
		},
		required: ["description", "evidence"],
	},
	async execute(
		{ description, context = "", proposedKind, requiredContracts, evidence }: NeedCapabilityArgs,
		{ session }: ToolContext,
	) {
		if (!description || description.length < 4) {
			return { output: "Please provide a meaningful description.", isError: true };
		}
		if (!evidence || evidence.futureTasks.length < 2 || evidence.alternativesChecked.length === 0) {
			return { output: "Persistent capabilities require reuse evidence and checked alternatives.", isError: true };
		}
		const contracts = normalizeRequiredContracts(requiredContracts);
		// An empty normalized result deliberately falls back to the free-text
		// marker path in the synthesizer: a schema slip in the tool call must not
		// silently lose the capability-gap signal.
		session?.learningBus?.enqueue(
			createCapabilityGapEvent(
				{
					description,
					context,
					proposedKind,
					...(contracts.length > 0 ? { requiredContracts: contracts } : {}),
					evidence,
				},
				{ toolName: "need_capability" },
			),
		);
		return {
			output: `Recorded capability need: ${description}\nThe resident learner is processing it; use review_pending list before creating a substitute capability.`,
		};
	},
};

export function normalizeRequiredContracts(
	contracts: NeedCapabilityArgs["requiredContracts"],
): RequiredCapabilityContract[] {
	if (!Array.isArray(contracts)) return [];
	return contracts.flatMap((value): RequiredCapabilityContract[] => {
		if (!value || typeof value !== "object") return [];
		const inputSchema = value.inputSchema ?? value.input_schema;
		if (
			typeof value.name !== "string" ||
			!value.name.trim() ||
			!inputSchema ||
			typeof inputSchema !== "object" ||
			Array.isArray(inputSchema)
		)
			return [];
		return [{ name: value.name, inputSchema }];
	});
}
