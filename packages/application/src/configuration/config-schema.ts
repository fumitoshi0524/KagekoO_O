import type { Config } from "./config-loader.js";

/** Public application configuration contract. */
export type RuntimeConfig = Config;

export function validateRuntimeConfig(config: RuntimeConfig): void {
	if (!config || typeof config !== "object") throw new TypeError("Configuration must be an object");
	if (!config.model || typeof config.model.provider !== "string" || config.model.provider.length === 0) {
		throw new Error("Configuration model.provider is required");
	}
	if (!Number.isFinite(config.model.maxContextSize) || config.model.maxContextSize! <= 0) {
		throw new Error("Configuration model.maxContextSize must be greater than zero");
	}
}
