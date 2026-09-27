import { spawn } from "node:child_process";
import * as http from "node:http";

const NATIVE_FETCH = globalThis.fetch;
let environmentProxyConfigured = false;
const WINDOWS_HTTP_SCRIPT = `
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([Console]::In.ReadToEnd())) | ConvertFrom-Json
$handler = [Net.Http.HttpClientHandler]::new()
$requestUri = [Uri][string]$payload.url
$proxyNames = if ($requestUri.Scheme -ieq 'https') { @('https_proxy', 'HTTPS_PROXY', 'http_proxy', 'HTTP_PROXY', 'all_proxy', 'ALL_PROXY') } else { @('http_proxy', 'HTTP_PROXY', 'all_proxy', 'ALL_PROXY') }
$proxyUrl = ''
foreach ($proxyName in $proxyNames) {
  $candidate = [Environment]::GetEnvironmentVariable($proxyName)
  if (-not [string]::IsNullOrWhiteSpace($candidate)) { $proxyUrl = $candidate; break }
}
if ($proxyUrl) {
  $proxyUri = [Uri]$proxyUrl
  $proxy = [Net.WebProxy]::new($proxyUri)
  if ($proxyUri.UserInfo) {
    $parts = $proxyUri.UserInfo.Split(':', 2)
    $password = if ($parts.Length -gt 1) { [Uri]::UnescapeDataString($parts[1]) } else { '' }
    $proxy.Credentials = [Net.NetworkCredential]::new([Uri]::UnescapeDataString($parts[0]), $password)
  }
  $handler.Proxy = $proxy
  $handler.UseProxy = $true
}
$client = [Net.Http.HttpClient]::new($handler)
$request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::new([string]$payload.method), [string]$payload.url)
if ($null -ne $payload.body) { $request.Content = [Net.Http.StringContent]::new([string]$payload.body, [Text.Encoding]::UTF8) }
foreach ($header in $payload.headers) {
  if ([string]$header[0] -ieq 'Content-Type') {
    if ($null -eq $request.Content) { $request.Content = [Net.Http.ByteArrayContent]::new([byte[]]@()) }
    $request.Content.Headers.ContentType = [Net.Http.Headers.MediaTypeHeaderValue]::Parse([string]$header[1])
  } elseif (-not $request.Headers.TryAddWithoutValidation([string]$header[0], [string]$header[1])) {
    if ($null -eq $request.Content) { $request.Content = [Net.Http.ByteArrayContent]::new([byte[]]@()) }
    $null = $request.Content.Headers.TryAddWithoutValidation([string]$header[0], [string]$header[1])
  }
}
$response = $client.SendAsync($request).GetAwaiter().GetResult()
$headers = @{}
foreach ($header in $response.Headers) { $headers[$header.Key] = ($header.Value -join ',') }
foreach ($header in $response.Content.Headers) { $headers[$header.Key] = ($header.Value -join ',') }
$result = @{ status = [int]$response.StatusCode; statusText = [string]$response.ReasonPhrase; headers = $headers; body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() } | ConvertTo-Json -Compress -Depth 6
[Console]::Out.Write([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($result)))
`;

interface WindowsHttpResponse {
	status: number;
	statusText: string;
	headers: Record<string, string>;
	body: string;
}

/**
 * Fetch an authenticated provider request through Windows' system HTTP stack.
 * Node's fetch does not automatically adopt Windows' system proxy settings;
 * OAuth has always used this route, so inference must use it too. On other
 * platforms, preserve the native fetch implementation (and its proxy setup).
 *
 * A test-installed fetch intentionally wins over the Windows bridge, keeping
 * provider tests hermetic and allowing callers to inject a fetch mock.
 */
export async function fetchProviderRequest(url: string, init: RequestInit = {}): Promise<Response> {
	configureEnvironmentProxy();
	// Never send loopback traffic through PowerShell's system bridge. A Windows
	// proxy can otherwise intercept localhost and make hermetic provider flows
	// hang before reaching their local test server.
	if (isLoopbackUrl(url) || process.platform !== "win32" || globalThis.fetch !== NATIVE_FETCH) return fetch(url, init);
	if (init.body instanceof ReadableStream) throw new Error("Provider requests cannot use a streaming request body.");
	const body = init.body === undefined || init.body === null ? undefined : await bodyText(init.body);
	return windowsSystemFetch(url, init.method ?? "GET", init.headers, body, init.signal);
}

function isLoopbackUrl(value: string): boolean {
	try {
		const hostname = new URL(value).hostname.toLowerCase();
		return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
	} catch {
		return false;
	}
}

/**
 * Node 24.14+ can apply HTTP(S)_PROXY/NO_PROXY to global fetch after startup.
 * Invoke it once before provider traffic. Older Node 24 releases still support
 * the same setting when launched with NODE_USE_ENV_PROXY=1, so they remain
 * compatible without pulling a second HTTP client into the provider layer.
 */
/** Apply the current process HTTP(S)_PROXY settings before SDK-backed provider calls. */
export function configureEnvironmentProxy(): void {
	if (environmentProxyConfigured || !hasHttpProxyEnvironment()) return;
	const setter = (http as typeof http & { setGlobalProxyFromEnv?: () => unknown }).setGlobalProxyFromEnv;
	if (typeof setter !== "function") return;
	setter();
	environmentProxyConfigured = true;
}

export function environmentProxyCompatibilityHint(): string | undefined {
	if (process.platform === "win32" || !hasProxyEnvironment()) return undefined;
	const startedWithProxy = process.env["NODE_USE_ENV_PROXY"] === "1" || process.execArgv.includes("--use-env-proxy");
	const supportsRuntimeProxy =
		typeof (http as typeof http & { setGlobalProxyFromEnv?: unknown }).setGlobalProxyFromEnv === "function";
	if (hasHttpProxyEnvironment() && !startedWithProxy && !supportsRuntimeProxy) {
		return " HTTP(S)_PROXY is set, but this Node release needs `NODE_USE_ENV_PROXY=1` (or `--use-env-proxy`) at startup to use it.";
	}
	if (!hasHttpProxyEnvironment() && process.env["ALL_PROXY"]?.trim()) {
		return " Node's built-in fetch does not use ALL_PROXY; set HTTPS_PROXY (and optionally HTTP_PROXY) instead.";
	}
	return undefined;
}

function hasHttpProxyEnvironment(): boolean {
	return ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"].some((name) => Boolean(process.env[name]?.trim()));
}

function hasProxyEnvironment(): boolean {
	return hasHttpProxyEnvironment() || Boolean(process.env["ALL_PROXY"]?.trim());
}

/** Backwards-compatible catalog-specific entry point. */
export function fetchLiveCatalog(url: string, init: RequestInit = {}): Promise<Response> {
	if (init.method !== undefined && init.method.toUpperCase() !== "GET")
		throw new Error("Live catalog discovery supports GET requests only.");
	if (init.body !== undefined) throw new Error("Live catalog discovery does not accept a request body.");
	return fetchProviderRequest(url, init);
}

async function bodyText(body: Exclude<NonNullable<RequestInit["body"]>, ReadableStream>): Promise<string> {
	if (typeof body === "string") return body;
	if (body instanceof URLSearchParams) return body.toString();
	if (body instanceof Blob) return body.text();
	if (body instanceof ArrayBuffer || ArrayBuffer.isView(body))
		return Buffer.from(body instanceof ArrayBuffer ? body : body.buffer).toString("utf8");
	return String(body);
}

function windowsSystemFetch(
	url: string,
	method: string,
	initHeaders: RequestInit["headers"],
	body: string | undefined,
	signal: AbortSignal | null | undefined,
): Promise<Response> {
	return new Promise<Response>((resolve, reject) => {
		if (signal?.aborted) {
			reject(new DOMException("The operation was aborted.", "AbortError"));
			return;
		}
		const headers = [...new Headers(initHeaders).entries()];
		const input = Buffer.from(JSON.stringify({ url, method, headers, body }), "utf8").toString("base64");
		const child = spawn(
			"powershell.exe",
			["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_HTTP_SCRIPT],
			{
				stdio: ["pipe", "pipe", "pipe"],
				windowsHide: true,
			},
		);
		const stdout: Buffer[] = [];
		const stderr: Buffer[] = [];
		let settled = false;
		const settle = (operation: () => void): void => {
			if (settled) return;
			settled = true;
			signal?.removeEventListener("abort", abort);
			operation();
		};
		const abort = (): void => {
			child.kill();
			settle(() => reject(new DOMException("The operation was aborted.", "AbortError")));
		};
		child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
		child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
		child.once("error", (error) => settle(() => reject(error)));
		child.once("close", (code) => {
			if (signal?.aborted) {
				settle(() => reject(new DOMException("The operation was aborted.", "AbortError")));
				return;
			}
			if (code !== 0) {
				settle(() =>
					reject(
						new Error(
							`Windows HTTP request failed (${code ?? "unknown"}): ${Buffer.concat(stderr).toString("utf8").trim()}`,
						),
					),
				);
				return;
			}
			try {
				const response = JSON.parse(
					Buffer.from(Buffer.concat(stdout).toString("utf8"), "base64").toString("utf8"),
				) as WindowsHttpResponse;
				settle(() =>
					resolve(
						new Response(response.body, {
							status: response.status,
							statusText: response.statusText,
							headers: response.headers,
						}),
					),
				);
			} catch (error) {
				settle(() => reject(error));
			}
		});
		signal?.addEventListener("abort", abort, { once: true });
		child.stdin.end(input);
	});
}
