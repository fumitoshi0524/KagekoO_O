/**
 * Shared types for Kageko OAuth flows and credential storage.
 *
 * This module replaces the previous `@earendil-works/pi-ai` type imports so
 * `packages/oauth` can stand on its own.
 */

/**
 * A persisted credential for any provider.
 */
export type Credential = OAuthCredential | ApiKeyCredential | Record<string, unknown>;

/**
 * OAuth 2.0 credential persisted by the credential store.
 */
export interface OAuthCredential extends Record<string, unknown> {
	type: "oauth";
	access: string;
	refresh: string;
	expires: number;
}

/**
 * API-key credential persisted by the credential store.
 */
export interface ApiKeyCredential extends Record<string, unknown> {
	type: "api_key";
	key: string;
}

/**
 * Generic credential store used by the OAuth service.
 */
export interface CredentialStore {
	read(providerId: string): Promise<Credential | undefined>;
	modify(
		providerId: string,
		fn: (current: Credential | undefined) => Promise<Credential | undefined>,
	): Promise<Credential | undefined>;
	delete(providerId: string): Promise<void>;
}

/**
 * Context used by auth flows to read environment variables and check files.
 */
export interface AuthContext {
	env(name: string): Promise<string | undefined>;
	fileExists(path: string): Promise<boolean>;
}

/**
 * Prompt definition passed to `AuthLoginCallbacks.prompt`.
 */
export interface PromptDef {
	type?: string;
	message: string;
	options?: ReadonlyArray<{ id: string; label: string; description?: string }>;
	placeholder?: string;
}

/**
 * Notification event emitted during an OAuth login flow.
 */
export type NotifyEvent =
	| {
			type: "auth_url";
			url: string;
			instructions?: string;
			/** The host, not a provider module, owns best-effort browser launch. */
			openBrowser?: boolean;
	  }
	| {
			type: "device_code";
			userCode: string;
			verificationUri: string;
			intervalSeconds?: number;
			expiresInSeconds?: number;
			/** Hermes opens this provider's verification page after showing its code. */
			openBrowser?: boolean;
	  }
	| { type: "progress"; message: string };

/**
 * Callbacks supplied by consumers to drive and observe an OAuth login flow.
 */
export interface AuthLoginCallbacks {
	signal?: AbortSignal;
	prompt?: (def: PromptDef) => Promise<string | undefined>;
	notify?: (event: NotifyEvent) => void;
}

/**
 * Auth result produced by an OAuth provider's `toAuth` method.
 */
export interface OAuthAuthResult {
	headers?: Record<string, string>;
	baseUrl?: string;
	/** Optional provider-specific runtime credential state to persist atomically. */
	credentialPatch?: Record<string, unknown>;
}

/**
 * OAuth provider implementation.
 */
export interface OAuthAuth {
	name: string;
	login(callbacks: AuthLoginCallbacks): Promise<OAuthCredential>;
	refresh?(credential: OAuthCredential): Promise<OAuthCredential>;
	toAuth?(credential: OAuthCredential): Promise<OAuthAuthResult>;
}

/**
 * Dependencies required by `createOAuthService`.
 */
export interface OAuthServiceDeps {
	credentialStore: CredentialStore;
	authContext: AuthContext;
	/**
	 * Maps a provider alias to its canonical credential-store id (the
	 * composition root injects kosong's `canonicalHermesProviderId`; oauth must
	 * not depend on kosong). Defaults to identity.
	 */
	canonicalizeProviderId?: (providerId: string) => string;
}

/**
 * OAuth service public API.
 */
export interface OAuthService {
	/**
	 * Run OAuth login for a provider and persist the resulting credential.
	 */
	login(providerId: string, callbacks: AuthLoginCallbacks): Promise<OAuthCredential>;

	/**
	 * Remove stored credentials for a provider.
	 */
	logout(providerId: string): Promise<void>;
}
