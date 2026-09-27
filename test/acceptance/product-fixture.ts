import { spawn } from "node:child_process";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { createServer, type Server, type ServerResponse } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "../..");
export const cli = path.join(root, "apps", "kageko", "dist", "main.mjs");

export interface ProductEnvironment {
	readonly home: string;
	readonly workspace: string;
	readonly env: NodeJS.ProcessEnv;
	cleanup(): Promise<void>;
}

export interface CommandResult {
	readonly code: number;
	readonly stdout: string;
	readonly stderr: string;
}

export async function createProductEnvironment(extraEnv: NodeJS.ProcessEnv = {}): Promise<ProductEnvironment> {
	const home = await mkdtemp(path.join(tmpdir(), "kageko-product-"));
	const workspace = path.join(home, "workspace");
	await mkdir(workspace, { recursive: true });
	return {
		home,
		workspace,
		env: {
			...process.env,
			KAGEKO_HOME: home,
			KAGEKO_MODEL_PROVIDER: "faux",
			KAGEKO_MODEL_NAME: "faux",
			KAGEKO_MAX_CONTEXT_SIZE: "32768",
			KAGEKO_LOG_LEVEL: "off",
			...extraEnv,
		},
		cleanup: () => rm(home, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }),
	};
}

export async function runProduct(
	product: ProductEnvironment,
	args: readonly string[],
	extraEnv: NodeJS.ProcessEnv = {},
): Promise<CommandResult> {
	return new Promise((resolve, reject) => {
		const child = spawn(process.execPath, [cli, ...args], {
			cwd: product.workspace,
			env: { ...product.env, ...extraEnv },
			stdio: ["ignore", "pipe", "pipe"],
			windowsHide: true,
		});
		let stdout = "";
		let stderr = "";
		let timedOut = false;
		const timeout = setTimeout(() => {
			timedOut = true;
			child.kill();
		}, 20_000);
		child.stdout.setEncoding("utf8");
		child.stderr.setEncoding("utf8");
		child.stdout.on("data", (data: string) => {
			stdout += data;
		});
		child.stderr.on("data", (data: string) => {
			stderr += data;
		});
		child.once("error", (error) => {
			clearTimeout(timeout);
			reject(error);
		});
		child.once("close", (code) => {
			clearTimeout(timeout);
			resolve({
				code: timedOut ? -1 : (code ?? -1),
				stdout,
				stderr: timedOut ? `${stderr}\nTimed out after 20000ms: kageko ${args.join(" ")}` : stderr,
			});
		});
	});
}

export function json(result: CommandResult): unknown {
	return JSON.parse(result.stdout) as unknown;
}

export async function startLearningModel(): Promise<{ readonly baseUrl: string; close(): Promise<void> }> {
	const server = createServer(async (request, response) => {
		let body = "";
		for await (const chunk of request) body += String(chunk);
		const input = JSON.parse(body) as {
			messages?: Array<{ role?: string; content?: unknown }>;
			stream?: boolean;
			tools?: Array<{ function?: { name?: unknown } }>;
		};
		const transcript = JSON.stringify(input.messages ?? []);
		const toolNames = Array.isArray(input.tools)
			? input.tools.map((tool) => String(tool?.function?.name ?? ""))
			: [];
		// The resident learner agent conversation carries only the five learner
		// tools; answer its proposal call with description-only args so the
		// resident synthesizer path (keyed above) still executes unchanged.
		if (toolNames.includes("propose_capability") || toolNames.includes("propose_skill")) {
			const hasToolResult = (input.messages ?? []).some((message) => message?.role === "tool");
			if (hasToolResult) return sendCompletion(response, "Learner run completed.", input.stream === true);
			if (toolNames.includes("propose_capability")) {
				const learnerMcp = transcript.includes("remote test feed");
				return sendToolCall(response, "propose_capability", {
					description: learnerMcp
						? "Read a remote test feed for recurring release checks"
						: "Create a concise release note for repeated release work",
					context: learnerMcp ? "remote test feed" : "release validation workflow",
					proposedKind: learnerMcp ? "mcp" : "tool",
				});
			}
			return sendCompletion(response, "No durable skill is justified by the evidence.", input.stream === true);
		}
		if (transcript.includes("safe external-command wrapper")) {
			const isMcp = transcript.includes("remote test feed");
			const content = isMcp
				? JSON.stringify({
						manifest: {
							kind: "mcp",
							name: "release-feed",
							description: "Read the reusable release feed.",
							command: "node",
							args: [],
						},
						code: mcpServerCode(),
					})
				: JSON.stringify({
						manifest: {
							kind: "tool",
							name: "release-note",
							description: "Create one concise release note.",
							parameters: { type: "object", properties: { subject: { type: "string" } }, required: ["subject"] },
							command: "node",
							args: ["{{__args_json}}"],
						},
						code: "const { subject = 'release' } = JSON.parse(process.argv[2] ?? '{}'); console.log(`release-note:${subject}`);",
					});
			return sendCompletion(response, content, input.stream === true);
		}
		if (transcript.includes("Derive one genuinely reusable procedural skill")) {
			return sendCompletion(
				response,
				"name: release-validation\ndescription: Validate a release before it is published.\n---\n1. Run the product acceptance suite.\n2. Inspect the generated artifacts.\n3. Report only verified results.",
				input.stream === true,
			);
		}
		const isMcp = transcript.includes("remote test feed");
		return sendToolCall(response, "need_capability", {
			description: isMcp
				? "Read a remote test feed for recurring release checks"
				: "Create a concise release note for repeated release work",
			context: isMcp ? "remote test feed" : "release validation workflow",
			proposedKind: isMcp ? "mcp" : "tool",
			evidence: {
				scope: isMcp ? "external_service" : "workflow",
				futureTasks: ["weekly release", "hotfix release"],
				alternativesChecked: ["existing built-in tools"],
			},
		});
	});
	await new Promise<void>((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", () => resolve());
	});
	const address = server.address();
	if (!address || typeof address === "string") throw new Error("Learning model did not receive a TCP address");
	return { baseUrl: `http://127.0.0.1:${address.port}/v1`, close: () => closeServer(server) };
}

function sendText(response: ServerResponse, content: string): void {
	response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
	response.end(
		`data: ${JSON.stringify({ choices: [{ delta: { content }, finish_reason: "stop" }] })}\n\ndata: [DONE]\n\n`,
	);
}

function sendCompletion(response: ServerResponse, content: string, streaming: boolean): void {
	if (streaming) return sendText(response, content);
	response.writeHead(200, { "content-type": "application/json" });
	response.end(JSON.stringify({ choices: [{ message: { role: "assistant", content }, finish_reason: "stop" }] }));
}

function sendToolCall(response: ServerResponse, name: string, args: Record<string, unknown>): void {
	response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
	response.end(
		`data: ${JSON.stringify({ choices: [{ delta: { tool_calls: [{ index: 0, id: "capability-call", type: "function", function: { name, arguments: JSON.stringify(args) } }] }, finish_reason: "tool_calls" }] })}\n\ndata: [DONE]\n\n`,
	);
}

function mcpServerCode(): string {
	return [
		"const readline = require('node:readline');",
		"readline.createInterface({ input: process.stdin }).on('line', (line) => {",
		"  const request = JSON.parse(line);",
		"  if (request.id === undefined) return;",
		"  const result = request.method === 'initialize'",
		"    ? { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'release-feed', version: '1.0.0' } }",
		"    : request.method === 'tools/list' ? { tools: [{ name: 'latest_release', description: 'Return release status', inputSchema: { type: 'object' } }] } : { content: [{ type: 'text', text: 'ok' }] };",
		"  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }) + '\\n');",
		"});",
	].join("\n");
}

function closeServer(server: Server): Promise<void> {
	return new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
}
