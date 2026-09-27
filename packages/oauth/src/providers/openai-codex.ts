/**
 * OpenAI Codex OAuth device-authorization flow.
 *
 * Endpoints (from the public Codex CLI / hermes-agent reference):
 * - User code:    POST https://auth.openai.com/api/accounts/deviceauth/usercode
 * - Device token: POST https://auth.openai.com/api/accounts/deviceauth/token
 * - Token:        POST https://auth.openai.com/oauth/token
 * - Client id:    app_EMoamEEZ73f0CkXaXp7hrann
 *
 * The flow is not RFC 8628: the device poll returns an authorization code plus
 * a server-generated PKCE code_verifier, which is then exchanged for tokens.
 */
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import type { OAuthAuth, OAuthCredential } from "../types.js";
import { providerFetch } from "../provider-fetch.ts";
import { abortableSleep } from "../utils/abortable-sleep.ts";

const ISSUER = "https://auth.openai.com";
const CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann";
const USERCODE_URL = `${ISSUER}/api/accounts/deviceauth/usercode`;
const DEVICE_TOKEN_URL = `${ISSUER}/api/accounts/deviceauth/token`;
const TOKEN_URL = `${ISSUER}/oauth/token`;
const VERIFICATION_URI = `${ISSUER}/codex/device`;
const REDIRECT_URI = `${ISSUER}/deviceauth/callback`;
const DEFAULT_BASE_URL = "https://chatgpt.com/backend-api/codex";
/** Matches Hermes' 15-second timeout for each device/token HTTP operation. */
const FETCH_TIMEOUT_MS = 15_000;
/** Matches the hermes reference: minimum 3s between polls, 15 minute limit. */
const MIN_POLL_INTERVAL_SECONDS = 3;
const MAX_WAIT_MS = 15 * 60 * 1000;

interface UserCodeResponse {
	user_code?: string;
	device_auth_id?: string;
	/** The reference implementation sends this as a string. */
	interval?: string | number;
}

interface DeviceTokenResponse {
	authorization_code?: string;
	code_verifier?: string;
}

interface TokenResponse {
	access_token?: string;
	refresh_token?: string;
	expires_in?: number;
	error?: string | { code?: string; message?: string; type?: string };
	error_description?: string;
}

export const openaiCodexOAuth: OAuthAuth = {
	name: "OpenAI Codex",

	async login(callbacks) {
		// Without an interactive prompt there is no consent channel for importing
		// another application's session, so always begin a fresh device flow.
		const cliCredential = callbacks.prompt ? await importCodexCliCredential() : undefined;
		if (cliCredential) {
			callbacks.notify?.({
				type: "progress",
				message: "Found Codex CLI credentials. Import them into Kageko? A fresh login remains available.",
			});
			const response = (
				await callbacks.prompt?.({
					type: "select",
					message: "Choose how to continue with the valid Codex CLI session:",
					options: [
						{ id: "import", label: "Import Codex CLI session" },
						{ id: "fresh", label: "Start a fresh device login" },
					],
				})
			)
				?.trim()
				.toLowerCase();
			if (response === "import") return cliCredential;
		}
		callbacks.notify?.({ type: "progress", message: "Requesting device code from OpenAI..." });

		const userCodeRes = await codexFetch("device-code request", USERCODE_URL, {
			signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
			method: "POST",
			// Hermes sends only the request content type on this endpoint.
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ client_id: CLIENT_ID }),
		});
		if (!userCodeRes.ok) {
			throw new Error(
				`OpenAI Codex device code request failed: ${userCodeRes.status} ${await readErrorDetail(userCodeRes)}`,
			);
		}
		const device = await parseJson<UserCodeResponse>(userCodeRes, "OpenAI Codex device code request");
		if (!device.user_code || !device.device_auth_id) {
			throw new Error("OpenAI Codex device code response is missing user_code or device_auth_id.");
		}

		callbacks.notify?.({
			type: "device_code",
			userCode: device.user_code,
			verificationUri: VERIFICATION_URI,
			intervalSeconds: pollIntervalSeconds(device.interval),
			expiresInSeconds: MAX_WAIT_MS / 1000,
		});

		const start = Date.now();
		const intervalMs = pollIntervalSeconds(device.interval) * 1000;
		let deviceToken: DeviceTokenResponse | undefined;

		while (Date.now() - start < MAX_WAIT_MS) {
			await abortableSleep(intervalMs, callbacks.signal);

			const pollRes = await codexFetch("device authorization poll", DEVICE_TOKEN_URL, {
				signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					device_auth_id: device.device_auth_id,
					user_code: device.user_code,
				}),
			});

			if (pollRes.status === 403 || pollRes.status === 404) {
				// User has not completed the browser login yet; keep polling.
				continue;
			}
			if (!pollRes.ok) {
				throw new Error(`OpenAI Codex device auth polling failed: ${pollRes.status} ${await readErrorDetail(pollRes)}`);
			}
			deviceToken = await parseJson<DeviceTokenResponse>(pollRes, "OpenAI Codex device auth poll");
			break;
		}

		if (!deviceToken) {
			throw new Error("OpenAI Codex login timed out after 15 minutes.");
		}
		if (!deviceToken.authorization_code || !deviceToken.code_verifier) {
			throw new Error("OpenAI Codex device auth response is missing authorization_code or code_verifier.");
		}

		const tokenRes = await codexFetch("token exchange", TOKEN_URL, {
			signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({
				grant_type: "authorization_code",
				code: deviceToken.authorization_code,
				redirect_uri: REDIRECT_URI,
				client_id: CLIENT_ID,
				code_verifier: deviceToken.code_verifier,
			}),
		});
		if (!tokenRes.ok) {
			throw new Error(`OpenAI Codex token exchange failed: ${tokenRes.status} ${await readErrorDetail(tokenRes)}`);
		}
		const token = await parseJson<TokenResponse>(tokenRes, "OpenAI Codex token exchange");

		return toCredential(token);
	},

	async refresh(credential) {
		const res = await codexFetch("token refresh", TOKEN_URL, {
			signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
			body: new URLSearchParams({
				grant_type: "refresh_token",
				client_id: CLIENT_ID,
				refresh_token: credential.refresh,
			}),
		});
		const bodyText = await res.text();
		let token: TokenResponse | undefined;
		try {
			token = JSON.parse(bodyText) as TokenResponse;
		} catch {
			// Non-JSON body handled below.
		}
		if (!res.ok) {
			const detail = formatErrorDetail(token, bodyText);
			// Hermes auth.py: a 401/403 from the token endpoint always means the
			// refresh token is invalid/expired — force relogin even when the body
			// error code is not a known string.
			if (res.status === 400 || res.status === 401 || res.status === 403 || token?.error === "invalid_grant") {
				throw new OpenAICodexReloginRequiredError(
					`OpenAI Codex refresh failed (re-login required): ${res.status} ${detail}`,
				);
			}
			throw new Error(`OpenAI Codex refresh failed: ${res.status} ${detail}`);
		}
		if (!token) {
			throw new Error(`OpenAI Codex refresh returned invalid JSON: ${bodyText.slice(0, 200)}`);
		}
		if (!token.access_token) {
			throw new OpenAICodexReloginRequiredError(
				"OpenAI Codex refresh response is missing access_token (re-login required).",
			);
		}
		return toCredential(
			{ ...token, refresh_token: token.refresh_token || credential.refresh },
			(credential["base_url"] as string | undefined) ?? DEFAULT_BASE_URL,
		);
	},

	async toAuth(credential) {
		// Keep this byte-for-byte aligned with Hermes' _codex_cloudflare_headers.
		// These first-party Codex headers are required by the Cloudflare layer in
		// front of chatgpt.com/backend-api/codex; auth alone can otherwise 403.
		const headers: Record<string, string> = {
			Authorization: `Bearer ${credential.access}`,
			"User-Agent": "codex_cli_rs/0.0.0 (Hermes Agent)",
			originator: "codex_cli_rs",
		};
		const accountId = readChatGptAccountId(credential.access);
		if (accountId) headers["ChatGPT-Account-ID"] = accountId;
		return {
			headers,
			baseUrl: (credential["base_url"] as string | undefined) ?? DEFAULT_BASE_URL,
		};
	},
};

function readChatGptAccountId(accessToken: string): string | undefined {
	const payload = accessToken.split(".")[1];
	if (!payload) return undefined;
	try {
		const claims = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Record<string, unknown>;
		const auth = claims["https://api.openai.com/auth"];
		if (auth && typeof auth === "object") {
			const accountId = (auth as Record<string, unknown>)["chatgpt_account_id"];
			if (typeof accountId === "string" && accountId.length > 0) return accountId;
		}
		const accountId = claims["chatgpt_account_id"];
		return typeof accountId === "string" && accountId.length > 0 ? accountId : undefined;
	} catch {
		return undefined;
	}
}

/**
 * Error thrown when the stored OpenAI Codex credential can no longer be
 * refreshed and the user must run the login flow again.
 */
export class OpenAICodexReloginRequiredError extends Error {
	readonly reloginRequired = true;
	constructor(message: string) {
		super(message);
		this.name = "OpenAICodexReloginRequiredError";
	}
}

/** A connection failure is distinct from a rejected refresh token. */
export class OpenAICodexConnectionError extends Error {
	readonly retryable = true;
	constructor(message: string, options: { cause?: unknown; code?: string } = {}) {
		super(message, options.cause === undefined ? undefined : { cause: options.cause });
		this.name = "OpenAICodexConnectionError";
		if (options.code !== undefined) Object.defineProperty(this, "code", { value: options.code, enumerable: true });
	}
}

async function codexFetch(stage: string, url: string, init: RequestInit): Promise<Response> {
	try {
		return await providerFetch(url, init);
	} catch (error) {
		throw codexConnectionError(stage, url, error);
	}
}

function codexConnectionError(stage: string, url: string, error: unknown): OpenAICodexConnectionError {
	const cause = error instanceof Error ? error : new Error(String(error));
	const code = errorCode(cause);
	const host = new URL(url).host;
	const lower = `${cause.message} ${code ?? ""}`.toLowerCase();
	if (code === "ENOTFOUND" || code === "EAI_AGAIN")
		return new OpenAICodexConnectionError(
			`OpenAI Codex ${stage} could not resolve ${host}. Check DNS, VPN, or proxy configuration.`,
			{ cause, code },
		);
	if (code === "ECONNREFUSED")
		return new OpenAICodexConnectionError(
			`OpenAI Codex ${stage} could not connect to ${host}. Check your proxy or firewall.`,
			{ cause, code },
		);
	if (lower.includes("certificate") || lower.includes("unable_to_verify") || lower.includes("self signed"))
		return new OpenAICodexConnectionError(
			`OpenAI Codex ${stage} could not verify the TLS certificate for ${host}. Install your network's trusted root certificate rather than disabling TLS verification.`,
			{ cause, code },
		);
	return new OpenAICodexConnectionError(
		`OpenAI Codex ${stage} could not reach ${host}. Check your network, HTTPS proxy, VPN, or firewall. (${cause.message})`,
		{ cause, code },
	);
}

function errorCode(error: Error): string | undefined {
	const candidate = error as Error & { code?: unknown; cause?: unknown };
	if (typeof candidate.code === "string") return candidate.code;
	return candidate.cause instanceof Error ? errorCode(candidate.cause) : undefined;
}

export function toCredential(token: TokenResponse, baseUrl: string = DEFAULT_BASE_URL): OAuthCredential {
	if (!token.access_token) {
		throw new Error("OpenAI Codex token response is missing access_token.");
	}
	if (!token.refresh_token) {
		throw new Error("OpenAI Codex token response is missing refresh_token.");
	}
	return {
		type: "oauth",
		access: token.access_token,
		refresh: token.refresh_token,
		expires: Date.now() + (token.expires_in ?? 3600) * 1000,
		expiresInMs: (token.expires_in ?? 3600) * 1000,
		base_url: baseUrl,
	};
}

/** Hermes-equivalent, read-only discovery of Codex CLI state. It never writes
 * to `.codex/auth.json` or imports automatically. An expired access token is
 * still importable when a refresh token exists: normal OAuth resolution will
 * rotate it before the first request instead of forcing an unnecessary login. */
export async function importCodexCliCredential(): Promise<OAuthCredential | undefined> {
	const codexHome =
		process.env["CODEX_HOME"]?.trim() ||
		path.join(process.env["USERPROFILE"]?.trim() || process.env["HOME"]?.trim() || os.homedir(), ".codex");
	try {
		const raw = JSON.parse(await fs.readFile(path.join(codexHome, "auth.json"), "utf8")) as {
			tokens?: { access_token?: unknown; refresh_token?: unknown };
		};
		const access = typeof raw.tokens?.access_token === "string" ? raw.tokens.access_token.trim() : "";
		const refresh = typeof raw.tokens?.refresh_token === "string" ? raw.tokens.refresh_token.trim() : "";
		const expires = codexTokenExpiresAt(access);
		if (!access || !refresh) return undefined;
		return { type: "oauth", access, refresh, expires, base_url: DEFAULT_BASE_URL };
	} catch {
		return undefined;
	}
}

function codexTokenExpiresAt(token: string): number {
	try {
		const payload = token.split(".")[1];
		if (!payload) return 0;
		const decoded = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { exp?: unknown };
		const exp = typeof decoded.exp === "number" ? decoded.exp : Number(decoded.exp);
		return Number.isFinite(exp) && exp > 0 ? exp * 1000 : 0;
	} catch {
		return 0;
	}
}

function pollIntervalSeconds(interval: string | number | undefined): number {
	const parsed = Number.parseInt(String(interval ?? "5"), 10);
	return Math.max(MIN_POLL_INTERVAL_SECONDS, Number.isFinite(parsed) ? parsed : 5);
}

async function parseJson<T>(res: Response, context: string): Promise<T> {
	const text = await res.text();
	try {
		return JSON.parse(text) as T;
	} catch {
		throw new Error(`${context} returned invalid JSON: ${text.slice(0, 200)}`);
	}
}

/**
 * Extract a readable detail string from an error response, preferring a parsed
 * OAuth `error`/`error_description` body over the raw text.
 */
async function readErrorDetail(res: Response): Promise<string> {
	const text = await res.text();
	try {
		const parsed = JSON.parse(text) as TokenResponse;
		return formatErrorDetail(parsed, text);
	} catch {
		return text.slice(0, 200);
	}
}

function formatErrorDetail(token: TokenResponse | undefined, rawText: string): string {
	const error = token?.error;
	if (typeof error === "string" && error.length > 0) {
		return token?.error_description ? `${error}: ${token.error_description}` : error;
	}
	if (error && typeof error === "object") {
		const code = error.code || error.type;
		const message = error.message || token?.error_description;
		if (code && message) return `${code}: ${message}`;
		if (message) return message;
		if (code) return code;
	}
	return rawText.slice(0, 200);
}
