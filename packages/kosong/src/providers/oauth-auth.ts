/**
 * Shared helper for resolving API-key or OAuth authentication for providers
 * that wrap OpenAI-compatible endpoints.
 *
 * Reads explicit keys and provider-specific environment variables first, then
 * falls back to the injected OAuth credential resolver. Kosong never touches
 * credential stores directly; the resolver is supplied by the composition
 * root.
 */
import type { OAuthCredentialResolver, OAuthRequestAuth } from "../credentials.js";

export interface ResolvedAuth {
	apiKey: string;
	baseUrl?: string;
}

interface ResolveAuthOptions {
	providerId: string;
	authMode?: "api" | "oauth";
	envKeyName?: string;
	apiKey?: string;
	oauthResolver?: OAuthCredentialResolver;
}

export async function resolveAuth(options: ResolveAuthOptions): Promise<ResolvedAuth> {
	if (options.authMode !== "oauth" && options.apiKey) {
		return { apiKey: options.apiKey };
	}

	if (options.authMode !== "oauth" && options.envKeyName) {
		const envValue = process.env[options.envKeyName];
		if (envValue) {
			return { apiKey: envValue };
		}
	}

	if (options.authMode !== "api" && options.oauthResolver) {
		return authResultToResolvedAuth(await options.oauthResolver(options.providerId), options.providerId);
	}

	if (options.authMode === "oauth") {
		throw new Error(`OAuth route for provider "${options.providerId}" requires a credential resolver.`);
	}

	throw new Error(
		`No credentials found for provider "${options.providerId}". Set ${options.envKeyName ?? "the provider-specific API key"}, or run \`kageko auth login ${options.providerId}\`.`,
	);
}

function authResultToResolvedAuth(result: OAuthRequestAuth, providerId: string): ResolvedAuth {
	const authorization = result.headers["Authorization"];
	const token = authorization?.replace(/^Bearer\s+/i, "");
	if (!token) {
		throw new Error(`OAuth auth for "${providerId}" did not return a bearer token.`);
	}
	return { apiKey: token, baseUrl: result.baseUrl };
}
