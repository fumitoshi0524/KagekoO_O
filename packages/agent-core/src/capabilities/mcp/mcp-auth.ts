import * as http from "node:http";
import * as https from "node:https";
import * as crypto from "node:crypto";
export { McpOAuthClient as McpAuth };
import * as net from "node:net";
import * as dns from "node:dns";
import type { Duplex } from "node:stream";

const MAX_TOKEN_VALUE_BYTES = 8 * 1024;
const OAUTH_FETCH_TIMEOUT_MS = 30_000;
const MAX_BODY_BYTES = 64 * 1024;
const MAX_POLL_INTERVAL_MS = 60_000;
const MAX_EXPIRES_IN_SEC = 24 * 60 * 60;
const CALLBACK_TIMEOUT_MS = 300_000;

function abortableSleep(ms: number, signal?: AbortSignal): Promise<void> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) {
			reject(signal.reason ?? new Error("Aborted"));
			return;
		}
		const timer = setTimeout(resolve, ms);
		if (!signal) return;
		const onAbort = (): void => {
			clearTimeout(timer);
			reject(signal.reason ?? new Error("Aborted"));
		};
		signal.addEventListener("abort", onAbort, { once: true });
	});
}

function throwIfAborted(signal?: AbortSignal): void {
	if (signal?.aborted) throw signal.reason ?? new Error("Aborted");
}

/**
 * HTTPS agent that validates the resolved IP address at socket-open time to
 * prevent SSRF to private/reserved addresses (TOCTOU-safe).
 */
class PublicOnlyAgent extends https.Agent {
	override createConnection(
		options: https.RequestOptions,
		callback?: (err: Error | null, stream: Duplex) => void,
	): Duplex | null | undefined {
		const reject = (error: Error): undefined => {
			callback?.(error, undefined as never);
			return undefined;
		};
		const host = options.host as string;
		if (net.isIP(host)) {
			if (isPrivateIPv4(host) || isPrivateIPv6(host)) {
				return reject(new Error(`OAuth endpoint ${host} is a private/reserved address; refusing to connect`));
			}
			return super.createConnection(options, callback);
		}
		dns.lookup(host, (err, address) => {
			if (err) {
				callback?.(err, undefined as never);
				return;
			}
			if (isPrivateIPv4(address) || isPrivateIPv6(address)) {
				callback?.(
					new Error(`OAuth endpoint ${host} resolves to a private/reserved address (${address}); refusing to connect`),
					undefined as never,
				);
				return;
			}
			super.createConnection({ ...options, host: address, servername: host }, callback);
		});
		return undefined;
	}
}

const publicAgent = new PublicOnlyAgent({ keepAlive: false });

export interface McpOAuthToken {
	accessToken?: string;
	refreshToken?: string;
	expiresAt?: number;
	tokenType?: string;
	raw?: Record<string, unknown>;
	[key: string]: unknown;
}

/**
 * Persistence port for MCP OAuth tokens, keyed by server name.
 *
 * Implementations are injected by the application layer (the file-backed store
 * lives in `@kageko/oauth`, which owns credential paths and formats); agent-core
 * never resolves credential file locations itself. Reads and writes are
 * whole-map; `McpOAuthClient` serializes read-modify-write access.
 */
export interface McpTokenStore {
	readAll(): Promise<Record<string, McpOAuthToken>>;
	writeAll(tokens: Record<string, McpOAuthToken>): Promise<void>;
}

export interface McpOAuthConfig {
	flow?: "device_code" | "authorization_code";
	deviceAuthorizationEndpoint?: string;
	deviceAuthUrl?: string;
	authorizationEndpoint?: string;
	authorizeUrl?: string;
	tokenEndpoint?: string;
	tokenUrl?: string;
	clientId?: string;
	clientSecret?: string;
	scopes?: string[] | string;
	instructions?: string;
	oauth?: McpOAuthConfig;
}

interface DeviceCodeResponse {
	user_code?: string;
	verification_uri?: string;
	interval?: number;
	expires_in?: number;
	device_code?: string;
	[error: string]: unknown;
}

interface OAuthTokenResponse {
	access_token?: string;
	refresh_token?: string;
	expires_in?: number;
	token_type?: string;
	error?: string;
	error_description?: string;
	[error: string]: unknown;
}

export interface OAuthNotifyEvent {
	type: string;
	serverName?: string;
	message?: string;
	userCode?: string;
	verificationUri?: string;
	intervalSeconds?: number;
	expiresInSeconds?: number;
	url?: string;
	instructions?: string;
}

export interface McpOAuthCallbacks {
	notify?: (event: OAuthNotifyEvent) => void;
}

export interface McpOAuthClientOptions {
	tokenStore: McpTokenStore;
	callbacks?: McpOAuthCallbacks;
}

interface FetchPublicInit {
	signal?: AbortSignal;
	method?: string;
	headers?: Record<string, string>;
	body?: URLSearchParams | string | Buffer | Record<string, unknown>;
}

interface FetchPublicResponse {
	ok: boolean;
	status: number;
	text(): Promise<string>;
	json(): Promise<unknown>;
}

/**
 * Generic OAuth helper for remote MCP servers.
 *
 * Supports device_code (RFC 8628) and authorization_code with a localhost
 * callback. Tokens are persisted through the injected {@link McpTokenStore},
 * keyed by server name.
 */
export class McpOAuthClient {
	readonly tokenStore: McpTokenStore;
	readonly callbacks: McpOAuthCallbacks;
	/** In-flight OAuth flows keyed by server name. */
	private _pending = new Map<string, Promise<McpOAuthToken>>();
	/** Serialize read-modify-write access to the token store. */
	private _lock: Promise<unknown> = Promise.resolve();

	constructor(options: McpOAuthClientOptions) {
		this.tokenStore = options.tokenStore;
		this.callbacks = options.callbacks ?? {};
	}

	notify(event: OAuthNotifyEvent): void {
		try {
			this.callbacks.notify?.(event);
		} catch {
			/* ignore */
		}
	}

	async readStore(): Promise<Record<string, McpOAuthToken>> {
		return this.tokenStore.readAll();
	}

	async writeStore(data: Record<string, McpOAuthToken>): Promise<void> {
		assertSafeKey("server name", Object.keys(data));
		await this.tokenStore.writeAll(data);
	}

	private _runLocked<T>(fn: () => Promise<T>): Promise<T> {
		const previous = this._lock;
		const next = (async () => {
			await previous.catch(() => {});
			return fn();
		})();
		this._lock = next.catch(() => {});
		return next;
	}

	/**
	 * Get the stored token for a server.
	 */
	async getToken(serverName: string): Promise<McpOAuthToken | undefined> {
		assertSafeKey("server name", serverName);
		return this._runLocked(async () => {
			const store = await this.readStore();
			return store[serverName];
		});
	}

	/**
	 * Store a token for a server.
	 */
	async setToken(serverName: string, token: McpOAuthToken): Promise<void> {
		assertSafeKey("server name", serverName);
		const capped = capTokenValues(token);
		return this._runLocked(async () => {
			const store = await this.readStore();
			store[serverName] = capped;
			await this.writeStore(store);
		});
	}

	/**
	 * Run the configured OAuth flow for a server and persist the token.
	 */
	async authenticate(
		serverName: string,
		config: McpOAuthConfig,
		{ signal }: { signal?: AbortSignal } = {},
	): Promise<McpOAuthToken> {
		assertSafeKey("server name", serverName);
		throwIfAborted(signal);

		const existing = this._pending.get(serverName);
		if (existing) return existing;

		const promise = this._runAuthentication(serverName, config, signal);
		this._pending.set(serverName, promise);
		try {
			return await promise;
		} finally {
			this._pending.delete(serverName);
		}
	}

	private async _runAuthentication(
		serverName: string,
		config: McpOAuthConfig,
		signal?: AbortSignal,
	): Promise<McpOAuthToken> {
		const oauth = config.oauth ?? config;
		const flow = oauth.flow;

		let token: McpOAuthToken;
		if (flow === "device_code") {
			await validateDeviceCodeEndpoints(oauth, signal);
			token = normalizeToken(await this.runDeviceCodeFlow(serverName, oauth, signal));
		} else if (flow === "authorization_code") {
			await validateAuthorizationCodeEndpoints(oauth, signal);
			token = normalizeToken(await this.runAuthorizationCodeFlow(serverName, oauth, signal));
		} else {
			throw new Error(`Unsupported OAuth flow: ${flow}`);
		}

		await this.setToken(serverName, token);
		return token;
	}

	async runDeviceCodeFlow(
		serverName: string,
		oauth: McpOAuthConfig,
		signal?: AbortSignal,
	): Promise<OAuthTokenResponse> {
		const deviceAuthUrl = oauth.deviceAuthorizationEndpoint ?? oauth.deviceAuthUrl;
		const tokenUrl = oauth.tokenEndpoint ?? oauth.tokenUrl;
		const clientId = oauth.clientId;

		if (!deviceAuthUrl) throw new Error("deviceAuthorizationEndpoint is required for device_code flow");
		if (!tokenUrl) throw new Error("tokenEndpoint is required for device_code flow");
		if (!clientId) throw new Error("clientId is required for device_code flow");

		const params = new URLSearchParams({ client_id: clientId });
		if (oauth.scopes) {
			params.set("scope", Array.isArray(oauth.scopes) ? oauth.scopes.join(" ") : oauth.scopes);
		}

		this.notify({ type: "progress", message: `Requesting device code for ${serverName}...` });
		const deviceRes = await fetchPublic(deviceAuthUrl, {
			signal,
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: params,
		});
		if (!deviceRes.ok) {
			throw new Error(`Device authorization failed: ${deviceRes.status} ${await deviceRes.text()}`);
		}
		const device = (await deviceRes.json()) as DeviceCodeResponse;

		this.notify({
			type: "device_code",
			serverName,
			userCode: device.user_code,
			verificationUri: device.verification_uri,
			intervalSeconds: device.interval,
			expiresInSeconds: device.expires_in,
		});

		const start = Date.now();
		const expiresInMs = Math.min(device.expires_in ?? 1800, MAX_EXPIRES_IN_SEC) * 1000;
		let intervalMs = Math.min(Math.max((device.interval ?? 5) * 1000, 1000), MAX_POLL_INTERVAL_MS);

		while (Date.now() - start < expiresInMs) {
			await abortableSleep(intervalMs, signal);

			const tokenRes = await fetchPublic(tokenUrl, {
				signal,
				method: "POST",
				headers: { "Content-Type": "application/x-www-form-urlencoded" },
				body: new URLSearchParams({
					grant_type: "urn:ietf:params:oauth:grant-type:device_code",
					client_id: clientId,
					device_code: device.device_code ?? "",
				}),
			});
			const token = (await tokenRes.json()) as OAuthTokenResponse;

			if (token.error) {
				if (token.error === "authorization_pending") continue;
				if (token.error === "slow_down") {
					intervalMs = Math.min(intervalMs + 5000, MAX_POLL_INTERVAL_MS);
					continue;
				}
				throw new Error(`Token exchange failed: ${token.error} ${token.error_description ?? ""}`);
			}

			return token;
		}

		throw new Error("Device code expired before authorization.");
	}

	async runAuthorizationCodeFlow(
		serverName: string,
		oauth: McpOAuthConfig,
		signal?: AbortSignal,
	): Promise<OAuthTokenResponse> {
		const authorizeUrl = oauth.authorizationEndpoint ?? oauth.authorizeUrl;
		const tokenUrl = oauth.tokenEndpoint ?? oauth.tokenUrl;
		const clientId = oauth.clientId;

		if (!authorizeUrl) throw new Error("authorizationEndpoint is required for authorization_code flow");
		if (!tokenUrl) throw new Error("tokenEndpoint is required for authorization_code flow");
		if (!clientId) throw new Error("clientId is required for authorization_code flow");

		// Always generate a fresh random state. Config-provided state is ignored
		// to prevent CSRF/predictable-state attacks.
		const state = crypto.randomUUID();
		// Always bind the callback to a random port on loopback. Config-provided
		// host/port/redirectUri are intentionally ignored to prevent plugins or
		// configs from redirecting authorization codes to attacker-controlled
		// endpoints.
		const host = "127.0.0.1";
		const port = 0;

		const server = http.createServer();
		await new Promise<void>((resolve, reject) => {
			server.once("error", reject);
			server.listen(port, host, resolve);
		});

		const address = server.address() as net.AddressInfo;
		const callbackUrl = `http://${address.address}:${address.port}/callback`;

		try {
			const authParams = new URLSearchParams({
				response_type: "code",
				client_id: clientId,
				redirect_uri: callbackUrl,
				state,
			});
			if (oauth.scopes) {
				authParams.set("scope", Array.isArray(oauth.scopes) ? oauth.scopes.join(" ") : oauth.scopes);
			}

			const fullUrl = `${authorizeUrl}?${authParams.toString()}`;
			this.notify({ type: "auth_url", serverName, url: fullUrl, instructions: oauth.instructions });

			const code = await waitForCallback(server, state, signal);

			const tokenParams = new URLSearchParams({
				grant_type: "authorization_code",
				client_id: clientId,
				code,
				redirect_uri: callbackUrl,
			});
			if (oauth.clientSecret) {
				tokenParams.set("client_secret", oauth.clientSecret);
			}

			const tokenRes = await fetchPublic(tokenUrl, {
				signal,
				method: "POST",
				headers: { "Content-Type": "application/x-www-form-urlencoded" },
				body: tokenParams,
			});
			if (!tokenRes.ok) {
				throw new Error(`Token exchange failed: ${tokenRes.status} ${await tokenRes.text()}`);
			}
			const token = (await tokenRes.json()) as OAuthTokenResponse;
			if (token.error) {
				throw new Error(`Token exchange failed: ${token.error} ${token.error_description ?? ""}`);
			}

			return token;
		} finally {
			await closeServer(server);
		}
	}

	/**
	 * Refresh a token using a refresh token.
	 */
	async refresh(
		serverName: string,
		refreshToken: string,
		tokenUrl: string,
		extra: { clientId?: string; clientSecret?: string } = {},
		{ signal }: { signal?: AbortSignal } = {},
	): Promise<McpOAuthToken> {
		assertSafeKey("server name", serverName);
		await assertPublicHttpsUrl(tokenUrl, "tokenEndpoint", signal);
		const clientId = extra.clientId;
		if (!clientId) throw new Error("clientId is required to refresh token");

		const params = new URLSearchParams({
			grant_type: "refresh_token",
			client_id: clientId,
			refresh_token: refreshToken,
		});
		if (extra.clientSecret) {
			params.set("client_secret", extra.clientSecret);
		}

		const res = await fetchPublic(tokenUrl, {
			signal,
			method: "POST",
			headers: { "Content-Type": "application/x-www-form-urlencoded" },
			body: params,
		});
		if (!res.ok) {
			throw new Error(`Refresh failed: ${res.status} ${await res.text()}`);
		}
		const token = (await res.json()) as OAuthTokenResponse;
		if (token.error) {
			throw new Error(`Refresh failed: ${token.error} ${token.error_description ?? ""}`);
		}

		const normalized = normalizeToken(token);
		await this.setToken(serverName, normalized);
		return normalized;
	}
}

function normalizeToken(token: OAuthTokenResponse): McpOAuthToken {
	const nowSeconds = Math.floor(Date.now() / 1000);
	return {
		accessToken: token.access_token,
		refreshToken: token.refresh_token,
		expiresAt: token.expires_in ? nowSeconds + token.expires_in : undefined,
		tokenType: token.token_type ?? "Bearer",
		raw: token,
	};
}

function capTokenValues(token: McpOAuthToken): McpOAuthToken {
	if (!token || typeof token !== "object") return token;
	const clone = { ...token };
	if (typeof clone.accessToken === "string" && Buffer.byteLength(clone.accessToken) > MAX_TOKEN_VALUE_BYTES) {
		clone.accessToken = clone.accessToken.slice(0, MAX_TOKEN_VALUE_BYTES);
	}
	if (typeof clone.refreshToken === "string" && Buffer.byteLength(clone.refreshToken) > MAX_TOKEN_VALUE_BYTES) {
		clone.refreshToken = clone.refreshToken.slice(0, MAX_TOKEN_VALUE_BYTES);
	}
	if (clone.raw && typeof clone.raw === "object") {
		clone.raw = { ...clone.raw };
		if (
			typeof clone.raw["access_token"] === "string" &&
			Buffer.byteLength(clone.raw["access_token"]) > MAX_TOKEN_VALUE_BYTES
		) {
			clone.raw["access_token"] = (clone.raw["access_token"] as string).slice(0, MAX_TOKEN_VALUE_BYTES);
		}
		if (
			typeof clone.raw["refresh_token"] === "string" &&
			Buffer.byteLength(clone.raw["refresh_token"]) > MAX_TOKEN_VALUE_BYTES
		) {
			clone.raw["refresh_token"] = (clone.raw["refresh_token"] as string).slice(0, MAX_TOKEN_VALUE_BYTES);
		}
	}
	return clone;
}

function waitForCallback(server: http.Server, expectedState: string, signal?: AbortSignal): Promise<string> {
	return new Promise((resolve, reject) => {
		throwIfAborted(signal);

		let settled = false;
		const timeout = setTimeout(() => {
			cleanup();
			reject(new Error("Authorization callback timed out."));
		}, CALLBACK_TIMEOUT_MS);

		const abortHandler = () => {
			cleanup();
			reject(signal?.reason ?? new Error("OAuth flow aborted"));
		};
		signal?.addEventListener("abort", abortHandler, { once: true });

		const handler = (req: http.IncomingMessage, res: http.ServerResponse) => {
			if (req.method !== "GET" || !req.url?.startsWith("/callback")) {
				res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
				res.end("Not found.");
				return;
			}

			const url = new URL(req.url, `http://localhost`);
			const code = url.searchParams.get("code");
			const state = url.searchParams.get("state");
			const error = url.searchParams.get("error");
			const errorDescription = url.searchParams.get("error_description");

			res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
			if (error) {
				res.end(`Authorization error: ${escapeText(error)}. You may close this window.`);
				cleanup();
				reject(new Error(`Authorization error: ${error} ${errorDescription ?? ""}`));
				return;
			}

			if (!code) {
				res.end("Missing authorization code. You may close this window.");
				cleanup();
				reject(new Error("Missing authorization code in callback."));
				return;
			}

			if (state !== expectedState) {
				res.end("Invalid state parameter. You may close this window.");
				cleanup();
				reject(new Error("Invalid state parameter in callback."));
				return;
			}

			res.end("Authorization successful. You may close this window.");
			cleanup();
			resolve(code);
		};

		function cleanup() {
			if (settled) return;
			settled = true;
			clearTimeout(timeout);
			signal?.removeEventListener("abort", abortHandler);
			server.removeAllListeners("request");
			server.removeAllListeners("error");
			void closeServer(server).catch(() => {});
		}

		server.on("request", handler);
	});
}

async function validateDeviceCodeEndpoints(oauth: McpOAuthConfig, signal?: AbortSignal): Promise<void> {
	const deviceAuthUrl = oauth.deviceAuthorizationEndpoint ?? oauth.deviceAuthUrl;
	const tokenUrl = oauth.tokenEndpoint ?? oauth.tokenUrl;
	await assertPublicHttpsUrl(deviceAuthUrl, "deviceAuthorizationEndpoint", signal);
	await assertPublicHttpsUrl(tokenUrl, "tokenEndpoint", signal);
}

async function validateAuthorizationCodeEndpoints(oauth: McpOAuthConfig, signal?: AbortSignal): Promise<void> {
	const authorizeUrl = oauth.authorizationEndpoint ?? oauth.authorizeUrl;
	const tokenUrl = oauth.tokenEndpoint ?? oauth.tokenUrl;
	await assertPublicHttpsUrl(authorizeUrl, "authorizationEndpoint", signal);
	await assertPublicHttpsUrl(tokenUrl, "tokenEndpoint", signal);
}

async function assertPublicHttpsUrl(urlString: string | undefined, label: string, signal?: AbortSignal): Promise<void> {
	throwIfAborted(signal);
	let parsed: URL;
	try {
		parsed = new URL(urlString ?? "");
	} catch {
		throw new Error(`OAuth ${label} is not a valid URL: ${urlString}`);
	}
	if (parsed.protocol !== "https:") {
		throw new Error(`OAuth ${label} must use HTTPS: ${urlString}`);
	}
	if (parsed.username || parsed.password) {
		throw new Error(`OAuth ${label} must not contain credentials: ${urlString}`);
	}
	// Reject literal private IPs early. Hostnames are validated at socket-open
	// time by PublicOnlyAgent to avoid DNS TOCTOU.
	const host = parsed.hostname;
	if (net.isIP(host) && (isPrivateIPv4(host) || isPrivateIPv6(host))) {
		throw new Error(`OAuth ${label} resolves to a private/reserved address (${host}); refusing to use it`);
	}
}

function fetchPublic(url: string, init: FetchPublicInit = {}): Promise<FetchPublicResponse> {
	const { signal: externalSignal, ...rest } = init;
	return new Promise((resolve, reject) => {
		if (externalSignal?.aborted) {
			reject(externalSignal.reason ?? new Error("OAuth request aborted"));
			return;
		}

		const timeoutController = new AbortController();
		const timer = setTimeout(() => {
			timeoutController.abort(new Error("OAuth request timed out"));
		}, OAUTH_FETCH_TIMEOUT_MS);

		let abortHandler: (() => void) | undefined;
		if (externalSignal) {
			abortHandler = () => timeoutController.abort(externalSignal.reason ?? new Error("OAuth request aborted"));
			externalSignal.addEventListener("abort", abortHandler, { once: true });
		}

		try {
			new URL(url);
		} catch {
			reject(new Error(`OAuth request URL is invalid: ${url}`));
			return;
		}
		const req = https.request(
			url,
			{
				method: rest.method ?? "GET",
				headers: rest.headers,
				agent: publicAgent,
				signal: timeoutController.signal,
			},
			(res) => {
				clearTimeout(timer);
				if (abortHandler) externalSignal?.removeEventListener("abort", abortHandler);
				collectLimitedBody(res, MAX_BODY_BYTES)
					.then((body) => {
						resolve({
							ok: (res.statusCode ?? 0) >= 200 && (res.statusCode ?? 0) < 300,
							status: res.statusCode ?? 0,
							text: async () => body.toString("utf-8"),
							json: async () => JSON.parse(body.toString("utf-8")),
						});
					})
					.catch(reject);
			},
		);

		req.on("error", (err) => {
			clearTimeout(timer);
			if (abortHandler) externalSignal?.removeEventListener("abort", abortHandler);
			reject(err);
		});

		timeoutController.signal.addEventListener("abort", () => {
			req.destroy(timeoutController.signal.reason ?? new Error("OAuth request aborted or timed out"));
		});

		const body = rest.body;
		if (body !== undefined) {
			if (body instanceof URLSearchParams) {
				req.write(body.toString());
			} else if (typeof body === "string" || Buffer.isBuffer(body)) {
				req.write(body);
			} else if (typeof body === "object" && body !== null) {
				req.write(JSON.stringify(body));
			}
		}
		req.end();
	});
}

function collectLimitedBody(stream: NodeJS.ReadableStream, maxBytes: number): Promise<Buffer> {
	return new Promise((resolve, reject) => {
		const chunks: Buffer[] = [];
		let received = 0;
		let overflow = false;
		stream.on("data", (chunk: Buffer) => {
			if (overflow) return;
			received += chunk.length;
			if (received > maxBytes) {
				overflow = true;
				(stream as NodeJS.ReadableStream & { destroy(err?: Error): void }).destroy(
					new Error(`OAuth response body exceeds ${maxBytes} byte limit`),
				);
				return;
			}
			chunks.push(chunk);
		});
		stream.on("end", () => resolve(Buffer.concat(chunks)));
		stream.on("error", reject);
	});
}

function isPrivateIPv4(ip: string): boolean {
	const parts = ip.split(".").map(Number);
	if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return false;
	const [a = 0, b = 0, c = 0] = parts;
	if (a === 0 || a === 10 || a === 127) return true;
	if (a === 169 && b === 254) return true;
	if (a === 172 && b >= 16 && b <= 31) return true;
	if (a === 192 && b === 168) return true;
	if (a === 100 && b >= 64 && b <= 127) return true;
	if (a >= 224 && a <= 239) return true;
	if (a === 255 && b === 255 && c === 255) return true;
	return false;
}

function isPrivateIPv6(ip: string): boolean {
	const full = ip.toLowerCase();
	if (full === "::1" || full.startsWith("fe80:") || full.startsWith("fc") || full.startsWith("fd")) return true;
	if (full.startsWith("::ffff:")) {
		const mapped = full.slice(7);
		return isPrivateIPv4(mapped);
	}
	return false;
}

function assertSafeKey(label: string, value: string | string[]): void {
	const values = Array.isArray(value) ? value : [value];
	for (const v of values) {
		if (typeof v === "string" && (v === "__proto__" || v === "constructor" || v === "prototype")) {
			throw new Error(`Invalid ${label}: ${v}`);
		}
	}
}

async function closeServer(server: http.Server): Promise<void> {
	if (!server.listening) return;
	if (typeof server.closeAllConnections === "function") {
		server.closeAllConnections();
	}
	await new Promise<void>((resolve) => server.close(() => resolve()));
}

function escapeText(text: unknown): string {
	return String(text)
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}
