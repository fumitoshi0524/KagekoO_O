import type { ProfileMemory } from "../../profile-memory.js";
import type { ProfileScope } from "../../types.js";
import type { LearningEvent } from "../event.js";
import type { Learner, TriageDecision } from "../types.js";

export interface UserFeedbackLearnerOptions {
	profileMemory: ProfileMemory;
}

export interface FeedbackOutput {
	scope: ProfileScope | string;
	fact: string;
	pending?: boolean;
}

/**
 * Learns from explicit or inferred user feedback.
 */
export class UserFeedbackLearner implements Learner {
	private readonly profileMemory: ProfileMemory;

	constructor({ profileMemory }: UserFeedbackLearnerOptions) {
		this.profileMemory = profileMemory;
	}

	async handle(event: LearningEvent, decision: TriageDecision): Promise<FeedbackOutput | undefined> {
		const { kind } = event.payload as { kind?: string };
		switch (kind) {
			case "remember": {
				const { scope = "user", fact } = event.payload as { scope?: string; fact?: string };
				if (!fact) return undefined;
				await this.profileMemory.remember(scope, fact);
				return { scope, fact };
			}
			case "deny": {
				const { toolName, reason } = event.payload as { toolName?: string; reason?: string };
				// Fields may be missing on hand-rolled events; never record
				// "User denied undefined".
				const deniedTool = toolName ?? "unknown tool";
				const fact = reason ? `User denied ${deniedTool}: ${reason}` : `User denied ${deniedTool}`;
				await this.profileMemory.remember("user", fact);
				return { scope: "user", fact };
			}
			case "correction": {
				const { original, corrected, context } = event.payload as {
					original?: string;
					corrected?: string;
					context?: string;
				};
				if (!original || !corrected) return undefined;
				// Triage always routes corrections to "pending"; the fact is
				// recorded only when the pending entry is approved.
				const fact = `Correction: "${original}" should be "${corrected}"${context ? ` (${context})` : ""}`;
				return { scope: "project", fact, pending: decision.action === "pending" };
			}
			case "preference": {
				const { topic, preference } = event.payload as { topic?: string; preference?: string };
				if (!preference) return undefined;
				// Triage always routes preferences to "pending"; same as above.
				const fact = `Preference (${topic ?? "general"}): ${preference}`;
				return { scope: "user", fact, pending: decision.action === "pending" };
			}
			default:
				return undefined;
		}
	}

	async approve(output: unknown): Promise<{ scope: ProfileScope | string; fact: string }> {
		const o = output as FeedbackOutput | undefined;
		if (!o || !o.fact) {
			throw new Error("Invalid feedback output");
		}
		const scope = o.scope ?? "user";
		await this.profileMemory.remember(scope, o.fact);
		return { scope, fact: o.fact };
	}
}
