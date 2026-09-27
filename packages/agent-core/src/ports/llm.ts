export interface LlmPort {
	complete(input: unknown): Promise<unknown>;
}

export interface LlmContentPart {
	type: string;
	text?: string;
	image_url?: { url: string };
	thinking?: string;
	thinkingSignature?: string;
}
export interface LlmToolCall {
	id: string;
	name: string;
	arguments: Record<string, unknown>;
}
export interface ChatMessage {
	role: "system" | "user" | "assistant" | "tool";
	content: string | LlmContentPart[];
	toolCalls?: LlmToolCall[];
	toolCallId?: string;
	isError?: boolean;
}
export interface ChatTool {
	function: { name: string; description: string; parameters: Record<string, unknown> };
}
export interface ChatOptions {
	messages: ChatMessage[];
	tools?: ChatTool[];
	onTextDelta?: (delta: string) => void;
	onThinkingDelta?: (delta: string) => void;
	onToolCallDelta?: (delta: { id: string; name: string; argumentsPartial: string }) => void;
	signal?: AbortSignal;
}
export interface ChatResponse {
	toolCalls: LlmToolCall[];
	content: string;
	finishReason: string;
	usage: { promptTokens: number; completionTokens: number };
}
