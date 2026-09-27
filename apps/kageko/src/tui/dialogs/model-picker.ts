import type { DiscoveredModel } from "@kageko/node-sdk";

/**
 * Model-picker policy shared by the route selector and its confirmation view.
 * Provider discovery is authoritative only for the fields it actually returns;
 * an absent field is surfaced as an actionable incomplete-metadata state.
 */
export function filterDiscoveredModels(models: readonly DiscoveredModel[], query: string): readonly DiscoveredModel[] {
	const normalized = query.trim().toLocaleLowerCase();
	if (!normalized) return models;
	return models.filter((model) => `${model.name ?? ""} ${model.id}`.toLocaleLowerCase().includes(normalized));
}

/** Return the exact provider reasoning payload for the highlighted effort. */
export function reasoningConfigForModel(
	model: Pick<DiscoveredModel, "reasoningLevels"> | undefined,
	index: number,
): Record<string, unknown> | undefined {
	const levels = model?.reasoningLevels;
	if (!levels?.length) return undefined;
	const effort = levels[Math.max(0, Math.min(index, levels.length - 1))];
	return effort === undefined ? undefined : { enabled: true, effort };
}

export function metadataOriginLabel(model: Pick<DiscoveredModel, "metadataSource">): string {
	const source = model.metadataSource;
	if (!source) return "discovery source not reported";
	return `${source.source ?? source.kind} · ${source.providerId}`;
}

const METADATA_FIELDS = [
	["context window", "contextLength"],
	["maximum context", "contextLimit"],
	["maximum output", "maxOutputTokens"],
	["capabilities", "capabilities"],
] as const;
const REQUIRED_METADATA_FIELDS = new Set(["contextLength"]);

/**
 * Model review must never imply that missing provider metadata is a usable
 * default. Keep the missing fields structured so the panel can show a clear
 * recovery action instead of a raw `unknown` placeholder.
 */
export function modelMetadataStatus(
	model: Pick<DiscoveredModel, "contextLength" | "contextLimit" | "maxOutputTokens" | "capabilities" | "provenance">,
): {
	readonly complete: boolean;
	readonly missing: readonly string[];
} {
	const provenance = model.provenance;
	const missing = METADATA_FIELDS.flatMap(([label, key]) => {
		if (!REQUIRED_METADATA_FIELDS.has(key)) return [];
		const value = model[key];
		const source =
			provenance?.[
				key === "contextLength"
					? "contextLength"
					: key === "contextLimit"
						? "maxContextSize"
						: key === "maxOutputTokens"
							? "maxOutputTokens"
							: "capabilities"
			];
		const present = key === "capabilities" ? Array.isArray(value) && value.length > 0 : typeof value === "number";
		return present && source !== "unknown" ? [] : [label];
	});
	return { complete: missing.length === 0, missing };
}
