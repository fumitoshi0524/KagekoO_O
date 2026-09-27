/**
 * Hermes-compatible GitHub Copilot ACP provider.
 *
 * ACP is deliberately not routed through fetch or the OpenAI-compatible
 * registry. Hermes starts `copilot --acp --stdio` for each request and speaks
 * JSON-RPC over the child process' stdin/stdout.
 */
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface, type Interface } from "node:readline";
import { isAbsolute, relative, resolve } from "node:path";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import type { ChatMessage, ChatTool, Provider, ProviderChatOptions, ProviderChatResponse, ToolCall } from "../types.js";
import { ProviderProtocolError } from "../errors.js";

const DEFAULT_TIMEOUT_MS = 900_000;
const ACP_BASE_URL = "acp://copilot";

export interface CopilotAcpProviderOptions {
	command?: string;
	args?: string[];
	cwd?: string;
	timeoutMs?: number;
}

export class CopilotAcpProvider implements Provider {
	private readonly defaults: CopilotAcpProviderOptions;

	constructor(options: CopilotAcpProviderOptions = {}) {
		this.defaults = options;
	}

	async chat(options: ProviderChatOptions): Promise<ProviderChatResponse> {
		const command =
			options.providerOptions?.acpCommand ??
			this.defaults.command ??
			process.env["HERMES_COPILOT_ACP_COMMAND"] ??
			process.env["COPILOT_CLI_PATH"] ??
			"copilot";
		const args = options.providerOptions?.acpArgs ?? this.defaults.args ?? resolveAcpArgs();
		const cwd = resolve(options.providerOptions?.acpCwd ?? this.defaults.cwd ?? process.cwd());
		const timeoutMs = options.providerOptions?.acpTimeoutMs ?? this.defaults.timeoutMs ?? DEFAULT_TIMEOUT_MS;
		const prompt = formatAcpPrompt(options.messages, options.modelName, options.tools);
		const session = new AcpSession(command, args, cwd, timeoutMs, options);
		const raw = await session.run(prompt);
		const { toolCalls, content } = extractToolCalls(raw.text);
		if (content) options.onTextDelta?.(content);
		if (raw.reasoning) options.onThinkingDelta?.(raw.reasoning);
		for (const call of toolCalls)
			options.onToolCallDelta?.({ id: call.id, name: call.name, argumentsPartial: JSON.stringify(call.arguments) });
		return {
			content,
			toolCalls,
			finishReason: toolCalls.length > 0 ? "tool_calls" : "stop",
			usage: { promptTokens: 0, completionTokens: 0 },
		};
	}
}

class AcpSession {
	private readonly child: ChildProcessWithoutNullStreams;
	private readonly lines: Interface;
	private readonly lineIterator: AsyncIterator<string>;
	private nextId = 0;

	constructor(
		command: string,
		args: string[],
		private readonly cwd: string,
		private readonly timeoutMs: number,
		private readonly options: ProviderChatOptions,
	) {
		this.child = spawn(command, args, {
			cwd,
			env: { ...process.env, HOME: process.env["HOME"] ?? process.env["USERPROFILE"] ?? cwd },
			stdio: ["pipe", "pipe", "pipe"],
		});
		this.lines = createInterface({ input: this.child.stdout });
		this.lineIterator = this.lines[Symbol.asyncIterator]();
	}

	async run(prompt: string): Promise<{ text: string; reasoning: string }> {
		const textParts: string[] = [];
		const reasoningParts: string[] = [];
		try {
			await this.request("initialize", {
				protocolVersion: 1,
				clientCapabilities: { fs: { readTextFile: true, writeTextFile: true } },
				clientInfo: { name: "kageko", title: "Kageko", version: "0.1.0" },
			});
			const result = await this.request("session/new", { cwd: this.cwd, mcpServers: [] });
			const sessionId = String(result?.sessionId ?? "").trim();
			if (!sessionId) throw new ProviderProtocolError("Copilot ACP did not return a sessionId");
			await this.request(
				"session/prompt",
				{ sessionId, prompt: [{ type: "text", text: prompt }] },
				textParts,
				reasoningParts,
			);
			return { text: textParts.join(""), reasoning: reasoningParts.join("") };
		} finally {
			this.lines.close();
			if (!this.child.killed) this.child.kill();
		}
	}

	private async request(
		method: string,
		params: Record<string, unknown>,
		textParts?: string[],
		reasoningParts?: string[],
	): Promise<any> {
		const id = ++this.nextId;
		this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
		while (true) {
			const line = await nextLine(this.lineIterator, this.timeoutMs, method);
			let message: any;
			try {
				message = JSON.parse(line);
			} catch {
				continue;
			}
			if (message?.method === "session/update") {
				const update = message.params?.update ?? {};
				const kind = String(update.sessionUpdate ?? "");
				const value = typeof update.content?.text === "string" ? update.content.text : "";
				if (kind === "agent_message_chunk") textParts?.push(value);
				if (kind === "agent_thought_chunk") reasoningParts?.push(value);
				continue;
			}
			if (typeof message?.method === "string" && message.id !== undefined) {
				await this.respondToServerRequest(message);
				continue;
			}
			if (message?.id !== id) continue;
			if (message.error)
				throw new ProviderProtocolError(
					`Copilot ACP ${method} failed: ${message.error.message ?? JSON.stringify(message.error)}`,
				);
			return message.result;
		}
	}

	private async respondToServerRequest(message: any): Promise<void> {
		const method = String(message.method);
		const params = message.params ?? {};
		let response: Record<string, unknown>;
		try {
			if (method === "fs/read_text_file") {
				const file = safeSessionPath(this.cwd, String(params.path ?? ""));
				response = { result: { content: await readFile(file, "utf8") } };
			} else if (method === "fs/write_text_file") {
				const file = safeSessionPath(this.cwd, String(params.path ?? ""));
				await mkdir(resolve(file, ".."), { recursive: true });
				await writeFile(file, String(params.content ?? ""), "utf8");
				response = { result: null };
			} else if (method === "session/request_permission") {
				response = { result: { outcome: { outcome: "cancelled" } } };
			} else {
				response = {
					error: { code: -32601, message: `ACP client method '${method}' is not supported by Kageko yet.` },
				};
			}
		} catch (error) {
			response = { error: { code: -32602, message: error instanceof Error ? error.message : String(error) } };
		}
		this.child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id: message.id, ...response })}\n`);
	}
}

async function nextLine(iterator: AsyncIterator<string>, timeoutMs: number, method: string): Promise<string> {
	let timer: ReturnType<typeof setTimeout> | undefined;
	try {
		const next = iterator.next();
		const timeout = new Promise<never>((_, reject) => {
			timer = setTimeout(
				() => reject(new ProviderProtocolError(`Timed out waiting for Copilot ACP response to ${method}`)),
				timeoutMs,
			);
		});
		const result = await Promise.race([next, timeout]);
		if (result.done) throw new ProviderProtocolError("Copilot ACP process exited before returning a JSON-RPC response");
		return result.value;
	} finally {
		if (timer) clearTimeout(timer);
	}
}

function resolveAcpArgs(): string[] {
	const raw = process.env["HERMES_COPILOT_ACP_ARGS"]?.trim();
	return raw ? raw.split(/\s+/) : ["--acp", "--stdio"];
}

function formatAcpPrompt(messages: ChatMessage[], model: string, tools?: ChatTool[]): string {
	const sections = [
		"You are being used as the active ACP agent backend for Hermes.",
		"Use ACP capabilities to complete tasks.",
		"IMPORTANT: If you take an action with a tool, you MUST output tool calls using <tool_call>{...}</tool_call> blocks with JSON exactly in OpenAI function-call shape.",
		"If no tool is needed, answer normally.",
		`Hermes requested model hint: ${model}`,
	];
	if (tools?.length) {
		const specs = tools.map((tool) => ({
			name: tool.function.name.trim(),
			description: tool.function.description,
			parameters: tool.function.parameters,
		}));
		sections.push(
			"Available tools (OpenAI function schema). When using a tool, emit ONLY <tool_call>{...}</tool_call> with one JSON object containing id/type/function{name,arguments}. arguments must be a JSON string\n" +
				JSON.stringify(specs),
		);
	}
	const transcript = messages.flatMap((message) => {
		const content = renderContent(message.content);
		if (!content) return [];
		const role = message.role.charAt(0).toUpperCase() + message.role.slice(1);
		return [`${role}:\n${content}`];
	});
	if (transcript.length) sections.push(`Conversation transcript:\n\n${transcript.join("\n\n")}`);
	sections.push("Continue the conversation from the latest user request.");
	return sections.join("\n\n");
}

function renderContent(content: ChatMessage["content"]): string {
	if (typeof content === "string") return content.trim();
	return content
		.map((part) => (typeof part === "string" ? part : part.type === "text" ? (part.text ?? "") : ""))
		.join("\n")
		.trim();
}

function extractToolCalls(text: string): { toolCalls: ToolCall[]; content: string } {
	const toolCalls: ToolCall[] = [];
	const consumed: Array<[number, number]> = [];
	const pattern = /<tool_call>\s*(\{.*?\})\s*<\/tool_call>/gs;
	for (const match of text.matchAll(pattern)) {
		try {
			const value = JSON.parse(match[1] ?? "");
			const fn = value?.function;
			if (typeof fn?.name === "string" && fn.name.trim()) {
				const args = typeof fn.arguments === "string" ? fn.arguments : JSON.stringify(fn.arguments ?? {});
				toolCalls.push({
					id: typeof value.id === "string" && value.id ? value.id : `acp_call_${toolCalls.length + 1}`,
					name: fn.name.trim(),
					arguments: parseObject(args),
				});
				consumed.push([match.index ?? 0, (match.index ?? 0) + match[0].length]);
			}
		} catch {
			// Match Hermes: malformed tool blocks remain visible as assistant text.
		}
	}
	let content = text;
	for (const [start, end] of consumed.reverse()) content = content.slice(0, start) + content.slice(end);
	return {
		toolCalls,
		content: content
			.split("\n")
			.map((line) => line.trim())
			.filter(Boolean)
			.join("\n")
			.trim(),
	};
}

function parseObject(value: string): Record<string, unknown> {
	try {
		const parsed = JSON.parse(value);
		return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
	} catch {
		return {};
	}
}

function safeSessionPath(cwd: string, target: string): string {
	const file = resolve(target);
	if (!isAbsolute(target) || (relative(resolve(cwd), file) && relative(resolve(cwd), file).startsWith(".."))) {
		throw new Error(`ACP file-system paths must be absolute and within session cwd '${cwd}'.`);
	}
	return file;
}

export { ACP_BASE_URL };
