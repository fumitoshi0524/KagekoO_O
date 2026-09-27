import type { PromptPart } from "@kageko/protocol";
export type { PromptPart } from "@kageko/protocol";
export interface PromptInput {
	readonly parts: readonly PromptPart[];
	readonly turnId?: string;
}
export interface PromptHandle {
	readonly turnId: string;
	readonly completion: Promise<void>;
	cancel(): void;
}
