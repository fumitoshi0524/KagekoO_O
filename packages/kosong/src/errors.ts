/** Provider boundary errors with enough structure for safe retry decisions. */
export class ProviderError extends Error {
	readonly status?: number;
	readonly code?: string;
	readonly retryAfterMs?: number;
	readonly retryable: boolean;

	constructor(
		message: string,
		options: {
			cause?: unknown;
			status?: number;
			code?: string;
			retryAfterMs?: number;
			retryable?: boolean;
		} = {},
	) {
		super(message, options.cause === undefined ? undefined : { cause: options.cause });
		this.name = "ProviderError";
		this.status = options.status;
		this.code = options.code;
		this.retryAfterMs = options.retryAfterMs;
		this.retryable = options.retryable ?? isRetryableStatus(options.status);
	}
}

/** A response that cannot be decoded without risking a wrong tool execution. */
export class ProviderProtocolError extends ProviderError {
	constructor(message: string, options: { cause?: unknown; retryable?: boolean } = {}) {
		super(message, { ...options, code: "PROVIDER_PROTOCOL_ERROR", retryable: options.retryable ?? true });
		this.name = "ProviderProtocolError";
	}
}

/** A provider request that never reached a usable HTTP response. */
export class ProviderConnectionError extends ProviderError {
	constructor(message: string, options: { cause?: unknown; code?: string } = {}) {
		super(message, { ...options, retryable: true });
		this.name = "ProviderConnectionError";
	}
}

/** A terminal OAuth state; retrying cannot restore a revoked refresh token. */
export class ProviderReloginRequiredError extends ProviderError {
	readonly reloginRequired = true;

	constructor(message: string, options: { cause?: unknown } = {}) {
		super(message, { ...options, code: "OAUTH_RELOGIN_REQUIRED", retryable: false });
		this.name = "ProviderReloginRequiredError";
	}
}

/** A structural timeout marker used instead of retrying arbitrary message text. */
export class LLMTimeoutError extends Error {
	readonly code = "LLM_TIMEOUT";
	readonly retryable = true;

	constructor(message: string) {
		super(message);
		this.name = "LLMTimeoutError";
	}
}

export function isRetryableStatus(status: number | undefined): boolean {
	return status === 408 || status === 425 || status === 429 || (status !== undefined && status >= 500);
}

export function parseRetryAfter(value: string | null, now = Date.now()): number | undefined {
	if (!value) return undefined;
	const seconds = Number(value);
	if (Number.isFinite(seconds) && seconds >= 0) return Math.ceil(seconds * 1000);
	const date = Date.parse(value);
	if (!Number.isFinite(date)) return undefined;
	return Math.max(0, date - now);
}
