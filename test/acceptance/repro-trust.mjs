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
const log = createWriteStream("/tmp/pty-repro-stream.log");
const env = {
	...process.env,
	KAGEKO_HOME: fixtureHome,
	KAGEKO_DATA_DIR: fixtureHome,
	KAGEKO_LOG_LEVEL: "off",
	KAGEKO_MODEL_PROVIDER: "custom",
	KAGEKO_MODEL_NAME: "acceptance-model",
	KAGEKO_API_KEY: "acceptance-key",
	KAGEKO_BASE_URL: "http://127.0.0.1:9/v1",
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

// mirror managementJourney's trust block
let mark = await open("/trust", "Workspace trust");
await choose("Trust this workspace");
await waitForText(mark, "Workspace trusted.", "trust grant");
pressEscape();
await waitComposer();
mark = await open("/trust", "Workspace trust");
await choose("Trusted");
await waitForText(mark, "Workspace trust status", "trust status action");
await waitForText(mark, "State: trusted", "trust status detail");
await choose("Back to Trust");
await waitForText(mark, "Revoke trust", "trust status parent return");
pressEscape();
await waitComposer();
mark = await open("/trust", "Workspace trust");
console.error("OPEN-OK at", Date.now());
await choose("Revoke trust");
console.error("CHOSE at", Date.now());
await waitForText(mark, "Revoke trust for this workspace?", "trust revoke confirmation", 20_000);
console.error("CONFIRM-OK");
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
async function choose(label) {
	await paste(label);
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
function pressEscape() {
	terminal.write("\x1b");
}
async function waitComposer() {
	await delay(150);
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
		if (request.method === "GET" && request.url?.endsWith("/models")) {
			response.writeHead(200, { "content-type": "application/json" });
			response.end(
				JSON.stringify({
					object: "list",
					data: [
						{
							id: "acceptance-model",
							object: "model",
							owned_by: "acceptance",
							context_length: 65_536,
							max_context_size: 32_768,
							max_output_tokens: 8_192,
							capabilities: ["reasoning", "tools"],
							supported_reasoning_levels: ["low", "high"],
						},
					],
				}),
			);
			return;
		}
		response.writeHead(200, { "content-type": "application/json" });
		response.end(JSON.stringify({ choices: [{ message: { role: "assistant", content: "ok" } }] }));
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	return { baseUrl: `http://127.0.0.1:${address.port}/v1`, close: () => server.close() };
}
