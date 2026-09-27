import { capDescription, validateManifest } from "../../capability-synthesizer.js";
import type { CapabilitySynthesizer } from "../../capability-synthesizer.js";
import type { CapabilityManifest, SessionEvent } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, JournalEventStore } from "../types.js";
import { assessCapabilityValue, isSemanticOverlap, type CapabilityInventoryItem } from "../capability-value-policy.js";
import type { CapabilityGapEvidence, RequiredCapabilityContract } from "../event.js";

/** Bound the dedupe set; oldest fingerprints are evicted past this size. */
const MAX_SEEN_FINGERPRINTS = 500;

export interface CapabilityGapLearnerOptions {
	synthesizer?: CapabilitySynthesizer;
	recordStore?: JournalEventStore;
	/** Runtime inventory used to prevent overlapping persistent capabilities. */
	capabilityInventory?: () => readonly CapabilityInventoryItem[];
	autoApprove?: boolean;
}

export interface CapabilityOutput extends CapabilityManifest {
	code?: string;
	fingerprint?: string;
	filePath?: string;
	status?: "approved" | "pending" | "failed";
	failure?: string;
}

/**
 * Learns from capability gaps and synthesizes persistent tool or MCP manifests.
 */
export class CapabilityGapLearner implements Learner {
	private readonly synthesizer?: CapabilitySynthesizer;
	private readonly recordStore?: JournalEventStore;
	private readonly capabilityInventory?: () => readonly CapabilityInventoryItem[];
	readonly autoApprove: boolean;
	private _seenFingerprints = new Set<string>();
	private _seenRequests = new Map<string, { kind?: "tool" | "mcp"; description: string }>();

	constructor({ synthesizer, recordStore, capabilityInventory, autoApprove = false }: CapabilityGapLearnerOptions) {
		this.synthesizer = synthesizer;
		this.recordStore = recordStore;
		this.capabilityInventory = capabilityInventory;
		this.autoApprove = autoApprove;
	}

	async handle(event: LearningEvent): Promise<CapabilityOutput | undefined> {
		if (!this.synthesizer) return undefined;

		const { description, context, proposedKind, requiredContracts, evidence } = event.payload as {
			description?: string;
			context?: string;
			proposedKind?: "tool" | "mcp";
			requiredContracts?: readonly RequiredCapabilityContract[];
			evidence?: CapabilityGapEvidence;
		};
		if (!description) return undefined;
		// Older embedders may construct this learner without a runtime inventory.
		// The application composition root always provides one; only there do we
		// permit persistence, so normal product use cannot bypass this policy.
		if (this.capabilityInventory) {
			const value = assessCapabilityValue(description, evidence, this.capabilityInventory());
			if (!value.accepted) return undefined;
		}

		const fingerprint = `${proposedKind ?? "any"}:${description}`;
		if (this._seenFingerprints.has(fingerprint)) return undefined;
		if ([...this._seenRequests.values()].some((request) => requestsOverlap(request.description, description)))
			return undefined;

		const recentEvents = this.recordStore ? await this.recordStore.load() : [];
		// DurableEvent is a superset of SessionEvent at runtime; the synthesizer
		// only reads fields common to both types.
		let synthesized;
		try {
			synthesized = await this.synthesizer.synthesize({
				description,
				context,
				proposedKind,
				requiredContracts,
				recentEvents: recentEvents as SessionEvent[],
			});
		} catch (error) {
			// A rejected generation remains auditable and retryable. Persist only a
			// bounded reason, never the raw provider response or user prompt.
			return {
				kind: "none",
				description: capDescription(description),
				fingerprint,
				status: "failed",
				failure: capDescription(error instanceof Error ? error.message : String(error), 2048),
			};
		}
		if (!synthesized) {
			// `kind:none` is a synthesis outcome, not an invisible no-op. Keep it on
			// the same review surface as provider and validation failures so users and
			// unattended harnesses can tell that the learner ran and declined.
			return {
				kind: "none",
				description: capDescription(description),
				fingerprint,
				status: "failed",
				failure: "Capability synthesis returned no safe reusable capability.",
			};
		}

		// Support both the new { manifest, code } shape and the legacy manifest-only shape.
		const s = synthesized as { manifest?: CapabilityManifest; code?: string };
		const { manifest, code } =
			s.manifest && typeof s.manifest === "object"
				? { manifest: s.manifest, code: s.code }
				: { manifest: synthesized as unknown as CapabilityManifest, code: undefined };
		if (!manifest) return undefined;
		manifest.description = capDescription(manifest.description);

		this._rememberFingerprint(fingerprint);
		this._rememberRequest(fingerprint, proposedKind, description);

		if (this.autoApprove) {
			const filePath = await this._writeManifest(manifest, code);
			return { ...manifest, code, filePath, status: "approved" };
		}

		return { ...manifest, code, fingerprint, status: "pending" };
	}

	async approve(output: unknown): Promise<{ name: string; filePath: string }> {
		if (!this.synthesizer) {
			throw new Error("Cannot approve capability: no synthesizer configured.");
		}
		const o = output as CapabilityOutput | undefined;
		if (!o || !o.kind || !o.name) {
			throw new Error("Invalid capability manifest output");
		}
		const manifest: CapabilityManifest = {
			kind: o.kind,
			name: o.name,
			description: o.description,
			parameters: o.parameters,
			command: o.command,
			args: o.args,
		};
		if (!validateManifest(manifest)) {
			throw new Error("Capability manifest failed validation on approve");
		}
		const filePath = await this._writeManifest(manifest, o.code);
		return { name: manifest.name as string, filePath };
	}

	reject(output: unknown): void {
		// A rejected proposal must not suppress an identical future one.
		const fingerprint = (output as CapabilityOutput | undefined)?.fingerprint;
		if (fingerprint) {
			this._seenFingerprints.delete(fingerprint);
			this._seenRequests.delete(fingerprint);
		}
	}

	private _rememberFingerprint(value: string): void {
		this._seenFingerprints.add(value);
		if (this._seenFingerprints.size > MAX_SEEN_FINGERPRINTS) {
			// Set iteration order is insertion order: evict the oldest entry.
			const oldest = this._seenFingerprints.keys().next().value;
			if (oldest !== undefined) this._seenFingerprints.delete(oldest);
		}
	}

	private _rememberRequest(fingerprint: string, kind: "tool" | "mcp" | undefined, description: string): void {
		this._seenRequests.set(fingerprint, { kind, description });
		if (this._seenRequests.size > MAX_SEEN_FINGERPRINTS) {
			const oldest = this._seenRequests.keys().next().value;
			if (oldest !== undefined) this._seenRequests.delete(oldest);
		}
	}

	private async _writeManifest(manifest: CapabilityManifest, code?: string): Promise<string> {
		if (manifest.kind === "tool") {
			return this.synthesizer!.writeToolManifest(manifest, code);
		}
		if (manifest.kind === "mcp") {
			return this.synthesizer!.writeMcpManifest(manifest, code);
		}
		throw new Error(`Unknown manifest kind: ${manifest.kind}`);
	}
}

/**
 * Overlap rule shared by `CapabilityGapLearner` and the learner-agent bridge
 * sink: semantic description overlap, or a shared multi-part identifier.
 */
export function requestsOverlap(left: string, right: string): boolean {
	if (isSemanticOverlap(left, right)) return true;
	const identifiers = new Set(left.toLowerCase().match(/\b[a-z][a-z0-9]*(?:[_-][a-z0-9]+)+\b/g) ?? []);
	return (right.toLowerCase().match(/\b[a-z][a-z0-9]*(?:[_-][a-z0-9]+)+\b/g) ?? []).some((value) =>
		identifiers.has(value),
	);
}
