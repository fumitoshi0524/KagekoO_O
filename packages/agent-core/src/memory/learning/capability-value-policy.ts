import { tokenize } from "../utils.js";
import type { CapabilityGapEvidence } from "./event.js";

export interface CapabilityInventoryItem {
	name: string;
	description?: string;
	/** Prompt skills can guide work but cannot satisfy an executable gap. */
	executable?: boolean;
}

export interface CapabilityValueDecision {
	accepted: boolean;
	reason: string;
}

/**
 * Product-level admission rule for generated tools and MCP servers.
 *
 * Correctness is necessary but insufficient: a persistent capability has to
 * cover a reusable task boundary, survive comparison with what is already
 * available, and reduce work for more than the current turn.  This is kept
 * domain-neutral on purpose; it must reject a fragmented release helper just
 * as readily as a fragmented calculator.
 */
export function assessCapabilityValue(
	description: string,
	evidence: CapabilityGapEvidence | undefined,
	inventory: readonly CapabilityInventoryItem[],
): CapabilityValueDecision {
	if (!evidence) return { accepted: false, reason: "missing reuse and alternatives evidence" };
	if (evidence.futureTasks.filter(isMeaningful).length < 2) {
		return { accepted: false, reason: "does not improve at least two future tasks" };
	}
	if (evidence.alternativesChecked.filter(isMeaningful).length === 0) {
		return { accepted: false, reason: "existing alternatives were not checked" };
	}
	const duplicate = inventory.find(
		(item) => item.executable !== false && isSemanticOverlap(description, `${item.name} ${item.description ?? ""}`),
	);
	if (duplicate) {
		return { accepted: false, reason: `overlaps existing capability ${duplicate.name}` };
	}
	return { accepted: true, reason: "reusable capability has positive coverage beyond this task" };
}

export function isSemanticOverlap(left: string, right: string): boolean {
	const a = new Set(tokenize(left).filter((token) => token.length > 2));
	const b = new Set(tokenize(right).filter((token) => token.length > 2));
	if (a.size === 0 || b.size === 0) return false;
	let shared = 0;
	for (const token of a) if (b.has(token)) shared += 1;
	// A short capability name must match completely; longer descriptions need a
	// strong overlap.  The rule is intentionally conservative: it prevents
	// equivalent registrations without pretending keyword similarity is a judge.
	return shared / Math.min(a.size, b.size) >= 0.8;
}

function isMeaningful(value: unknown): value is string {
	return typeof value === "string" && value.trim().length >= 8;
}
