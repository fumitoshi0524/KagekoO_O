/**
 * Message anomaly repair projector.
 *
 * Mirrors kimi-code's agent/context/projector.ts. Transforms a raw message
 * history into a wire-valid message list for strict LLM providers.
 */

export const ProjectionAnomaly = {
	TOOL_RESULT_REORDERED: "tool_result_reordered",
	TOOL_RESULT_SYNTHESIZED: "tool_result_synthesized",
	ORPHAN_TOOL_RESULT_DROPPED: "orphan_tool_result_dropped",
	DUPLICATE_TOOL_CALL_DROPPED: "duplicate_tool_call_dropped",
	DUPLICATE_TOOL_RESULT_DROPPED: "duplicate_tool_result_dropped",
	LEADING_NON_USER_DROPPED: "leading_non_user_dropped",
	CONSECUTIVE_ASSISTANTS_MERGED: "consecutive_assistants_merged",
	WHITESPACE_TEXT_DROPPED: "whitespace_text_dropped",
} as const;

export type ProjectionAnomalyKind = (typeof ProjectionAnomaly)[keyof typeof ProjectionAnomaly];

const SYNTHETIC_TOOL_RESULT_TEXT =
	"Tool result is not available in the current context. Do not assume the tool completed successfully.";

export interface ContentPart {
	type: string;
	text?: string;
	[key: string]: unknown;
}

export interface ToolCall {
	id: string;
	name?: string;
	arguments?: unknown;
	[key: string]: unknown;
}

export type MessageContent = string | ContentPart[];

export interface ContextMessage {
	role: string;
	content: MessageContent;
	name?: string;
	toolCalls?: ToolCall[];
	toolCallId?: string;
	isError?: boolean;
	origin?: string;
	[key: string]: unknown;
}

export interface ProjectionAnomalyEvent {
	kind: ProjectionAnomalyKind;
	toolCallId?: string;
	role?: string;
	trailing?: boolean;
}

export interface ProjectOptions {
	synthesizeMissing?: boolean;
	dropOrphanResults?: boolean;
	dropLeadingNonUser?: boolean;
	mergeConsecutiveAssistants?: boolean;
	dedupeDuplicateToolCalls?: boolean;
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void;
}

/**
 * Project a raw message history into a wire-valid message list.
 */
export function project(history: readonly ContextMessage[], options: ProjectOptions = {}): ContextMessage[] {
	let result = mergeAdjacentUserMessages(history, options.onAnomaly);
	if (options.dedupeDuplicateToolCalls === true) {
		result = dedupeDuplicateToolCalls(result, options.onAnomaly);
	}
	result = repairToolExchangeAdjacency(result, options);
	if (options.mergeConsecutiveAssistants === true) {
		result = mergeConsecutiveAssistantMessages(result, options.onAnomaly);
	}
	if (options.dropOrphanResults === true) {
		result = dropOrphanToolResults(result, options.onAnomaly);
	}
	if (options.dropLeadingNonUser === true) {
		result = dropLeadingNonUserMessages(result, options.onAnomaly);
	}
	return deepCloneMessages(result);
}

function deepCloneMessages(messages: ContextMessage[]): ContextMessage[] {
	try {
		return structuredClone(messages);
	} catch {
		try {
			return JSON.parse(JSON.stringify(messages)) as ContextMessage[];
		} catch {
			return messages;
		}
	}
}

function repairToolExchangeAdjacency(messages: ContextMessage[], options: ProjectOptions): ContextMessage[] {
	let lastNonToolIndex = messages.length - 1;
	while (lastNonToolIndex >= 0 && messages[lastNonToolIndex]?.role === "tool") {
		lastNonToolIndex -= 1;
	}

	const out: ContextMessage[] = [];
	const consumed = new Set<number>();
	for (let i = 0; i < messages.length; i++) {
		if (consumed.has(i)) continue;
		const message = messages[i] as ContextMessage;
		if (message.role !== "assistant" || !message.toolCalls || message.toolCalls.length === 0) {
			out.push(message);
			continue;
		}

		out.push(message);
		const pending = new Set(message.toolCalls.map((toolCall) => toolCall.id));
		let foreignBetween = false;
		for (let j = i + 1; j < messages.length && pending.size > 0; j++) {
			if (consumed.has(j)) continue;
			const next = messages[j] as ContextMessage;
			const toolCallId = next.toolCallId;
			if (next.role === "tool" && toolCallId !== undefined && pending.has(toolCallId)) {
				out.push(next);
				consumed.add(j);
				pending.delete(toolCallId);
				if (foreignBetween) {
					options?.onAnomaly?.({ kind: ProjectionAnomaly.TOOL_RESULT_REORDERED, toolCallId });
				}
			} else {
				foreignBetween = true;
			}
		}

		const isMidHistory = i < lastNonToolIndex;
		if (options?.synthesizeMissing === true || isMidHistory) {
			for (const missingId of pending) {
				out.push(makeSyntheticToolResult(missingId));
				options?.onAnomaly?.({
					kind: ProjectionAnomaly.TOOL_RESULT_SYNTHESIZED,
					toolCallId: missingId,
					trailing: !isMidHistory,
				});
			}
		}
	}
	return out;
}

function dedupeDuplicateToolCalls(
	messages: ContextMessage[],
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage[] {
	const seenToolCallIds = new Set<string>();
	const seenToolResultIds = new Set<string>();
	const out: ContextMessage[] = [];
	for (const message of messages) {
		if (message.role === "assistant" && message.toolCalls && message.toolCalls.length > 0) {
			const kept = message.toolCalls.filter((toolCall) => {
				if (seenToolCallIds.has(toolCall.id)) {
					onAnomaly?.({ kind: ProjectionAnomaly.DUPLICATE_TOOL_CALL_DROPPED, toolCallId: toolCall.id });
					return false;
				}
				seenToolCallIds.add(toolCall.id);
				return true;
			});
			if (kept.length === message.toolCalls.length) {
				out.push(message);
			} else if (kept.length > 0 || hasContent(message)) {
				out.push({ ...message, toolCalls: kept });
			}
			continue;
		}
		if (message.role === "tool" && message.toolCallId !== undefined) {
			if (seenToolResultIds.has(message.toolCallId)) {
				onAnomaly?.({ kind: ProjectionAnomaly.DUPLICATE_TOOL_RESULT_DROPPED, toolCallId: message.toolCallId });
				continue;
			}
			seenToolResultIds.add(message.toolCallId);
		}
		out.push(message);
	}
	return out;
}

function dropOrphanToolResults(
	messages: ContextMessage[],
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage[] {
	const toolUseIds = new Set<string>();
	for (const message of messages) {
		if (message.role === "assistant" && message.toolCalls) {
			for (const toolCall of message.toolCalls) {
				toolUseIds.add(toolCall.id);
			}
		}
	}
	return messages.filter((message) => {
		if (message.role !== "tool" || message.toolCallId === undefined) return true;
		if (toolUseIds.has(message.toolCallId)) return true;
		onAnomaly?.({ kind: ProjectionAnomaly.ORPHAN_TOOL_RESULT_DROPPED, toolCallId: message.toolCallId });
		return false;
	});
}

function mergeConsecutiveAssistantMessages(
	messages: ContextMessage[],
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage[] {
	const out: ContextMessage[] = [];
	for (const message of messages) {
		const previous = out.at(-1);
		if (previous && previous.role === "assistant" && message.role === "assistant") {
			out[out.length - 1] = {
				...previous,
				content: mergeText(previous.content, message.content),
				toolCalls: [...(previous.toolCalls || []), ...(message.toolCalls || [])],
			};
			onAnomaly?.({ kind: ProjectionAnomaly.CONSECUTIVE_ASSISTANTS_MERGED });
			continue;
		}
		out.push(message);
	}
	return out;
}

function dropLeadingNonUserMessages(
	messages: ContextMessage[],
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage[] {
	let start = 0;
	while (start < messages.length && (messages[start] as ContextMessage).role !== "user") {
		onAnomaly?.({ kind: ProjectionAnomaly.LEADING_NON_USER_DROPPED, role: (messages[start] as ContextMessage).role });
		start += 1;
	}
	return start === 0 ? [...messages] : messages.slice(start);
}

function makeSyntheticToolResult(toolCallId: string): ContextMessage {
	return {
		role: "tool",
		toolCallId,
		content: SYNTHETIC_TOOL_RESULT_TEXT,
	};
}

function mergeAdjacentUserMessages(
	history: readonly ContextMessage[],
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage[] {
	const out: ContextMessage[] = [];
	for (const source of history) {
		const message = prepareMessageForProjection(source, onAnomaly);
		if (message === null) continue;

		const previous = out.at(-1);
		if (canMergeUserMessage(message) && previous && canMergeUserMessage(previous)) {
			out[out.length - 1] = mergeTwoUserMessages(previous, message);
			continue;
		}
		out.push(message);
	}
	return out.map(stripContextMetadata);
}

function prepareMessageForProjection(
	message: ContextMessage,
	onAnomaly?: (anomaly: ProjectionAnomalyEvent) => void,
): ContextMessage | null {
	const content = normalizeContent(message.content);
	const isPartArray = Array.isArray(content);
	const hasCalls = Boolean(message.toolCalls && message.toolCalls.length > 0);

	if (typeof content === "string") {
		const isWhitespaceOnly = content.trim().length === 0 && content.length > 0;
		if (isWhitespaceOnly) {
			onAnomaly?.({ kind: ProjectionAnomaly.WHITESPACE_TEXT_DROPPED, role: message.role });
			if (message.role !== "tool" && !hasCalls) {
				return null;
			}
		}
	} else if (isPartArray) {
		const dropped = content.filter(isWhitespaceOnlyTextPart);
		if (dropped.length > 0) {
			onAnomaly?.({ kind: ProjectionAnomaly.WHITESPACE_TEXT_DROPPED, role: message.role });
		}
	}

	const cleanedContent = isPartArray ? dropWhitespaceOnlyTextParts(content) : content;
	const hasTextContent =
		typeof cleanedContent === "string"
			? cleanedContent.length > 0
			: cleanedContent.some((part) => part.type === "text" && typeof part.text === "string" && part.text.length > 0);
	const hasNonTextContent = Array.isArray(cleanedContent) && cleanedContent.some((part) => part.type !== "text");

	const next = cleanedContent === message.content ? message : { ...message, content: cleanedContent };
	if (!hasTextContent && !hasCalls && !hasNonTextContent) {
		return null;
	}
	return next;
}

function canMergeUserMessage(message: ContextMessage): boolean {
	return message.role === "user" && message.origin === "user";
}

function mergeTwoUserMessages(a: ContextMessage, b: ContextMessage): ContextMessage {
	if (typeof a.content === "string" && typeof b.content === "string") {
		return {
			...a,
			content: `${a.content}\n\n${b.content}`,
			toolCalls: [],
		};
	}
	return {
		...a,
		content: mergeText(a.content, b.content),
		toolCalls: [],
	};
}

function normalizeContent(content: unknown): MessageContent {
	if (content === undefined || content === null) return "";
	if (typeof content === "string") return content;
	if (Array.isArray(content)) return content as ContentPart[];
	return String(content);
}

function hasContent(message: ContextMessage): boolean {
	const content = normalizeContent(message.content);
	if (typeof content === "string") return content.length > 0;
	if (Array.isArray(content)) {
		return content.some((part) => part.type !== "text" || (typeof part.text === "string" && part.text.length > 0));
	}
	return false;
}

function mergeText(a: MessageContent, b: MessageContent): MessageContent {
	if (typeof a === "string" && typeof b === "string") {
		if (a.length === 0) return b;
		if (b.length === 0) return a;
		return `${a}\n${b}`;
	}
	const partsA = toContentParts(a);
	const partsB = toContentParts(b);
	return [...partsA, ...partsB];
}

function toContentParts(content: MessageContent): ContentPart[] {
	if (typeof content === "string") {
		return content.length > 0 ? [{ type: "text", text: content }] : [];
	}
	if (Array.isArray(content)) return content;
	return [];
}

function isWhitespaceOnlyTextPart(part: ContentPart): boolean {
	return (
		part?.type === "text" && typeof part.text === "string" && part.text.trim().length === 0 && part.text.length > 0
	);
}

function dropWhitespaceOnlyTextParts(content: ContentPart[]): ContentPart[];
function dropWhitespaceOnlyTextParts(content: MessageContent): MessageContent;
function dropWhitespaceOnlyTextParts(content: MessageContent): MessageContent {
	if (!Array.isArray(content)) return content;
	return content.filter((part) => !isWhitespaceOnlyTextPart(part));
}

function stripContextMetadata(message: ContextMessage): ContextMessage {
	const stripped: ContextMessage = {
		role: message.role,
		content: message.content,
	};
	if (message.name) stripped.name = message.name;
	if (message.toolCalls && message.toolCalls.length > 0)
		stripped.toolCalls = message.toolCalls.map((tc) => ({ ...tc }));
	if (message.toolCallId !== undefined) stripped.toolCallId = message.toolCallId;
	if (message.isError !== undefined) stripped.isError = message.isError;
	return stripped;
}
