/**
 * The only telemetry surface agent-core is allowed to depend on.
 *
 * Implementations belong to the composition root (for example
 * `@kageko/telemetry`), never to the agent loop.  Keeping this as a port lets
 * embedders choose a collector without making telemetry availability a core
 * runtime concern.
 */
export interface TelemetryEvent {
	type: string;
	[key: string]: unknown;
}

export interface TelemetryClient {
	record(event: TelemetryEvent): void;
	close?(): Promise<void> | void;
}

export const noopTelemetryClient: TelemetryClient = Object.freeze({
	record(): void {},
});
