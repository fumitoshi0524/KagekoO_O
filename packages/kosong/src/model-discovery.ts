/** Provider-owned model discovery with explicit provenance. */
import { OPENAI_COMPATIBLE_REGISTRY, type ModelMetadataOrigin, type ModelMetadataProvenance } from "./types.js";
import type { OAuthRequestAuth } from "./credentials.js";
import {
	parseLiveModelCatalog,
	provenanceForLiveModel,
	providerOrigin,
	unknownProvenance,
	type ParsedLiveModel,
} from "./model-metadata.js";
import { canonicalHermesProviderId, resolveHermesApiKey, resolveHermesBaseUrl } from "./provider-parity.js";
import { ProviderError, parseRetryAfter } from "./errors.js";
import { environmentProxyCompatibilityHint, fetchLiveCatalog } from "./live-catalog-fetch.js";

export interface DiscoveredModel {
	id: string;
	name?: string;
	contextLength?: number;
	contextLimit?: number;
	maxOutputTokens?: number;
	reasoningLevels?: readonly string[];
	capabilities?: string[];
	provenance?: ModelMetadataProvenance;
	metadataSource?: ModelMetadataOrigin;
	readonly contextLengthSource?: ModelMetadataProvenance["contextLength"];
	readonly capabilitiesSource?: ModelMetadataProvenance["capabilities"];
	readonly maxContextSizeSource?: ModelMetadataProvenance["maxContextSize"];
	readonly maxOutputTokensSource?: ModelMetadataProvenance["maxOutputTokens"];
}

/** A provider model endpoint did not yield a usable live catalog.  This is
 * intentionally surfaced to the setup UI: a cached, public, or curated list
 * must never make an authenticated route look healthy. */
export class ModelDiscoveryError extends ProviderError {
	constructor(
		providerId: string,
		message: string,
		options: { cause?: unknown; status?: number; retryAfterMs?: number; retryable?: boolean } = {},
	) {
		super(`Model discovery for ${providerId} failed: ${message}`, {
			...options,
			code: "MODEL_DISCOVERY_FAILED",
			retryable: options.retryable ?? true,
		});
		this.name = "ModelDiscoveryError";
	}
}

const NATIVE_DEFAULTS: Record<string, string> = {
	anthropic: "https://api.anthropic.com",
	claude: "https://api.anthropic.com",
	mistral: "https://api.mistral.ai/v1",
	"openai-api": "https://api.openai.com/v1",
};

export async function discoverModels(
	providerId: string,
	options: {
		baseUrl?: string;
		apiKey?: string;
		oauthAuth?: OAuthRequestAuth;
		includeProvenance?: boolean;
		request?: typeof fetch;
		signal?: AbortSignal;
	} = {},
): Promise<DiscoveredModel[]> {
	const normalizedProviderId = canonicalHermesProviderId(providerId);
	// Do not mix a process API key into an OAuth request. Some providers
	// interpret the extra key header as a different auth mode altogether.
	const apiKey = options.oauthAuth ? undefined : (options.apiKey ?? resolveHermesApiKey(normalizedProviderId));
	const authMode: "api" | "oauth" = options.oauthAuth ? "oauth" : "api";
	assertKimiDiscoveryAuth(normalizedProviderId, authMode, apiKey);
	// A configured route (including HERMES_CODEX_BASE_URL) is an explicit
	// operator choice and must win over the endpoint remembered in an imported
	// OAuth credential. Otherwise discovery and inference would hit different
	// hosts, which is especially confusing behind a corporate proxy.
	const configuredBase =
		options.baseUrl ??
		resolveHermesBaseUrl(normalizedProviderId) ??
		options.oauthAuth?.baseUrl ??
		OPENAI_COMPATIBLE_REGISTRY[normalizedProviderId] ??
		NATIVE_DEFAULTS[normalizedProviderId];
	if (!configuredBase) throw new Error(`Cannot discover models for provider "${providerId}" without baseUrl.`);
	const endpoint = modelCatalogUrl(normalizedProviderId, configuredBase);
	const headers: Record<string, string> = {
		...discoveryHeaders(normalizedProviderId, apiKey),
		...(options.oauthAuth?.headers ?? {}),
	};
	const requestUrl = endpoint;
	const controller = new AbortController();
	const cancel = (): void => controller.abort(options.signal?.reason);
	if (options.signal?.aborted) cancel();
	else options.signal?.addEventListener("abort", cancel, { once: true });
	// Hermes gives its live Codex discovery request ten seconds.  Five seconds
	// was short enough to reject healthy authenticated connections, especially
	// on the ChatGPT backend.
	const timeout = setTimeout(() => controller.abort(), 10_000);
	try {
		const response = await (options.request ?? fetchLiveCatalog)(requestUrl, { headers, signal: controller.signal });
		if (!response.ok) {
			if ((response.status === 401 || response.status === 403) && authMode === "oauth") {
				throw new ModelDiscoveryError(
					normalizedProviderId,
					`OAuth session expired, was revoked, or lacks access to this route. Run \`kageko auth login ${normalizedProviderId}\` and try again.`,
					{ status: response.status, retryable: false },
				);
			}
			if ((response.status === 401 || response.status === 403) && authMode === "api") {
				throw new ModelDiscoveryError(normalizedProviderId, apiCredentialRejectionMessage(normalizedProviderId), {
					status: response.status,
					retryAfterMs: parseRetryAfter(response.headers?.get?.("retry-after") ?? null),
					retryable: false,
				});
			}
			throw new ModelDiscoveryError(normalizedProviderId, `${response.status} ${response.statusText}`, {
				status: response.status,
				retryAfterMs: parseRetryAfter(response.headers?.get?.("retry-after") ?? null),
				retryable: response.status !== 401 && response.status !== 403,
			});
		}
		const live = parseLiveModelCatalog(await response.json());
		const liveModels = live.map((model) => fromLive(model, normalizedProviderId, authMode, endpoint));
		if (liveModels.length > 0)
			return liveModels.map((model) => (options.includeProvenance === true ? model : hideProvenance(model)));
		throw new ModelDiscoveryError(normalizedProviderId, "provider returned no model entries.", { retryable: false });
	} catch (error) {
		if (error instanceof ModelDiscoveryError) throw error;
		const cancelled = options.signal?.aborted === true;
		const timedOut = controller.signal.aborted && !cancelled;
		throw new ModelDiscoveryError(
			normalizedProviderId,
			cancelled
				? "request cancelled."
				: timedOut
					? "request timed out after 10 seconds."
					: error instanceof Error
						? modelDiscoveryConnectionMessage(requestUrl, error)
						: String(error),
			{ cause: error, retryable: true },
		);
	} finally {
		clearTimeout(timeout);
		options.signal?.removeEventListener("abort", cancel);
	}
}

function assertKimiDiscoveryAuth(providerId: string, authMode: "api" | "oauth", apiKey: string | undefined): void {
	if (providerId === "kimi-code" && authMode !== "oauth") {
		throw new ModelDiscoveryError(
			providerId,
			"Kimi For Coding is a subscription route and requires OAuth. Run `kageko auth login kimi-code`; Moonshot Open Platform API keys belong to kimi-coding or kimi-coding-cn.",
			{ retryable: false },
		);
	}
	if (providerId === "kimi-coding-cn" && !apiKey) {
		throw new ModelDiscoveryError(
			providerId,
			"Moonshot China Open Platform requires KIMI_CN_API_KEY. A Kimi For Coding subscription/OAuth token cannot be used on api.moonshot.cn.",
			{ retryable: false },
		);
	}
	if (providerId === "kimi-coding" && !apiKey) {
		throw new ModelDiscoveryError(
			providerId,
			"Moonshot Open Platform requires KIMI_API_KEY or KIMI_CODING_API_KEY. For a Kimi For Coding subscription, select kimi-code and log in with OAuth instead.",
			{ retryable: false },
		);
	}
}

function apiCredentialRejectionMessage(providerId: string): string {
	if (providerId === "kimi-coding-cn")
		return "Moonshot China Open Platform rejected KIMI_CN_API_KEY. This endpoint does not accept a Kimi For Coding subscription/OAuth token.";
	if (providerId === "kimi-coding")
		return "Moonshot Open Platform rejected KIMI_API_KEY/KIMI_CODING_API_KEY. For a subscription account, use the separate kimi-code OAuth provider.";
	return "API credentials were rejected or do not have permission to list models.";
}

function modelDiscoveryConnectionMessage(endpoint: string, error: Error): string {
	const code = errorCode(error);
	const host = new URL(endpoint).host;
	if (code === "ENOTFOUND" || code === "EAI_AGAIN")
		return `could not resolve ${host}; check DNS, VPN, or proxy configuration.`;
	if (code === "ECONNREFUSED") return `could not connect to ${host}; check your proxy or firewall.`;
	const lower = `${error.message} ${code ?? ""}`.toLowerCase();
	if (lower.includes("certificate") || lower.includes("unable_to_verify") || lower.includes("self signed"))
		return `could not verify the TLS certificate for ${host}; install your network's trusted root certificate rather than disabling TLS verification.`;
	return `could not reach ${host}; check network, HTTPS proxy, VPN, or firewall.${environmentProxyCompatibilityHint() ?? ""} (${error.message})`;
}

function errorCode(error: Error): string | undefined {
	const candidate = error as Error & { code?: unknown; cause?: unknown };
	if (typeof candidate.code === "string") return candidate.code;
	return candidate.cause instanceof Error ? errorCode(candidate.cause) : undefined;
}

function fromLive(
	model: ParsedLiveModel,
	providerId: string,
	authMode: "api" | "oauth",
	endpoint: string,
): DiscoveredModel {
	const id = model.id.replace(/^models\//, "");
	return withProvenance(
		{
			id,
			...(model.name === undefined ? {} : { name: model.name }),
			...(model.contextLength === undefined ? {} : { contextLength: model.contextLength }),
			...(model.contextLimit === undefined ? {} : { contextLimit: model.contextLimit }),
			...(model.maxOutputTokens === undefined ? {} : { maxOutputTokens: model.maxOutputTokens }),
			...(model.reasoningLevels === undefined ? {} : { reasoningLevels: [...model.reasoningLevels] }),
			...(model.capabilities === undefined ? {} : { capabilities: model.capabilities }),
		},
		providerId,
		authMode,
		endpoint,
		true,
		provenanceForLiveModel(model),
	);
}

function withProvenance(
	model: DiscoveredModel,
	providerId: string,
	authMode: "api" | "oauth",
	endpoint: string,
	enumerable: boolean,
	explicit?: ModelMetadataProvenance,
): DiscoveredModel {
	const provenance = explicit ?? unknownProvenance();
	const source = providerOrigin(providerId, endpoint, authMode);
	const result = { ...model } as DiscoveredModel;
	Object.defineProperty(result, "provenance", { value: provenance, enumerable, writable: false });
	Object.defineProperty(result, "metadataSource", { value: source, enumerable, writable: false });
	for (const [key, value] of Object.entries({
		contextLengthSource: provenance.contextLength,
		capabilitiesSource: provenance.capabilities,
		maxContextSizeSource: provenance.maxContextSize,
		maxOutputTokensSource: provenance.maxOutputTokens,
	}))
		Object.defineProperty(result, key, { value, enumerable, writable: false });
	return result;
}

function hideProvenance(model: DiscoveredModel): DiscoveredModel {
	return withProvenance(
		model,
		model.metadataSource?.providerId ?? "unknown",
		model.metadataSource?.authMode ?? "api",
		model.metadataSource?.endpoint ?? "",
		false,
		model.provenance,
	);
}

function modelCatalogUrl(providerId: string, baseUrl: string): string {
	const base = baseUrl.replace(/\/$/, "");
	if (providerId === "anthropic" || providerId === "claude")
		return /\/v1$/.test(base) ? `${base}/models` : `${base}/v1/models`;
	const url = `${base}/models`;
	// Hermes codex_models.py pins client_version=1.0.0 on the live catalog.
	return providerId === "openai-codex" ? `${url}${url.includes("?") ? "&" : "?"}client_version=1.0.0` : url;
}

function discoveryHeaders(providerId: string, apiKey: string | undefined): Record<string, string> {
	const headers: Record<string, string> = { "User-Agent": "hermes-cli/0.1.0", Accept: "application/json" };
	if (providerId === "anthropic" || providerId === "claude") {
		if (apiKey) Object.assign(headers, { "x-api-key": apiKey, "anthropic-version": "2023-06-01" });
	} else if (apiKey) {
		headers["Authorization"] = `Bearer ${apiKey}`;
	}
	if (["github-copilot", "copilot"].includes(providerId)) {
		Object.assign(headers, {
			"Editor-Version": "vscode/1.104.1",
			"User-Agent": "HermesAgent/1.0",
			"Copilot-Integration-Id": "vscode-chat",
			"Openai-Intent": "conversation-edits",
			"x-initiator": "agent",
		});
	}
	if (["kimi", "kimi-code", "kimi-coding", "kimi-coding-cn", "moonshot", "moonshotai"].includes(providerId)) {
		headers["User-Agent"] = "hermes-agent/1.0";
	}
	if (["gmi", "gmi-cloud", "gmicloud"].includes(providerId)) {
		headers["User-Agent"] = "HermesAgent/1.0";
	}
	if (["ai-gateway", "vercel"].includes(providerId)) {
		headers["HTTP-Referer"] = "https://hermes-agent.nousresearch.com";
		headers["X-Title"] = "Hermes Agent";
	}
	return headers;
}
