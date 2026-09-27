import * as dns from "node:dns/promises";
import * as http from "node:http";
import * as https from "node:https";
import * as net from "node:net";
import * as tls from "node:tls";
import { createExternalFetchEvent } from "../../memory/learning/event.js";
import type { Tool, ToolContext } from "../types.js";
import { publicNetworkAccess } from "../accesses.js";

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MAX_BYTES = 2 * 1024 * 1024; // 2 MiB hard cap on fetch body
const MAX_REDIRECTS = 5;
const MAX_TIMEOUT_MS = 120_000;
const MAX_OUTPUT_CHARS = 100_000;

interface FetchUrlArgs {
	url: string;
	maxLength?: number;
	timeout?: number;
}

interface DispatcherOptions {
	origin?: string;
	path?: string;
	method?: string;
	headers?: Record<string, string | string[]>;
	signal?: AbortSignal;
	body?: string | Buffer;
}

interface DispatcherHandler {
	onConnect(abort: () => void): void;
	onHeaders(statusCode: number, headers: string[], resume: () => void, statusMessage?: string): void;
	onData(chunk: Buffer): void;
	onComplete(trailers: string[]): void;
	onError(err: Error): void;
}

interface Dispatcher {
	dispatch(opts: DispatcherOptions, handler: DispatcherHandler): void;
}

export const fetchUrlTool: Tool<FetchUrlArgs> = {
	name: "fetch_url",
	description: "Fetch the text content of a public URL.",
	parameters: {
		type: "object",
		properties: {
			url: { type: "string", description: "URL to fetch" },
			maxLength: { type: "number", description: "Maximum characters to return (default 8000)" },
			timeout: { type: "number", description: "Fetch timeout in milliseconds (default 30000)" },
		},
		required: ["url"],
	},
	resolveExecution({ url }: FetchUrlArgs) {
		return { accesses: publicNetworkAccess("fetch", url, { sendsContent: false }) };
	},
	async execute({ url, maxLength = 8000, timeout = DEFAULT_TIMEOUT_MS }: FetchUrlArgs, { session }: ToolContext) {
		maxLength = Number.isFinite(maxLength) ? Math.max(0, Math.min(MAX_OUTPUT_CHARS, Math.trunc(maxLength))) : 8000;
		timeout = Number.isFinite(timeout)
			? Math.max(1, Math.min(MAX_TIMEOUT_MS, Math.trunc(timeout)))
			: DEFAULT_TIMEOUT_MS;
		let currentUrl = url;
		let redirects = 0;
		while (redirects <= MAX_REDIRECTS) {
			let parsed: URL;
			try {
				parsed = new URL(currentUrl);
			} catch {
				return { output: `Invalid URL: ${currentUrl}`, isError: true };
			}
			if (!/^https?:$/i.test(parsed.protocol)) {
				return { output: `Only HTTP/HTTPS URLs are allowed: ${currentUrl}`, isError: true };
			}
			if (parsed.username || parsed.password) {
				return { output: `URLs containing credentials are not allowed: ${currentUrl}`, isError: true };
			}
			const hostCheck = await isHostPrivate(parsed.hostname);
			if (hostCheck.private) {
				return { output: `Refusing to fetch private/reserved address: ${hostCheck.reason}`, isError: true };
			}

			const signal = AbortSignal.timeout(timeout);
			let res: Response;
			try {
				res = await fetch(currentUrl, {
					signal,
					redirect: "manual",
					dispatcher: new SafeDispatcher(),
					headers: {
						"User-Agent": "Mozilla/5.0 (compatible; Kageko/0.1)",
						Accept: "text/html, text/plain, application/json",
					},
				} as unknown as RequestInit);
			} catch (err) {
				if (signal.aborted || (err as Error).name === "TimeoutError" || (err as Error).name === "AbortError") {
					return { output: `Fetch timed out after ${timeout}ms: ${currentUrl}`, isError: true };
				}
				return { output: `Fetch failed: ${(err as Error).message}`, isError: true };
			}

			if (isRedirect(res.status)) {
				const location = res.headers.get("location");
				if (!location) {
					cancelBody(res);
					return { output: `Redirect response missing Location header: ${currentUrl}`, isError: true };
				}
				currentUrl = new URL(location, currentUrl).toString();
				redirects += 1;
				cancelBody(res);
				continue;
			}

			if (!res.ok) {
				cancelBody(res);
				return { output: `Fetch failed: ${res.status} ${res.statusText}`, isError: true };
			}

			let text: string;
			try {
				text = await readTextWithCap(res, DEFAULT_MAX_BYTES);
			} catch (err) {
				return { output: `Fetch failed: ${(err as Error).message}`, isError: true };
			}

			const contentType = res.headers.get("content-type") ?? "";
			if (contentType.includes("text/html")) {
				text = stripHtml(text);
			}
			const truncated = text.length > maxLength;
			const output = text.slice(0, maxLength) + (truncated ? "\n... (truncated)" : "");
			session?.learningBus?.enqueue(
				createExternalFetchEvent("url", { url, content: output, truncated }, { toolName: "fetch_url" }),
			);
			return { output, truncated };
		}
		return { output: `Too many redirects (${MAX_REDIRECTS}) starting from ${url}`, isError: true };
	},
};

function isRedirect(status: number): boolean {
	return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

async function readTextWithCap(res: Response, maxBytes: number): Promise<string> {
	const contentLength = res.headers?.get?.("content-length");
	if (contentLength && Number(contentLength) > maxBytes) {
		cancelBody(res);
		throw new Error(`Response body exceeds ${maxBytes} bytes`);
	}
	if (!res.body) {
		if (typeof res.text !== "function") {
			return "";
		}
		const text = await res.text();
		if (Buffer.byteLength(text) > maxBytes) {
			throw new Error(`Response body exceeds ${maxBytes} bytes`);
		}
		return text;
	}
	const reader = res.body.getReader();
	const chunks: Buffer[] = [];
	let received = 0;
	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;
			const buffer = Buffer.isBuffer(value) ? value : Buffer.from(value);
			received += buffer.length;
			if (received > maxBytes) {
				reader.cancel().catch(() => {});
				throw new Error(`Response body exceeds ${maxBytes} bytes`);
			}
			chunks.push(buffer);
		}
	} finally {
		reader.releaseLock();
	}
	return Buffer.concat(chunks).toString("utf-8");
}

function cancelBody(res: Response): void {
	res.body?.cancel?.().catch(() => {});
}

function stripHtml(raw: string): string {
	return raw
		.replace(/<script[\s\S]*?<\/script>/gi, " ")
		.replace(/<style[\s\S]*?<\/style>/gi, " ")
		.replace(/<[^>]+>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

async function isHostPrivate(hostname: string): Promise<{ private: boolean; reason?: string }> {
	const host = hostname.replace(/^\[|\]$/g, "");
	const family = net.isIP(host);
	if (family === 4) {
		return { private: isPrivateIPv4(host), reason: hostname };
	}
	if (family === 6) {
		return { private: isPrivateIPv6(host), reason: hostname };
	}
	try {
		const records = await dns.lookup(host, { all: true });
		for (const { address } of records) {
			if (isPrivateIPv4(address) || isPrivateIPv6(address)) {
				return { private: true, reason: address };
			}
		}
	} catch {
		// Allow the fetch to proceed; the network will reject unreachable hosts.
	}
	return { private: false };
}

function isPrivateIPv4(ip: string): boolean {
	const lowered = ip.toLowerCase();
	if (lowered.startsWith("::ffff:")) {
		return isPrivateIPv4(extractMappedIPv4(lowered));
	}
	const parts = ip.split(".").map(Number);
	if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) return false;
	const [a, b, c] = parts as [number, number, number, number];
	// Reject special-use destinations conservatively. Some ranges include
	// individually routable addresses; a public-page fetcher does not need them.
	if (a === 0 || a === 10 || a === 127) return true;
	if (a === 169 && b === 254) return true;
	if (a === 172 && b >= 16 && b <= 31) return true;
	if (a === 192 && b === 0 && (c === 0 || c === 2)) return true;
	if (a === 192 && b === 88 && c === 99) return true;
	if (a === 192 && b === 168) return true;
	if (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) return true;
	if (a === 203 && b === 0 && c === 113) return true;
	if (a === 100 && b >= 64 && b <= 127) return true;
	if (a >= 224) return true;
	return false;
}

function extractMappedIPv4(mapped: string): string {
	if (mapped.includes(".")) return mapped.slice(mapped.lastIndexOf(":") + 1);
	// Convert compressed hex form ::ffff:7f00:1 to dotted decimal.
	const groups = mapped.split(":").filter(Boolean);
	const octets: number[] = [];
	for (const group of groups) {
		const value = parseInt(group, 16);
		if (Number.isNaN(value) || value < 0 || value > 0xffff) return "";
		octets.push((value >> 8) & 0xff, value & 0xff);
	}
	if (octets.length !== 4) return "";
	return octets.join(".");
}

function isPrivateIPv6(ip: string): boolean {
	const full = ip.toLowerCase();
	if (full.startsWith("::ffff:")) {
		const mapped = full.slice(7);
		return isPrivateIPv4(extractMappedIPv4(mapped));
	}
	// Only native global unicast is eligible. This also excludes loopback,
	// unspecified, link-local, unique-local and multicast destinations.
	const first = Number.parseInt(full.split(":", 1)[0] ?? "", 16);
	return !Number.isFinite(first) || first < 0x2000 || first > 0x3fff || full.startsWith("2001:db8:");
}

async function resolvePublicAddress(hostname: string): Promise<{ address: string; family: number }> {
	const host = hostname.replace(/^\[|\]$/g, "");
	const family = net.isIP(host);
	if (family === 4) {
		if (isPrivateIPv4(host)) {
			throw new Error(`Refusing to fetch private/reserved address: ${hostname}`);
		}
		return { address: host, family };
	}
	if (family === 6) {
		if (isPrivateIPv6(host)) {
			throw new Error(`Refusing to fetch private/reserved address: ${hostname}`);
		}
		return { address: host, family };
	}
	const records = await dns.lookup(host, { all: true });
	for (const record of records) {
		if (!isPrivateIPv4(record.address) && !isPrivateIPv6(record.address)) {
			return { address: record.address, family: record.family };
		}
	}
	throw new Error(`Refusing to fetch private/reserved address: ${hostname}`);
}

class SafeDispatcher implements Dispatcher {
	dispatch(opts: DispatcherOptions, handler: DispatcherHandler): void {
		let url: URL;
		try {
			url = new URL(opts.origin ?? "");
		} catch (err) {
			handler.onError(err as Error);
			return;
		}
		resolvePublicAddress(url.hostname)
			.then(({ address }) => {
				const isHttps = url.protocol === "https:";
				const port = url.port || (isHttps ? "443" : "80");
				const headers: Record<string, string> = {
					...(opts.headers as Record<string, string> | undefined),
					Host: url.host,
				};
				headers["accept-encoding"] = "identity";
				const requestOptions: http.RequestOptions & { servername?: string } = {
					method: opts.method,
					host: address,
					hostname: address,
					port: Number(port),
					path: opts.path,
					headers,
					servername: url.hostname,
					createConnection: (
						options: http.ClientRequestArgs,
						oncreate: (err: Error | null, socket: net.Socket) => void,
					) => {
						const remote = options.host || options.hostname;
						if (!remote || isPrivateIPv4(remote) || isPrivateIPv6(remote)) {
							const err = new Error(`Refusing to fetch private/reserved address: ${remote ?? ""}`);
							oncreate(err, undefined as unknown as net.Socket);
							return;
						}
						if (isHttps) {
							const socket = tls.connect({
								host: remote,
								port: Number(options.port),
								servername: url.hostname,
							});
							socket.once("secureConnect", () => oncreate(null, socket));
							return socket;
						}
						const socket = net.connect({
							host: remote,
							port: Number(options.port),
						});
						socket.once("connect", () => oncreate(null, socket));
						return socket;
					},
				};
				const lib = isHttps ? https : http;
				const req = lib.request(requestOptions, (res: http.IncomingMessage) => {
					const rawHeaders: string[] = res.rawHeaders;
					const headers: string[] = [];
					for (let i = 0; i < rawHeaders.length; i += 2) {
						headers.push(rawHeaders[i]!, rawHeaders[i + 1]!);
					}
					handler.onHeaders(res.statusCode ?? 0, headers, () => {}, res.statusMessage);
					res.on("data", (chunk: Buffer) => handler.onData(chunk));
					res.on("end", () => handler.onComplete([]));
					res.on("error", (err: Error) => handler.onError(err));
				});
				if (opts.signal) {
					const onAbort = () => {
						req.destroy();
					};
					if (opts.signal.aborted) {
						onAbort();
						return;
					}
					opts.signal.addEventListener("abort", onAbort, { once: true });
					req.once("close", () => opts.signal!.removeEventListener("abort", onAbort));
				}
				req.on("error", (err: Error) => handler.onError(err));
				handler.onConnect(() => {
					req.destroy();
				});
				if (opts.body) {
					req.write(opts.body);
				}
				req.end();
			})
			.catch((err: Error) => handler.onError(err));
	}
}
