/**
 * Normalize a supported configuration document without guessing removed
 * permission semantics. Legacy permission shortcuts remain rejected by the
 * canonical loader.
 */
export function migrateConfigDocument(input: Record<string, unknown>): Record<string, unknown> {
	const output = structuredClone(input);
	const permission = output["permission"];
	if (permission && typeof permission === "object" && !Array.isArray(permission)) {
		const record = permission as Record<string, unknown>;
		if (Object.hasOwn(record, "defaultMode")) {
			throw new Error(
				"Legacy permission.defaultMode is unsupported; use permission.defaultProfile and interaction.defaultMode",
			);
		}
	}
	return output;
}
