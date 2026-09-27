/** Kimi For Coding subscription OAuth (RFC 8628 device-code flow). */
import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import type { OAuthAuth, OAuthCredential } from "../types.js";
import { providerFetch } from "../provider-fetch.js";
import { abortableSleep } from "../utils/abortable-sleep.ts";

export const KIMI_CODE_CLIENT_ID = "17e5f671-d194-4dfb-9706-5516cb48c098";
export const KIMI_CODE_OAUTH_HOST = "https://auth.kimi.com";
export const KIMI_CODE_API_BASE_URL = "https://api.kimi.com/coding/v1";
const FETCH_TIMEOUT_MS = 30_000;
const SLOW_DOWN_INCREMENT_MS = 5_000;
const REFRESH_MAX_RETRIES = 3;
const RETRYABLE_STATUSES = new Set([429, 500, 502, 503, 504]);

interface DeviceAuthorization {
	device_code: string;
	user_code: string;
	verification_uri?: string;
	verification_uri_complete?: string;
	interval?: number;
	expires_in?: number;
}

interface TokenResponse {
	access_token?: string;
	refresh_token?: string;
	expires_in?: number;
	error?: string;
	error_description?: string;
}

export interface KimiOAuthOptions {
	oauthHost?: string;
	baseUrl?: string;
	request?: typeof fetch;
	now?: () => number;
	sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
	deviceId?: () => string;
}

/** A terminal token state: retries cannot repair it. */
export class KimiReLoginRequiredError extends Error {
	readonly reloginRequired = true;
	readonly retryable = false;

	constructor(message: string) {
		super(message);
		this.name = "KimiReLoginRequiredError";
	}
}

export function createKimiOAuth(options: KimiOAuthOptions = {}): OAuthAuth {
	const oauthHost = (options.oauthHost ?? KIMI_CODE_OAUTH_HOST).replace(/\/+$/, "");
	const baseUrl = (options.baseUrl ?? KIMI_CODE_API_BASE_URL).replace(/\/+$/, "");
	const request = options.request ?? providerFetch;
	const now = options.now ?? Date.now;
	const sleepWithSignal = options.sleep ?? abortableSleep;
	const resolveDeviceId = options.deviceId ?? loadOrCreateDeviceId;

	return {
		name: "Kimi For Coding (subscription OAuth)",

		async login(callbacks) {
			const deviceId = resolveDeviceId();
			const headers = buildHeaders(deviceId);
			callbacks.notify?.({ type: "progress", message: "Requesting a Kimi For Coding device code..." });
			const deviceRes = await request(`${oauthHost}/api/oauth/device_authorization`, {
				signal: combinedSignal(callbacks.signal),
				method: "POST",
				headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
				body: new URLSearchParams({ client_id: KIMI_CODE_CLIENT_ID }),
			});
			const deviceBody = await parseJson<DeviceAuthorization & TokenResponse>(deviceRes, "Kimi device authorization");
			if (!deviceRes.ok) {
				throw new Error(
					`Kimi device authorization failed: ${deviceRes.status} ${deviceBody.error_description ?? deviceBody.error ?? deviceRes.statusText}`,
				);
			}
			assertDeviceAuthorization(deviceBody);
			const verificationUri = buildVerificationUri(deviceBody);
			callbacks.notify?.({
				type: "device_code",
				userCode: deviceBody.user_code,
				verificationUri,
				intervalSeconds: deviceBody.interval,
				expiresInSeconds: deviceBody.expires_in,
				openBrowser: true,
			});

			const startedAt = now();
			const expiresInMs = (deviceBody.expires_in ?? 1800) * 1000;
			let intervalMs = Math.max(deviceBody.interval ?? 5, 1) * 1000;
			while (now() - startedAt < expiresInMs) {
				await sleepWithSignal(intervalMs, callbacks.signal);
				const tokenRes = await request(`${oauthHost}/api/oauth/token`, {
					signal: combinedSignal(callbacks.signal),
					method: "POST",
					headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
					body: new URLSearchParams({
						grant_type: "urn:ietf:params:oauth:grant-type:device_code",
						client_id: KIMI_CODE_CLIENT_ID,
						device_code: deviceBody.device_code,
					}),
				});
				const token = await parseJson<TokenResponse>(tokenRes, "Kimi token exchange");
				if (token.error === "authorization_pending") continue;
				if (token.error === "slow_down") {
					intervalMs += SLOW_DOWN_INCREMENT_MS;
					continue;
				}
				if (token.error === "expired_token") throw new Error("Kimi device code expired before authorization.");
				if (!tokenRes.ok || token.error) {
					throw new Error(
						`Kimi token exchange failed: ${tokenRes.status} ${token.error ?? "unknown_error"} ${token.error_description ?? ""}`.trim(),
					);
				}
				return toCredential(token, deviceId, undefined, now());
			}
			throw new Error("Kimi device code expired before authorization.");
		},

		async refresh(credential) {
			const deviceId = typeof credential["deviceId"] === "string" ? credential["deviceId"] : resolveDeviceId();
			const headers = buildHeaders(deviceId);
			let lastError: Error | undefined;
			for (let attempt = 0; attempt < REFRESH_MAX_RETRIES; attempt += 1) {
				let res: Response;
				try {
					res = await request(`${oauthHost}/api/oauth/token`, {
						signal: AbortSignal.timeout(FETCH_TIMEOUT_MS),
						method: "POST",
						headers: { ...headers, "Content-Type": "application/x-www-form-urlencoded" },
						body: new URLSearchParams({
							grant_type: "refresh_token",
							client_id: KIMI_CODE_CLIENT_ID,
							refresh_token: credential.refresh,
						}),
					});
				} catch (error) {
					lastError = error instanceof Error ? error : new Error(String(error));
					if (attempt < REFRESH_MAX_RETRIES - 1) {
						await sleepWithSignal(refreshBackoffMs(attempt));
						continue;
					}
					throw lastError;
				}
				const token = await parseJson<TokenResponse>(res, "Kimi token refresh");
				if (res.status === 401 || res.status === 403 || token.error === "invalid_grant") {
					throw new KimiReLoginRequiredError(
						`Kimi For Coding OAuth expired or was revoked (HTTP ${res.status}); run \`kageko auth login kimi-code\` again.`,
					);
				}
				if (res.ok && !token.error) return toCredential(token, deviceId, credential.refresh, now());
				const detail = token.error_description ?? token.error ?? res.statusText;
				if (!RETRYABLE_STATUSES.has(res.status)) throw new Error(`Kimi refresh failed: ${res.status} ${detail}`);
				lastError = new Error(`Kimi refresh failed: ${res.status} ${detail}`);
				if (attempt < REFRESH_MAX_RETRIES - 1) {
					await sleepWithSignal(refreshBackoffMs(attempt));
					continue;
				}
				throw lastError;
			}
			throw lastError ?? new Error("Kimi refresh failed after retries.");
		},

		async toAuth(credential) {
			return { headers: { Authorization: `Bearer ${credential.access}` }, baseUrl };
		},
	};
}

export const kimiOAuth: OAuthAuth = createKimiOAuth();

function combinedSignal(signal: AbortSignal | undefined): AbortSignal {
	return signal
		? AbortSignal.any([signal, AbortSignal.timeout(FETCH_TIMEOUT_MS)])
		: AbortSignal.timeout(FETCH_TIMEOUT_MS);
}

function assertDeviceAuthorization(device: Partial<DeviceAuthorization>): asserts device is DeviceAuthorization {
	if (!device.device_code || !device.user_code || (!device.verification_uri && !device.verification_uri_complete)) {
		throw new Error("Kimi device authorization response is missing device_code, user_code, or verification URI.");
	}
}

function buildVerificationUri(device: DeviceAuthorization): string {
	if (device.verification_uri_complete) return device.verification_uri_complete;
	const url = new URL(device.verification_uri!);
	url.searchParams.set("user_code", device.user_code);
	return url.toString();
}

function buildHeaders(deviceId: string): Record<string, string> {
	return {
		"User-Agent": "Kageko/1.0",
		"X-Msh-Platform": "kimi_code_cli",
		"X-Msh-Version": "1.0.0",
		"X-Msh-Device-Name": asciiHeader(os.hostname()),
		"X-Msh-Device-Model": asciiHeader(`Kageko ${process.platform} ${process.arch}`),
		"X-Msh-Os-Version": asciiHeader(os.release()),
		"X-Msh-Device-Id": deviceId,
		Accept: "application/json",
	};
}

function asciiHeader(value: string): string {
	const cleaned = value.replaceAll(/[^\u0020-\u007E]/g, "").trim();
	return cleaned || "unknown";
}

function loadOrCreateDeviceId(): string {
	const target = path.join(os.homedir(), ".kageko", "device_id");
	try {
		const existing = fs.readFileSync(target, "utf8").trim();
		if (existing) return existing;
	} catch {
		// First launch or unreadable file.
	}
	const id = crypto.randomUUID();
	try {
		fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 });
		fs.writeFileSync(target, id, { encoding: "utf8", mode: 0o600 });
	} catch {
		// Requests can still use the process-local id.
	}
	return id;
}

function refreshBackoffMs(attempt: number): number {
	return 2 ** attempt * 1000;
}

function toCredential(
	token: TokenResponse,
	deviceId: string,
	fallbackRefreshToken: string | undefined,
	now: number,
): OAuthCredential {
	if (!token.access_token) throw new Error("Kimi token response missing access_token");
	const refresh = token.refresh_token || fallbackRefreshToken;
	if (!refresh) throw new Error("Kimi token response missing refresh_token");
	const expiresIn = Number(token.expires_in);
	if (!Number.isFinite(expiresIn) || expiresIn <= 0)
		throw new Error("Kimi token response missing or invalid expires_in");
	return {
		type: "oauth",
		access: token.access_token,
		refresh,
		expires: now + expiresIn * 1000,
		expiresInMs: expiresIn * 1000,
		deviceId,
	};
}

async function parseJson<T>(response: Response, context: string): Promise<T> {
	const text = await response.text();
	try {
		return JSON.parse(text) as T;
	} catch {
		throw new Error(`${context} returned invalid JSON: ${text.slice(0, 200)}`);
	}
}
