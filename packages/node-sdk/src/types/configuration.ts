/** Stable client DTO. It deliberately mirrors validated values, never ConfigService internals. */
export interface Configuration {
	readonly model: Readonly<Record<string, unknown>>;
	readonly permission: Readonly<Record<string, unknown>>;
	readonly interaction: Readonly<Record<string, unknown>>;
	readonly shell: Readonly<Record<string, unknown>>;
	readonly mcp: Readonly<Record<string, unknown>>;
	readonly telemetry: Readonly<Record<string, unknown>>;
	readonly memory: Readonly<Record<string, unknown>>;
	readonly learning: Readonly<Record<string, unknown>>;
	readonly agentGraph: Readonly<Record<string, unknown>>;
	readonly hooks: readonly unknown[];
}
export type ConfigurationPatch = Readonly<Record<string, unknown>>;
export type ConfigurationScope = "user" | "project";
