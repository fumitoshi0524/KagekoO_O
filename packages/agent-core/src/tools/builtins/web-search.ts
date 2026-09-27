import { createExternalFetchEvent } from "../../memory/learning/event.js";
import type { Tool, ToolContext } from "../types.js";
import { publicNetworkAccess } from "../accesses.js";

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MAX_BYTES = 2 * 1024 * 1024;

interface WebSearchArgs {
	query: string;
	limit?: number;
	timeout?: number;
}

interface SearchResult {
	title: string;
	url: string;
	snippet: string;
}

export const webSearchTool: Tool<WebSearchArgs> = {
	name: "web_search",
	description:
		"Search the web using DuckDuckGo Lite (no API key required). Returns top results with titles and snippets.",
	parameters: {
		type: "object",
		properties: {
			query: { type: "string", description: "Search query" },
			limit: { type: "number", description: "Maximum number of results (default 5, max 10)" },
			timeout: { type: "number", description: "Search timeout in milliseconds (default 30000)" },
		},
		required: ["query"],
	},
	resolveExecution() {
		return { accesses: publicNetworkAccess("search", "https://lite.duckduckgo.com", { sendsContent: true }) };
	},
	async execute({ query, limit = 5, timeout = DEFAULT_TIMEOUT_MS }: WebSearchArgs, { session }: ToolContext) {
		const count = Math.min(Math.max(Number(limit) || 5, 1), 10);
		const url = `https://lite.duckduckgo.com/lite/?q=${encodeURIComponent(query)}`;
		if (!/^https?:$/i.test(new URL(url).protocol)) {
			return { output: "Only HTTP/HTTPS URLs are allowed", isError: true };
		}
		let res: Response;
		const signal = AbortSignal.timeout(timeout);
		try {
			res = await fetch(url, {
				signal,
				headers: {
					"User-Agent": "Mozilla/5.0 (compatible; Kageko/0.1)",
					Accept: "text/html",
				},
			});
		} catch (err) {
			if (signal.aborted || (err as Error).name === "TimeoutError" || (err as Error).name === "AbortError") {
				return { output: `Search timed out after ${timeout}ms`, isError: true };
			}
			return { output: `Search failed: ${(err as Error).message}`, isError: true };
		}
		if (!res.ok) {
			res.body?.cancel?.().catch(() => {});
			return { output: `Search failed: ${res.status} ${res.statusText}`, isError: true };
		}
		let html: string;
		try {
			html = await readTextWithCap(res, DEFAULT_MAX_BYTES);
		} catch (err) {
			return { output: `Search failed: ${(err as Error).message}`, isError: true };
		}
		const results = parseDuckDuckGoLite(html).slice(0, count);
		if (results.length === 0) {
			return { output: "No results found." };
		}
		const output = results.map((r, i) => `${i + 1}. ${r.title}\n   ${r.url}\n   ${r.snippet}`).join("\n\n");
		session?.learningBus?.enqueue(
			createExternalFetchEvent("topic", { topic: query, content: output }, { toolName: "web_search" }),
		);
		return { output };
	},
};

async function readTextWithCap(res: Response, maxBytes: number): Promise<string> {
	const contentLength = res.headers?.get?.("content-length");
	if (contentLength && Number(contentLength) > maxBytes) {
		res.body?.cancel?.().catch(() => {});
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

function parseDuckDuckGoLite(html: string): SearchResult[] {
	const results: SearchResult[] = [];
	// DuckDuckGo lite results are rows with class "result-link" and "result-snippet".
	const linkRe = /<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
	const snippetRe = /<td[^>]+class="result-snippet"[^>]*>([\s\S]*?)<\/td>/gi;

	const links: { url: string; title: string }[] = [];
	let m: RegExpExecArray | null;
	while ((m = linkRe.exec(html)) !== null) {
		links.push({ url: decodeHtmlEntities(m[1]!), title: stripHtml(m[2]!) });
	}

	const snippets: string[] = [];
	while ((m = snippetRe.exec(html)) !== null) {
		snippets.push(stripHtml(m[1]!));
	}

	for (let i = 0; i < links.length; i++) {
		results.push({ ...links[i]!, snippet: snippets[i] ?? "" });
	}
	return results;
}

function stripHtml(raw: string): string {
	return raw
		.replace(/<[^>]+>/g, " ")
		.replace(/\s+/g, " ")
		.trim();
}

function decodeHtmlEntities(str: string): string {
	return str
		.replace(/&amp;/g, "&")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'");
}
