/**
 * Credential ports for OAuth-backed providers.
 *
 * Kosong owns the model/provider abstraction; credential storage, refresh and
 * persistence belong to the host's credential layer. Providers receive these
 * ports by injection and never touch credential stores directly.
 */

/** Request authentication resolved from an OAuth credential. */
export interface OAuthRequestAuth {
	headers: Record<string, string>;
	baseUrl?: string;
}

/**
 * Resolve the stored OAuth credential for a provider into request auth,
 * refreshing and persisting it when it is close to expiry.
 *
 * Implementations live in the composition root, which binds this port to the
 * credential layer's stored-credential resolution.
 */
export type OAuthCredentialResolver = (providerId: string) => Promise<OAuthRequestAuth>;
