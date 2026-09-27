export type CapabilityKind = "plugin" | "skill" | "mcp";

export interface Capability {
	readonly sessionId: string;
	readonly id: string;
	readonly kind: CapabilityKind;
	readonly description?: string;
	/** Origin of the capability (e.g. the skill's file path) when known. */
	readonly source?: string;
	/** Whether this capability exposes an interactive authentication flow. */
	readonly authSupported?: boolean;
}

/**
 * Application projection of session-scoped extension state. Capability names
 * are not globally unique: two workspaces may legitimately expose the same
 * plugin, skill, or MCP server with different configuration.
 */
export class CapabilityService {
	private readonly values = new Map<string, Map<string, Capability>>();

	register(capability: Capability): void {
		const values = this.values.get(capability.sessionId) ?? new Map<string, Capability>();
		values.set(key(capability.kind, capability.id), capability);
		this.values.set(capability.sessionId, values);
	}

	replace(
		sessionId: string,
		kind: CapabilityKind,
		entries: Iterable<{
			readonly id: string;
			readonly description?: string;
			readonly source?: string;
			readonly authSupported?: boolean;
		}>,
	): void {
		const values = this.values.get(sessionId) ?? new Map<string, Capability>();
		for (const [entryKey, capability] of values) {
			if (capability.kind === kind) values.delete(entryKey);
		}
		for (const { id, description, source, authSupported } of entries)
			values.set(key(kind, id), {
				sessionId,
				id,
				kind,
				...(description === undefined ? {} : { description }),
				...(source === undefined ? {} : { source }),
				...(authSupported === undefined ? {} : { authSupported }),
			});
		if (values.size) this.values.set(sessionId, values);
		else this.values.delete(sessionId);
	}

	get(sessionId: string, id: string, kind?: CapabilityKind): Capability | undefined {
		const values = this.values.get(sessionId);
		if (kind) return values?.get(key(kind, id));
		return [...(values?.values() ?? [])].find((value) => value.id === id);
	}

	list(sessionId: string, kind?: CapabilityKind): readonly Capability[] {
		return [...(this.values.get(sessionId)?.values() ?? [])].filter((value) => !kind || value.kind === kind);
	}

	releaseSession(sessionId: string): void {
		this.values.delete(sessionId);
	}
}

function key(kind: CapabilityKind, id: string): string {
	return `${kind}:${id}`;
}
