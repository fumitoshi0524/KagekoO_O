/** A model returned by a provider's live catalog or OAuth fallback catalog. */
export interface DiscoveredModel {
	readonly id: string;
	readonly name?: string;
	readonly contextLength?: number;
	/** Maximum provider-reported context ceiling, separate from contextLength. */
	readonly contextLimit?: number;
	readonly capabilities?: readonly string[];
	readonly maxOutputTokens?: number;
	readonly reasoningConfig?: Readonly<Record<string, unknown>>;
	readonly reasoningLevels?: readonly string[];
	readonly provenance?: ModelMetadataProvenance;
	readonly metadataSource?: ModelMetadataOrigin;
	readonly contextLengthSource?: ModelMetadataSource;
	readonly capabilitiesSource?: ModelMetadataSource;
	readonly maxContextSizeSource?: ModelMetadataSource;
	readonly maxOutputTokensSource?: ModelMetadataSource;
}

export type ModelMetadataSource = "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
export interface ModelMetadataProvenance {
	readonly contextLength: ModelMetadataSource;
	readonly capabilities: ModelMetadataSource;
	readonly maxContextSize: ModelMetadataSource;
	readonly maxOutputTokens: ModelMetadataSource;
}

export interface ModelMetadataOrigin {
	readonly kind: "provider" | "catalog";
	readonly providerId: string;
	readonly endpoint?: string;
	readonly authMode?: ModelAuthMode;
	readonly source?: "provider-live" | "public-catalog" | "local-cache" | "static-fallback";
	readonly authoritative?: boolean;
}

export type ModelAuthMode = "api" | "oauth";

export interface ModelRoute {
	readonly provider?: string;
	readonly modelName?: string;
	readonly contextLength?: number;
	readonly capabilities?: readonly string[];
	readonly maxContextSize?: number;
	readonly maxOutputTokens?: number;
	readonly reasoningConfig?: Readonly<Record<string, unknown>>;
	readonly baseUrl?: string;
	readonly authMode?: ModelAuthMode;
	readonly provenance?: ModelMetadataProvenance;
	readonly metadataSource?: ModelMetadataOrigin;
	readonly contextLengthSource?: ModelMetadataSource;
	readonly capabilitiesSource?: ModelMetadataSource;
	readonly maxContextSizeSource?: ModelMetadataSource;
	readonly maxOutputTokensSource?: ModelMetadataSource;
}

export interface ModelSwitchInput {
	readonly provider: string;
	readonly modelName: string;
	/** Provider-live result selected immediately before applying this route. */
	readonly discoveredModel?: DiscoveredModel;
	readonly maxContextSize?: number;
	readonly maxOutputTokens?: number;
	readonly reasoningConfig?: Readonly<Record<string, unknown>>;
	readonly baseUrl?: string;
	readonly authMode?: ModelAuthMode;
	/** Session keeps the route in the active runtime and never writes config. */
	readonly scope?: "user" | "project" | "session";
	readonly sessionId?: string;
}

export interface OAuthLoginResult {
	readonly providerId: string;
	readonly authenticated: true;
	readonly authMode: "oauth";
}

/**
 * Ephemeral host callbacks for an interactive OAuth run. These deliberately
 * never become credential data or persisted configuration. The current SDK
 * transports are in-process; a future remote transport must expose the same
 * interaction as a serializable session protocol rather than silently drop it.
 */
export type OAuthLoginEvent =
	| { readonly type: "auth_url"; readonly url: string; readonly instructions?: string; readonly openBrowser?: boolean }
	| {
			readonly type: "device_code";
			readonly userCode: string;
			readonly verificationUri: string;
			readonly intervalSeconds?: number;
			readonly expiresInSeconds?: number;
			readonly openBrowser?: boolean;
	  }
	| { readonly type: "progress"; readonly message: string };

export interface OAuthPrompt {
	readonly type?: string;
	readonly message: string;
	readonly options?: readonly { readonly id: string; readonly label: string; readonly description?: string }[];
	readonly placeholder?: string;
}

export interface OAuthLoginCallbacks {
	readonly signal?: AbortSignal;
	notify?(event: OAuthLoginEvent): void;
	prompt?(prompt: OAuthPrompt): Promise<string | undefined>;
}
