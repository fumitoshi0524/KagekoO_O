import type { ToolAccess } from "../../tools/types.js";

/** Accesses eligible for built-in convenience approval without external side effects. */
export function hasOnlyLocallySafeAccesses(accesses: readonly ToolAccess[] | undefined): boolean {
	if (!accesses?.length) return false;
	return accesses.every((access) => {
		switch (access.kind) {
			case "none":
				return true;
			case "file":
				return access.operation === "read" || access.operation === "search";
			case "session":
				return true;
			case "interaction":
				return access.operation === "use";
			case "durable_state":
			case "process":
				return access.operation === "read";
			default:
				return false;
		}
	});
}
