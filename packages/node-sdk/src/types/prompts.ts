export interface PromptPart {
	readonly type: string;
	readonly text?: string;
	readonly path?: string;
	readonly mimeType?: string;
	readonly data?: string;
	readonly image_url?: { readonly url: string };
}
export interface PromptInput {
	readonly parts: readonly PromptPart[];
	/** Caller-assigned turn id propagated to turn events; generated when omitted. */
	readonly turnId?: string;
}
