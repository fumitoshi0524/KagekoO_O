import type { ModelMetadataOrigin, ModelMetadataProvenance, ModelMetadataSource } from "./types.js";

export interface ParsedLiveModel {
	readonly id: string;
	readonly name?: string;
	readonly contextLength?: number;
	readonly contextLimit?: number;
	readonly maxOutputTokens?: number;
	readonly reasoningLevels?: readonly string[];
	readonly capabilities?: string[];
	readonly present: ReadonlySet<
		"contextLength" | "contextLimit" | "maxOutputTokens" | "reasoningLevels" | "capabilities"
	>;
}

/**
 * Provider model endpoints are not uniform.  This parser deliberately reads
 * only known metadata keys, including their common nested forms, so a usage
 * counter or an arbitrary `max_tokens` field cannot be mistaken for a model
 * context window.
 */
export function parseLiveModelCatalog(payload: unknown): ParsedLiveModel[] {
	const records = catalogRecords(payload);
	const result: ParsedLiveModel[] = [];
	for (const record of records) {
		const id = firstString(record, ["id", "model_id", "modelId", "slug", "model", "name"]);
		if (!id) continue;
		const contextLength = firstPositiveNumber(record, [
			"context_length",
			"contextLength",
			"context_window",
			"contextWindow",
			"context_size",
			"max_context_length",
			"maxContextLength",
			"inputTokenLimit",
			"input_token_limit",
			"contextTokenLimit",
			"context_token_limit",
			"context",
		]);
		const contextLimit = firstPositiveNumber(record, [
			"max_context_window",
			"maxContextWindow",
			"max_context_size",
			"maxContextSize",
			"context_limit",
			"contextLimit",
		]);
		const maxOutputTokens = firstPositiveNumber(record, [
			"max_output_tokens",
			"maxOutputTokens",
			"output_token_limit",
			"outputTokenLimit",
			"max_completion_tokens",
			"maxCompletionTokens",
			"outputLimit",
			"output_limit",
			"output",
		]);
		const capabilities = extractCapabilities(record);
		const reasoningLevels = extractReasoningLevels(record);
		const present = new Set<
			"contextLength" | "contextLimit" | "maxOutputTokens" | "reasoningLevels" | "capabilities"
		>();
		if (contextLength !== undefined) present.add("contextLength");
		if (contextLimit !== undefined) present.add("contextLimit");
		if (maxOutputTokens !== undefined) present.add("maxOutputTokens");
		if (reasoningLevels !== undefined) present.add("reasoningLevels");
		if (capabilities !== undefined) present.add("capabilities");
		const name = firstString(record, ["display_name", "displayName", "label", "name"]);
		result.push({
			id,
			...(name === undefined ? {} : { name }),
			...(contextLength === undefined ? {} : { contextLength }),
			...(contextLimit === undefined ? {} : { contextLimit }),
			...(maxOutputTokens === undefined ? {} : { maxOutputTokens }),
			...(reasoningLevels === undefined ? {} : { reasoningLevels }),
			...(capabilities === undefined ? {} : { capabilities }),
			present,
		});
	}
	return result;
}

export function provenanceForLiveModel(model: ParsedLiveModel): ModelMetadataProvenance {
	const source = (field: "contextLength" | "maxOutputTokens" | "capabilities"): ModelMetadataSource =>
		model.present.has(field) ? "authoritative" : "unknown";
	return {
		contextLength: source("contextLength"),
		capabilities: source("capabilities"),
		maxContextSize: model.present.has("contextLimit") ? "authoritative" : "unknown",
		maxOutputTokens: source("maxOutputTokens"),
	};
}

export function unknownProvenance(): ModelMetadataProvenance {
	return { contextLength: "unknown", capabilities: "unknown", maxContextSize: "unknown", maxOutputTokens: "unknown" };
}

export function providerOrigin(providerId: string, endpoint: string, authMode: "api" | "oauth"): ModelMetadataOrigin {
	return { kind: "provider", providerId, endpoint, authMode, source: "provider-live", authoritative: true };
}

export function catalogOrigin(
	providerId: string,
	authMode: "api" | "oauth",
	source: "public-catalog" | "local-cache" | "static-fallback" = "public-catalog",
): ModelMetadataOrigin {
	return { kind: "catalog", providerId, authMode, source, authoritative: false };
}

function catalogRecords(payload: unknown): Record<string, unknown>[] {
	if (Array.isArray(payload)) return payload.filter(isRecord);
	if (!isRecord(payload)) return [];
	for (const key of ["data", "models", "items", "result", "model_list", "modelList"]) {
		const value = payload[key];
		if (Array.isArray(value)) return value.filter(isRecord);
		if (isRecord(value)) {
			const nested = catalogRecords(value);
			if (nested.length > 0) return nested;
		}
	}
	// Some catalog APIs return an object keyed by model id.
	if (Object.values(payload).some(isRecord)) {
		return Object.entries(payload).flatMap(([key, value]) => (isRecord(value) ? [{ id: key, ...value }] : []));
	}
	return [payload];
}

function extractCapabilities(record: Record<string, unknown>): string[] | undefined {
	for (const key of [
		"capabilities",
		"capability",
		"features",
		"supported",
		"supported_capabilities",
		"supportedCapabilities",
	]) {
		const value = record[key];
		if (Array.isArray(value)) return value.filter((item): item is string => typeof item === "string");
		if (isRecord(value)) {
			const objectFlags = ["tools", "tool_use", "vision", "reasoning", "structured_output"]
				.filter((name) => value[name] === true)
				.map((name) => (name === "tool_use" ? "tools" : name));
			if (objectFlags.length > 0) return [...new Set(objectFlags)];
			const nested = extractCapabilities(value);
			if (nested !== undefined) return nested;
		}
	}
	const modalities = record["modalities"];
	if (isRecord(modalities)) {
		const values = [modalities["input"], modalities["output"]].flatMap((value) => (Array.isArray(value) ? value : []));
		if (values.length > 0) return values.filter((item): item is string => typeof item === "string");
	}
	const methods = record["supportedGenerationMethods"] ?? record["supported_generation_methods"];
	const result = Array.isArray(methods) ? methods.filter((item): item is string => typeof item === "string") : [];
	const inputModalities = record["input_modalities"] ?? record["inputModalities"];
	if (
		Array.isArray(inputModalities) &&
		inputModalities.some((value) => typeof value === "string" && /image|vision/i.test(value))
	)
		result.push("vision");
	const experimentalTools = record["experimental_supported_tools"] ?? record["experimentalSupportedTools"];
	if (Array.isArray(experimentalTools) && experimentalTools.length > 0) result.push("tools");
	if (extractReasoningLevels(record) !== undefined) result.push("reasoning");
	if (record["supports_search_tool"] === true || record["supportsSearchTool"] === true) result.push("web");
	if (
		(typeof record["web_search_tool_type"] === "string" && record["web_search_tool_type"].trim().length > 0) ||
		(typeof record["webSearchToolType"] === "string" && record["webSearchToolType"].trim().length > 0)
	)
		result.push("web");
	const flags: Array<[string, string[]]> = [
		["tool_call", ["tools"]],
		["toolCall", ["tools"]],
		["tool_use", ["tools"]],
		["toolUse", ["tools"]],
		["supports_tools", ["tools"]],
		["supportsTools", ["tools"]],
		["vision", ["vision"]],
		["supports_vision", ["vision"]],
		["supportsVision", ["vision"]],
		["supports_image_in", ["vision"]],
		["supportsImageIn", ["vision"]],
		["supports_video_in", ["video"]],
		["supportsVideoIn", ["video"]],
		["supports_tool_use", ["tools"]],
		["supportsToolUse", ["tools"]],
		["reasoning", ["reasoning"]],
		["supports_reasoning", ["reasoning"]],
		["supportsReasoning", ["reasoning"]],
	];
	for (const [key, values] of flags) if (record[key] === true) result.push(...values);
	const parameters = record["supported_parameters"] ?? record["supportedParameters"];
	if (Array.isArray(parameters)) {
		if (parameters.some((value) => typeof value === "string" && /tool|function/i.test(value))) result.push("tools");
		if (parameters.some((value) => typeof value === "string" && /reason/i.test(value))) result.push("reasoning");
	}
	return result.length > 0 ? [...new Set(result)] : undefined;
}

function extractReasoningLevels(record: Record<string, unknown>): string[] | undefined {
	const value = findKey(record, "supported_reasoning_levels") ?? findKey(record, "supportedReasoningLevels");
	const thinkEfforts = record["think_efforts"] ?? record["thinkEfforts"];
	const effortRecord = isRecord(thinkEfforts) && thinkEfforts["support"] === true ? thinkEfforts : undefined;
	const levelsValue = Array.isArray(value)
		? value
		: effortRecord && Array.isArray(effortRecord["valid_efforts"])
			? effortRecord["valid_efforts"]
			: undefined;
	if (!levelsValue) return undefined;
	const levels = levelsValue.flatMap((item) => {
		if (typeof item === "string" && item.trim()) return [item.trim()];
		if (isRecord(item) && typeof item["effort"] === "string" && item["effort"].trim()) return [item["effort"].trim()];
		return [];
	});
	return levels.length > 0 ? [...new Set(levels)] : undefined;
}

function firstString(record: Record<string, unknown>, keys: readonly string[]): string | undefined {
	for (const key of keys) {
		const value = findKey(record, key);
		if (typeof value === "string" && value.trim()) return value.trim();
	}
	return undefined;
}

function firstPositiveNumber(record: Record<string, unknown>, keys: readonly string[]): number | undefined {
	for (const key of keys) {
		const value = findKey(record, key);
		if (typeof value === "number" && Number.isFinite(value) && value > 0) return Math.round(value);
		if (typeof value === "string" && /^\d+(?:\.\d+)?$/.test(value.trim())) {
			const parsed = Number(value);
			if (Number.isFinite(parsed) && parsed > 0) return Math.round(parsed);
		}
	}
	return undefined;
}

function findKey(record: Record<string, unknown>, key: string, depth = 0): unknown {
	if (Object.hasOwn(record, key)) return record[key];
	if (depth >= 4) return undefined;
	for (const nestedKey of ["limit", "limits", "architecture", "metadata", "model", "spec", "config", "properties"]) {
		const nested = record[nestedKey];
		if (isRecord(nested)) {
			const value = findKey(nested, key, depth + 1);
			if (value !== undefined) return value;
		}
	}
	return undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}
