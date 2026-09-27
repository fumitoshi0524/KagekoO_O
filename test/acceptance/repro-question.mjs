import { execFile } from "node:child_process";
import { createServer } from "node:http";
import { createWriteStream } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import * as pty from "node-pty";

const root = "F:/projects/Kageko/KagekoO_O";
const cli = path.join(root, "apps", "kageko", "dist", "main.mjs");
const execute = promisify(execFile);
const fixtureHome = process.env.KAGEKO_PTY_HOME;
const log = createWriteStream("C:/Users/15601/AppData/Local/Temp/pty-question-stream.log");
const env = {
	...process.env,
	KAGEKO_HOME: fixtureHome,
	KAGEKO_DATA_DIR: fixtureHome,
	KAGEKO_LOG_LEVEL: "off",
	KAGEKO_MODEL_PROVIDER: "custom",
	KAGEKO_MODEL_NAME: "acceptance-model",
	KAGEKO_API_KEY: "acceptance-key",
	KAGEKO_MAX_CONTEXT_SIZE: "32768",
	NO_PROXY: "127.0.0.1,localhost",
	no_proxy: "127.0.0.1,localhost",
};
let output = "";

const model = await startModel();
env.KAGEKO_BASE_URL = model.baseUrl;
for (const args of [
	["config", "set", "model.maxContextSize", "32768"],
	["config", "set", "model.provider", '"custom"'],
	["config", "set", "model.modelName", '"acceptance-model"'],
	["config", "set", "model.baseUrl", JSON.stringify(env.KAGEKO_BASE_URL)],
	["trust", "grant"],
])
	await execute(process.execPath, [cli, ...args], { cwd: fixtureHome, env, windowsHide: true });

const terminal = pty.spawn(process.execPath, [cli], {
	cwd: fixtureHome,
	env,
	name: "xterm-256color",
	cols: 140,
	rows: 50,
});
terminal.onData((chunk) => {
	output += chunk;
	log.write(chunk);
});
await waitForText(0, "Ask Kageko", "composer");
console.error("T0 composer ready", Date.now());

// newSessionJourney equivalent
let mark = await open("/new", "New session", "Title (optional)");
await fillForm("interactive-alpha");
await waitForText(mark, "Session “interactive-alpha” created.", "new session creation");
console.error("T1 session created", Date.now());
// the batch inspects the session list through a second CLI process here
await execute(process.execPath, [cli, "session", "list", "--json"], { cwd: fixtureHome, env, windowsHide: true });
console.error("T2 cli session list done", Date.now());

mark = output.length;
await submitText("PTY question alpha");
console.error("T3 prompt submitted", Date.now());
await waitForText(mark, "ask_user", "tool call visible", 20_000);
console.error("T4 ask_user visible", Date.now());
await waitForText(mark, "Type your answer…", "question input ownership", 30_000);
console.error("T5 modal open", Date.now());
terminal.write("\r");
await waitForText(mark, "Runtime observed Alpha", "question answered", 30_000);
console.error("T6 answered", Date.now());
terminal.kill();
process.exit(0);

async function open(command, title, readyText = "Search: type to filter", timeoutMs = 15_000) {
	const mark = output.length;
	await submitText(command);
	await waitForText(mark, title, `${command} panel`, timeoutMs);
	await waitForText(mark, readyText, `${command} input ownership`, timeoutMs);
	await delay(300);
	return mark;
}
async function fillForm(value) {
	await paste(value);
	await delay(150);
	pressEnter();
	await delay(250);
}
async function submitText(value) {
	await paste(value);
	await delay(150);
	pressEnter();
	await delay(250);
}
async function paste(value) {
	terminal.write(`\x1b[200~${value}\x1b[201~`);
	await delay(60);
}
function pressEnter() {
	terminal.write("\r");
}
async function waitForText(mark, text, label, timeoutMs = 15_000) {
	const deadline = Date.now() + timeoutMs;
	while (!visibleText(output.slice(mark)).includes(text)) {
		if (Date.now() >= deadline) {
			console.error(`TIMEOUT waiting for ${label}; tail:`);
			console.error(visibleText(output.slice(-3000)));
			terminal.kill();
			process.exit(1);
		}
		await delay(25);
	}
}
function visibleText(value) {
	const ESC = String.fromCharCode(27);
	const BEL = String.fromCharCode(7);
	return value
		.replace(new RegExp(`${ESC}\\][^${BEL}]*(?:${BEL}|${ESC}\\\\)`, "g"), "")
		.replace(new RegExp(`${ESC}\\[[0-?]*[ -/]*[@-~]`, "g"), "");
}
function delay(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
async function startModel() {
	const server = createServer((request, response) => {
		let body = "";
		request.on("data", (chunk) => (body += String(chunk)));
		request.on("end", () => {
			if (request.method === "GET" && request.url?.endsWith("/models")) {
				response.writeHead(200, { "content-type": "application/json" });
				response.end(
					JSON.stringify({
						data: [{ id: "acceptance-model", context_length: 65_536, max_context_size: 32_768 }],
					}),
				);
				return;
			}
			let input = {};
			try {
				input = JSON.parse(body);
			} catch {
				// Malformed requests intentionally retain the empty request body.
			}
			const messages = Array.isArray(input.messages) ? input.messages : [];
			const latestUserIndex = messages.findLastIndex((message) => message?.role === "user");
			const latestUserContent = messages[latestUserIndex]?.content ?? "";
			const latestUserText =
				typeof latestUserContent === "string" ? latestUserContent : JSON.stringify(latestUserContent);
			const turnMessages = messages.slice(latestUserIndex + 1);
			const hasToolResult = turnMessages.some((message) => message?.role === "tool");
			const latestTool = turnMessages.findLast((message) => message?.role === "tool")?.content ?? "";
			if (latestUserText.includes("PTY question")) {
				if (hasToolResult) return sendCompletion(response, `Runtime observed ${latestTool}`, input.stream === true);
				return sendToolCall(
					response,
					"ask_user",
					{ question: "Which runtime option?", options: ["Alpha", "Beta"] },
					input.stream === true,
				);
			}
			return sendCompletion(response, "ok", input.stream === true);
		});
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	return { baseUrl: `http://127.0.0.1:${address.port}/v1`, close: () => server.close() };
}
function sendCompletion(response, content, streaming) {
	if (streaming) {
		response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "close" });
		response.end(
			`data: ${JSON.stringify({ choices: [{ delta: { content }, finish_reason: "stop" }] })}\n\ndata: [DONE]\n\n`,
		);
		return;
	}
	response.writeHead(200, { "content-type": "application/json", connection: "close" });
	response.end(JSON.stringify({ choices: [{ message: { role: "assistant", content }, finish_reason: "stop" }] }));
}
function sendToolCall(response, name, args, streaming) {
	const id = `question-${Date.now()}`;
	const toolCall = { id, type: "function", function: { name, arguments: JSON.stringify(args) } };
	if (streaming) {
		response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache", connection: "close" });
		response.end(
			`data: ${JSON.stringify({ choices: [{ delta: { tool_calls: [{ index: 0, ...toolCall }] }, finish_reason: "tool_calls" }] })}\n\ndata: [DONE]\n\n`,
		);
		return;
	}
	response.writeHead(200, { "content-type": "application/json", connection: "close" });
	response.end(
		JSON.stringify({
			choices: [{ message: { role: "assistant", content: null, tool_calls: [toolCall] }, finish_reason: "tool_calls" }],
		}),
	);
}
