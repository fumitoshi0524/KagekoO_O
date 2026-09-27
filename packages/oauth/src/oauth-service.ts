import type {
	AuthContext,
	AuthLoginCallbacks,
	CredentialStore,
	OAuthAuth,
	OAuthCredential,
	OAuthService,
	OAuthServiceDeps,
} from "./types.js";
import { openaiCodexOAuth } from "./providers/openai-codex.ts";
import { kimiOAuth } from "./providers/kimi-oauth.ts";

const customOAuthProviders: Record<string, OAuthAuth> = {
	"kimi-code": kimiOAuth,
	"kimi-for-coding": kimiOAuth,
	"openai-codex": openaiCodexOAuth,
};

const storedCredentialResolutions = new WeakMap<
	CredentialStore,
	Map<string, Promise<{ headers: Record<string, string>; baseUrl?: string }>>
>();

async function getProviderOAuth(providerId: string): Promise<OAuthAuth> {
	const custom = customOAuthProviders[providerId];
	if (custom) {
		return custom;
	}
	throw new Error(
		`Unknown OAuth provider "${providerId}". Supported providers: ${Object.keys(customOAuthProviders).join(", ")}.`,
	);
}

/**
 * Convert a freshly issued OAuth credential into request authentication for
 * the provider API. This is used immediately after login by setup/model
 * discovery, before the normal LLM provider has been constructed.
 */
export async function resolveOAuthCredential(
	providerId: string,
	credential: OAuthCredential,
): Promise<{ headers: Record<string, string>; baseUrl?: string }> {
	const oauth = await getProviderOAuth(providerId);
	if (!oauth.toAuth) {
		throw new Error(`OAuth provider "${providerId}" does not expose API authentication.`);
	}
	const auth = await oauth.toAuth(credential);
	return { headers: auth.headers ?? {}, baseUrl: auth.baseUrl };
}

/**
 * Resolve a persisted credential, refreshing and saving it when it is close
 * to expiry. Consumers use this for providers whose chat API is
 * OpenAI-compatible but whose authentication is OAuth-specific.
 */
export async function resolveStoredOAuthCredential(
	providerId: string,
	credentialStore: CredentialStore,
	options: { readonly credentialProviderId?: string; readonly signal?: AbortSignal } = {},
): Promise<{ headers: Record<string, string>; baseUrl?: string }> {
	const credentialProviderId = options.credentialProviderId ?? providerId;
	const resolutionKey = `${providerId}\u0000${credentialProviderId}`;
	let resolutions = storedCredentialResolutions.get(credentialStore);
	if (!resolutions) {
		resolutions = new Map();
		storedCredentialResolutions.set(credentialStore, resolutions);
	}
	let resolution = resolutions.get(resolutionKey);
	if (!resolution) {
		resolution = resolveStoredOAuthCredentialOnce(providerId, credentialProviderId, credentialStore);
		resolutions.set(resolutionKey, resolution);
		const cleanup = (): void => {
			if (resolutions?.get(resolutionKey) === resolution) resolutions.delete(resolutionKey);
			if (resolutions?.size === 0) storedCredentialResolutions.delete(credentialStore);
		};
		void resolution.then(cleanup, cleanup);
	}
	return abortableResolution(resolution, options.signal);
}

async function resolveStoredOAuthCredentialOnce(
	providerId: string,
	credentialProviderId: string,
	credentialStore: CredentialStore,
): Promise<{ headers: Record<string, string>; baseUrl?: string }> {
	const oauth = await getProviderOAuth(providerId);
	const stored = await credentialStore.read(credentialProviderId);
	if (!isOAuthCredential(stored)) {
		throw new Error(`No OAuth credential found for provider "${credentialProviderId}". Run setup or log in again.`);
	}
	const credential = !needsRefresh(stored)
		? stored
		: await credentialStore.modify(credentialProviderId, async (current) => {
				if (!isOAuthCredential(current)) {
					throw new Error(
						`No OAuth credential found for provider "${credentialProviderId}". Run setup or log in again.`,
					);
				}
				if (!needsRefresh(current)) return current;
				if (!oauth.refresh) {
					throw new Error(`OAuth credential for "${providerId}" has expired and cannot be refreshed.`);
				}
				// Built-in refresh routes are bounded below the store's 60-second lock
				// deadline, so waiters can safely re-read the rotated token under one lock.
				const refreshed = await oauth.refresh(current);
				if (!isOAuthCredential(refreshed)) {
					throw new Error(`OAuth provider "${providerId}" returned an invalid credential during refresh.`);
				}
				return refreshed;
			});
	if (!isOAuthCredential(credential)) {
		throw new Error(`No OAuth credential found for provider "${credentialProviderId}". Run setup or log in again.`);
	}
	const oauthAuth = await getProviderOAuth(providerId);
	if (!oauthAuth.toAuth) {
		throw new Error(`OAuth provider "${providerId}" does not expose API authentication.`);
	}
	const auth = await oauthAuth.toAuth(credential);
	if (auth.credentialPatch && Object.keys(auth.credentialPatch).length > 0) {
		await credentialStore.modify(credentialProviderId, async (current) => {
			if (!isOAuthCredential(current)) return current;
			return { ...current, ...auth.credentialPatch };
		});
	}
	return { headers: auth.headers ?? {}, baseUrl: auth.baseUrl };
}

function abortableResolution<T>(resolution: Promise<T>, signal: AbortSignal | undefined): Promise<T> {
	if (!signal) return resolution;
	if (signal.aborted)
		return Promise.reject(signal.reason instanceof Error ? signal.reason : new Error("OAuth resolution was aborted"));
	return new Promise<T>((resolve, reject) => {
		const abort = (): void =>
			reject(signal.reason instanceof Error ? signal.reason : new Error("OAuth resolution was aborted"));
		signal.addEventListener("abort", abort, { once: true });
		void resolution.then(
			(value) => {
				signal.removeEventListener("abort", abort);
				resolve(value);
			},
			(error: unknown) => {
				signal.removeEventListener("abort", abort);
				reject(error);
			},
		);
	});
}

function needsRefresh(credential: OAuthCredential): boolean {
	if (!credential.refresh) return credential.expires > 0 && credential.expires <= Date.now();
	const expiresInMs = Number(credential["expiresInMs"]);
	const skewMs = Math.max(60_000, Number.isFinite(expiresInMs) && expiresInMs > 0 ? expiresInMs * 0.1 : 0);
	return credential.expires <= 0 || credential.expires < Date.now() + skewMs;
}

function isOAuthCredential(value: unknown): value is OAuthCredential {
	if (!value || typeof value !== "object") return false;
	const credential = value as Record<string, unknown>;
	return (
		credential["type"] === "oauth" &&
		typeof credential["access"] === "string" &&
		typeof credential["refresh"] === "string" &&
		typeof credential["expires"] === "number"
	);
}

/**
 * Create the Kageko OAuth service.
 */
export function createOAuthService({
	credentialStore,
	authContext,
	canonicalizeProviderId,
}: OAuthServiceDeps): OAuthService {
	// `authContext` is accepted to preserve the public API; it is not currently
	// used by the built-in custom OAuth providers.
	void authContext;
	const canonicalize = canonicalizeProviderId ?? ((providerId: string) => providerId);

	return {
		async login(providerId, callbacks) {
			const canonical = canonicalize(providerId);
			const oauth = await getProviderOAuth(canonical);
			const credential = await oauth.login(callbacks);
			await credentialStore.modify(canonical, async () => credential);
			return credential;
		},

		async logout(providerId) {
			await getProviderOAuth(providerId);
			// Mirror the application's auth.remove symmetry: aliases share one
			// canonical store entry, so logout clears both the canonical id and
			// the raw alias the credential was stored under.
			const canonical = canonicalize(providerId);
			await credentialStore.delete(canonical);
			if (canonical !== providerId) await credentialStore.delete(providerId);
		},
	};
}

export type { OAuthServiceDeps, OAuthService };
