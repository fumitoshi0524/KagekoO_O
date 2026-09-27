import { capabilityAccess, noAccess } from "../../../tools/accesses.js";
import { normalizeRequiredContracts } from "../../../tools/builtins/need-capability.js";
import type { Tool, ToolResult } from "../../../tools/types.js";
import type { SynthesizeCapabilityInput } from "../../capability-synthesizer.js";
import type { SessionEvent, SynthesizedSkill } from "../../types.js";
import type { CapabilityInventoryItem } from "../capability-value-policy.js";
import type { JournalEventStore } from "../types.js";
import { trimEventsForSynthesis } from "./event-trim.js";
import { validateCapabilityProposal, validateSkillProposal } from "./proposals.js";

export interface SubmitSkillProposalResult {
	accepted: boolean;
	status?: "pending" | "approved";
	reason?: string;
}

export interface SubmitCapabilityProposalResult {
	accepted: boolean;
	status?: "pending" | "approved";
	reason?: string;
	name?: string;
}

export type LearnerProposalKind = "skill" | "tool" | "mcp";

export interface LearnerCapabilityProposal extends SynthesizeCapabilityInput {
	/** Pre-synthesized candidate; when absent the sink runs the full synthesizer. */
	candidate?: {
		kind?: "tool" | "mcp";
		name?: string;
		description?: string;
		parameters?: Record<string, unknown>;
		command?: string;
		args?: string[];
		code?: string;
	};
}

export interface LearnerToolsDeps {
	recordStore: JournalEventStore;
	/** Live capability inventory (tools, skills, MCP servers) for dedupe checks. */
	inventory: () => readonly CapabilityInventoryItem[];
	/**
	 * Read back the error-pattern knowledge written by `ErrorPatternLearner`.
	 * The knowledge store has no tag-filtered read, so the composition root
	 * wires the narrowest available read (e.g. `KnowledgeStore.list()` filtered
	 * to entries tagged `error-pattern`).
	 */
	errorPatterns: () => Promise<unknown> | unknown;
	submitSkillProposal: (skill: SynthesizedSkill) => Promise<SubmitSkillProposalResult>;
	submitCapabilityProposal: (input: LearnerCapabilityProposal) => Promise<SubmitCapabilityProposalResult>;
	/** Restricts the proposal surfaces exposed to the learner. Defaults to all products. */
	proposalKinds?: readonly LearnerProposalKind[];
}

interface ProposeSkillArgs {
	name?: string;
	description?: string;
	instructions?: string;
}

interface ProposeCapabilityArgs {
	description?: string;
	context?: string;
	proposedKind?: "tool" | "mcp";
	requiredContracts?: Array<{
		name?: string;
		inputSchema?: Record<string, unknown>;
		/** Accepted as an alias for inputSchema, mirroring need_capability. */
		input_schema?: Record<string, unknown>;
	}>;
	/** Optional inline candidate fields; supplying any of them switches to candidate mode. */
	name?: string;
	parameters?: Record<string, unknown>;
	command?: string;
	args?: string[];
	code?: string;
}

const LEARNING_QUEUE_ACCESS = () => capabilityAccess("durable_state", "mutate", "learning_queue");

/**
 * The resident learner agent's dedicated tool set. These are plain builtin
 * tools but are NOT part of the main builtin registry; the composition root
 * registers them into a registry scoped to the learner agent only.
 *
 * Proposal rejections are returned as normal (non-error) tool results so the
 * agent can reconsider within its run instead of treating them as failures.
 */
export function createLearnerTools(deps: LearnerToolsDeps): Tool[] {
	const proposalKinds = new Set<LearnerProposalKind>(deps.proposalKinds ?? ["skill", "tool", "mcp"]);
	const capabilityKinds = [...proposalKinds].filter(
		(kind): kind is "tool" | "mcp" => kind === "tool" || kind === "mcp",
	);
	const readRecentEvents: Tool = {
		name: "read_recent_events",
		description:
			"Read the recent session evidence (user prompts, assistant text, tool calls/results, turn boundaries), bounded to the same window skill synthesis uses.",
		parameters: { type: "object", properties: {} },
		resolveExecution: () => ({ accesses: noAccess() }),
		async execute(): Promise<ToolResult> {
			const events = await deps.recordStore.load();
			// DurableEvent is a superset of SessionEvent at runtime; the trim only
			// reads fields common to both types.
			return { output: trimEventsForSynthesis(events as SessionEvent[]) };
		},
	};

	const inspectInventory: Tool = {
		name: "inspect_inventory",
		description: "List the current capability inventory (tools, skills, MCP servers) to avoid proposing duplicates.",
		parameters: { type: "object", properties: {} },
		resolveExecution: () => ({ accesses: noAccess() }),
		execute(): ToolResult {
			return { output: [...deps.inventory()] };
		},
	};

	const readErrorPatterns: Tool = {
		name: "read_error_patterns",
		description: "Read the recurring error patterns the learning pipeline has recorded.",
		parameters: { type: "object", properties: {} },
		resolveExecution: () => ({ accesses: noAccess() }),
		async execute(): Promise<ToolResult> {
			return { output: (await deps.errorPatterns()) ?? [] };
		},
	};

	const proposeSkill: Tool<ProposeSkillArgs> = {
		name: "propose_skill",
		description:
			"Propose a reusable skill learned from the session. The proposal is validated and queued for approval (or auto-approved); rejections are returned as normal results so you can revise.",
		parameters: {
			type: "object",
			properties: {
				name: { type: "string", description: "Short domain-neutral kebab-case skill name" },
				description: { type: "string", description: "One sentence stating when the workflow should be used" },
				instructions: { type: "string", description: "Concise executable instructions for another agent" },
			},
			required: ["name", "description", "instructions"],
		},
		resolveExecution: () => ({ accesses: LEARNING_QUEUE_ACCESS() }),
		async execute({ name, description, instructions }: ProposeSkillArgs): Promise<ToolResult> {
			const verdict = validateSkillProposal({ name, description, instructions }, deps.inventory());
			if (!verdict.ok) {
				return { output: `Skill proposal rejected: ${verdict.reason}` };
			}
			const result = await deps.submitSkillProposal(verdict.skill);
			if (!result.accepted) {
				return { output: `Skill proposal not accepted: ${result.reason ?? "no reason given"}` };
			}
			return { output: `Skill proposal ${result.status ?? "accepted"}: ${verdict.skill.name}` };
		},
	};

	const proposeCapability: Tool<ProposeCapabilityArgs> = {
		name: "propose_capability",
		description:
			"Propose a persistent capability (local tool or MCP server) for a gap the agent cannot cover. Supply an inline candidate (name/parameters/command/args/code) to submit a pre-synthesized manifest, or only the description/context/contracts to let the resident synthesizer generate one.",
		parameters: {
			type: "object",
			properties: {
				description: { type: "string", description: "What the agent needs to be able to do" },
				context: { type: "string", description: "Optional context, e.g. file types, apps, or workflows involved" },
				proposedKind: {
					type: "string",
					enum: capabilityKinds,
					description: "Whether this should be a local tool or an MCP server",
				},
				requiredContracts: {
					type: "array",
					description:
						"Exact public tool contracts the capability must expose. When present, these names and input schemas are authoritative.",
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
				name: { type: "string", description: "Inline candidate: kebab-case manifest name" },
				parameters: { type: "object", description: "Inline candidate: JSON Schema for tool input" },
				command: { type: "string", description: "Inline candidate: command, e.g. node" },
				args: { type: "array", items: { type: "string" }, description: "Inline candidate: command arguments" },
				code: { type: "string", description: "Inline candidate: self-contained Node.js implementation" },
			},
			required: ["description"],
		},
		resolveExecution: () => ({ accesses: LEARNING_QUEUE_ACCESS() }),
		async execute(args: ProposeCapabilityArgs): Promise<ToolResult> {
			const { description, context, proposedKind, name, parameters, command, args: commandArgs, code } = args;
			if (typeof description !== "string" || description.trim().length < 4) {
				return { output: "Capability proposal rejected: a meaningful description is required." };
			}
			if (proposedKind && !capabilityKinds.includes(proposedKind)) {
				return { output: `Capability proposal rejected: ${proposedKind} proposals are disabled.` };
			}
			// Same tolerance as need_capability: input_schema alias, malformed
			// entries dropped. An empty normalized result keeps the free-text
			// marker fallback in the synthesizer.
			const contracts = normalizeRequiredContracts(args.requiredContracts);
			const base: SynthesizeCapabilityInput = {
				description,
				...(context ? { context } : {}),
				...(proposedKind ? { proposedKind } : {}),
				...(contracts.length > 0 ? { requiredContracts: contracts } : {}),
			};

			const hasInlineCandidate =
				name !== undefined ||
				parameters !== undefined ||
				command !== undefined ||
				commandArgs !== undefined ||
				code !== undefined;
			if (hasInlineCandidate) {
				const verdict = validateCapabilityProposal({
					kind: proposedKind,
					name,
					description,
					parameters,
					command,
					args: commandArgs,
					code,
					requiredContracts: contracts,
				});
				if (!verdict.ok) {
					return { output: `Capability proposal rejected: ${verdict.reason}` };
				}
				const candidate = {
					// An ok verdict can never carry kind "none": normalizeCandidate
					// returns { none: true } (no result) for that, which maps to a
					// rejection above.
					kind: verdict.output.kind as "tool" | "mcp",
					name: verdict.output.name,
					description: verdict.output.description,
					parameters: verdict.output.parameters,
					command: verdict.output.command,
					args: verdict.output.args,
					code: verdict.output.code,
				};
				return reportCapabilityResult(await deps.submitCapabilityProposal({ ...base, candidate }));
			}

			// No inline candidate: the sink runs the full CapabilitySynthesizer,
			// preserving its repair rounds and prompt contract.
			return reportCapabilityResult(await deps.submitCapabilityProposal(base));
		},
	};

	return [
		readRecentEvents,
		inspectInventory,
		readErrorPatterns,
		...(proposalKinds.has("skill") ? [proposeSkill] : []),
		...(capabilityKinds.length > 0 ? [proposeCapability] : []),
	];
}

function reportCapabilityResult(result: SubmitCapabilityProposalResult): ToolResult {
	if (!result.accepted) {
		return { output: `Capability proposal not accepted: ${result.reason ?? "no reason given"}` };
	}
	const status = result.status ?? "accepted";
	return { output: `Capability proposal ${status}${result.name ? `: ${result.name}` : ""}` };
}
