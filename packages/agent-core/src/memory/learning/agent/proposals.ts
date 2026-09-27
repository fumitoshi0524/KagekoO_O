import { sanitizeSkillName, validateSkillQuality } from "../../skill-synthesizer.js";
import { validateCapabilityCandidate } from "../../capability-synthesizer.js";
import { tokenize } from "../../utils.js";
import type { CapabilityManifest, SynthesizedSkill } from "../../types.js";
import type { RequiredCapabilityContract } from "../event.js";
import type { CapabilityOutput } from "../learners/capability-gap.js";

export const DEFAULT_SKILL_SIMILARITY_THRESHOLD: number = 0.85;
// Learner-produced procedures are intentionally domain-neutral and share
// contract/identifier/recovery language, so their paraphrases have much lower
// lexical overlap than copied skills. Keep the relaxed threshold scoped to
// auto outputs; user, project, and plugin skills retain the conservative
// caller-configured threshold above.
const AUTO_GENERATED_SIMILARITY_THRESHOLD = 0.3;
const AUTO_GENERATED_CONTAINMENT_THRESHOLD = 0.4;

/**
 * The skill fields the similarity/dedupe check reads. A loaded skill carries
 * `content` (the SKILL.md body) and `source`; a bare inventory item may only
 * have `description`, which then stands in for the body.
 */
export interface ExistingSkillSummary {
	name: string;
	description?: string;
	content?: string;
	source?: string;
}

/**
 * Shared skill dedupe rule: exact name equality, then token overlap against
 * each existing skill with a relaxed threshold for auto-generated skills.
 * Used by `SkillLearner` (full loaded skills) and by the learner-agent
 * `propose_skill` tool (inventory summaries).
 */
export function isSimilarToExistingSkills(
	skill: { name: string; instructions: string },
	existing: readonly ExistingSkillSummary[],
	similarityThreshold: number = DEFAULT_SKILL_SIMILARITY_THRESHOLD,
): boolean {
	if (existing.length === 0) return false;

	const normalizedName = skill.name.trim().toLowerCase();
	if (existing.some((candidate) => candidate.name.trim().toLowerCase() === normalizedName)) return true;

	const newTokens = new Set(tokenize(skill.instructions));
	if (newTokens.size === 0) return false;

	for (const candidate of existing) {
		const overlap = tokenOverlap(newTokens, tokenize(candidate.content ?? candidate.description ?? ""));
		const threshold =
			candidate.source === "auto"
				? Math.min(similarityThreshold, AUTO_GENERATED_SIMILARITY_THRESHOLD)
				: similarityThreshold;
		if (
			overlap.jaccard >= threshold ||
			(candidate.source === "auto" && overlap.containment >= AUTO_GENERATED_CONTAINMENT_THRESHOLD)
		)
			return true;
	}
	return false;
}

export type SkillProposalVerdict = { ok: true; skill: SynthesizedSkill } | { ok: false; reason: string };

/**
 * Validate a learner-agent skill proposal: sanitize the name exactly like
 * `SkillSynthesizer`, enforce the same quality bar, and reject proposals that
 * duplicate or paraphrase an existing skill.
 */
export function validateSkillProposal(
	input: { name?: unknown; description?: unknown; instructions?: unknown },
	existingSkills: readonly ExistingSkillSummary[],
	{ similarityThreshold = DEFAULT_SKILL_SIMILARITY_THRESHOLD }: { similarityThreshold?: number } = {},
): SkillProposalVerdict {
	const name = sanitizeSkillName(input.name);
	if (!name) return { ok: false, reason: "the skill name was missing or invalid" };
	const skill: SynthesizedSkill = {
		name,
		description: typeof input.description === "string" ? input.description : "",
		instructions: typeof input.instructions === "string" ? input.instructions : "",
	};
	try {
		validateSkillQuality(skill);
	} catch (error) {
		return { ok: false, reason: error instanceof Error ? error.message : String(error) };
	}
	if (isSimilarToExistingSkills(skill, existingSkills, similarityThreshold)) {
		return { ok: false, reason: "an existing skill already covers this workflow (name or content overlap)" };
	}
	return { ok: true, skill };
}

export interface CapabilityProposalInput {
	kind?: "tool" | "mcp";
	name?: string;
	description?: string;
	parameters?: Record<string, unknown>;
	command?: string;
	args?: string[];
	code?: string;
	requiredContracts?: readonly RequiredCapabilityContract[];
}

export type CapabilityProposalVerdict = { ok: true; output: CapabilityOutput } | { ok: false; reason: string };

/**
 * Validate an inline capability candidate proposed by the learner agent.
 * Runs the identical checks `CapabilitySynthesizer` applies to raw model
 * output: contract-driven kind forcing, exact name/schema equality against
 * required contracts, the arguments placeholder, a parse-only syntax check,
 * and manifest structural validation.
 */
export function validateCapabilityProposal(input: CapabilityProposalInput): CapabilityProposalVerdict {
	const manifest = {
		kind: input.kind,
		name: input.name,
		description: input.description,
		parameters: input.parameters,
		command: input.command,
		args: input.args,
	} as CapabilityManifest;
	const result = validateCapabilityCandidate({ manifest, code: input.code }, input.kind, input.requiredContracts ?? []);
	if (!result.result) {
		return { ok: false, reason: result.issue };
	}
	return { ok: true, output: { ...result.result.manifest, code: result.result.code } };
}

function tokenOverlap(newTokens: Set<string>, existingTokens: string[]): { jaccard: number; containment: number } {
	const existingSet = new Set(existingTokens);
	if (existingSet.size === 0 || newTokens.size === 0) return { jaccard: 0, containment: 0 };

	let intersection = 0;
	for (const token of newTokens) {
		if (existingSet.has(token)) intersection++;
	}
	return {
		jaccard: intersection / (newTokens.size + existingSet.size - intersection),
		containment: intersection / Math.min(newTokens.size, existingSet.size),
	};
}
