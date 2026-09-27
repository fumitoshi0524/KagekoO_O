import { spawn } from "node:child_process";

const NATIVE_FETCH = globalThis.fetch;
const WINDOWS_HTTP_SCRIPT = `
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [Text.Encoding]::UTF8
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
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

interface SystemResponse {
	status: number;
	statusText: string;
	headers: Record<string, string>;
	body: string;
}

/** Every OAuth provider shares this transport. On Windows it uses the system
 * HTTP stack, which honors the machine's real egress route; it never changes
 * an OAuth request into a cached/local result. */
export async function providerFetch(input: string | URL, init: RequestInit = {}): Promise<Response> {
	if (process.platform !== "win32" || globalThis.fetch !== NATIVE_FETCH) return globalThis.fetch(input, init);
	if (init.body instanceof ReadableStream) throw new Error("OAuth requests cannot use a streaming body.");
	const body = init.body === undefined || init.body === null ? undefined : await bodyText(init.body);
	return windowsSystemFetch(
		String(input),
		init.method ?? "GET",
		[...new Headers(init.headers).entries()],
		body,
		init.signal,
	);
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
	headers: readonly [string, string][],
	body: string | undefined,
	signal: AbortSignal | null | undefined,
): Promise<Response> {
	return new Promise((resolve, reject) => {
		if (signal?.aborted) return reject(new DOMException("The operation was aborted.", "AbortError"));
		const child = spawn(
			"powershell.exe",
			["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", WINDOWS_HTTP_SCRIPT],
			{ stdio: ["pipe", "pipe", "pipe"], windowsHide: true },
		);
		const stdout: Buffer[] = [];
		const stderr: Buffer[] = [];
		const abort = (): void => {
			child.kill();
		};
		child.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
		child.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));
		child.once("error", reject);
		child.once("close", (code) => {
			signal?.removeEventListener("abort", abort);
			if (signal?.aborted) return reject(new DOMException("The operation was aborted.", "AbortError"));
			if (code !== 0)
				return reject(
					new Error(
						`Windows OAuth HTTP request failed (${code ?? "unknown"}): ${Buffer.concat(stderr).toString("utf8").trim()}`,
					),
				);
			try {
				const response = JSON.parse(
					Buffer.from(Buffer.concat(stdout).toString("utf8"), "base64").toString("utf8"),
				) as SystemResponse;
				resolve(
					new Response(response.body, {
						status: response.status,
						statusText: response.statusText,
						headers: response.headers,
					}),
				);
			} catch (error) {
				reject(error);
			}
		});
		signal?.addEventListener("abort", abort, { once: true });
		child.stdin.end(Buffer.from(JSON.stringify({ url, method, headers, body }), "utf8").toString("base64"));
	});
}
