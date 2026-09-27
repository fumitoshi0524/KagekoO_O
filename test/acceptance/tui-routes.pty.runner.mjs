import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import * as pty from "node-pty";

const root = path.resolve(import.meta.dirname, "../..");
const cli = path.join(root, "apps", "kageko", "dist", "main.mjs");
const execute = promisify(execFile);
const externalHome = process.env.KAGEKO_PTY_HOME;
const home = externalHome ?? (await mkdtemp(path.join(tmpdir(), "kageko-tui-routes-")));
let terminal;
let output = "";
let exited = false;
let modelServer;

try {
	const contract = JSON.parse(await readFile(path.join(import.meta.dirname, "contracts", "tui-routes.json"), "utf8"));
	validateRouteContract(contract);
	modelServer = await startModelServer();
	await configureReturningUser();
	terminal = pty.spawn(process.execPath, [cli], {
		cwd: home,
		env: {
			...process.env,
			KAGEKO_HOME: home,
			KAGEKO_DATA_DIR: path.join(home, ".kageko"),
			CODEX_HOME: path.join(home, ".codex"),
			KAGEKO_LOG_LEVEL: "off",
			// Route smoke never needs a real OAuth authorization side effect.
			KAGEKO_DISABLE_EXTERNAL_BROWSER: "1",
			KAGEKO_MODEL_PROVIDER: "custom",
			KAGEKO_MODEL_NAME: "acceptance-model",
			KAGEKO_API_KEY: "acceptance-key",
			KAGEKO_BASE_URL: modelServer.baseUrl,
		},
		name: "xterm-256color",
		cols: 140,
		rows: 50,
		useConpty: false,
	});
	terminal.onData((chunk) => {
		output += chunk;
	});
	terminal.onExit(() => {
		exited = true;
	});
	await waitFor(() => output.includes("Ask Kageko"), "initial composer", 15_000);
	const expected = new Map([
		["new", "New session"],
		["sessions", "Sessions"],
		["fork", "Fork the current session · (no arguments)"],
		["rename", "Rename session"],
		["archive", "Session archive"],
		["delete", "Delete session"],
		["help", "Help"],
		["activity", "Activity"],
		["theme", "Theme"],
		["undo", "Session timeline"],
		["interactions", "No approval or question is waiting."],
		["capabilities", "Capabilities"],
		["cron", "Create scheduled prompt"],
		["shell", "Embedded shell"],
		["goal", "Session goal"],
		["plan", "Coordinator plan"],
		["compact", "Compact context"],
		["memory", "Memory"],
		["learn", "pending proposals"],
		["tools", "builtin"],
		["skills", "Reload skills"],
		["plugins", "Install plugin"],
		["mcp", "Reconnect capabilities"],
		["model", "Choose which agent receives"],
		["graph", "Add subagent profile"],
		["trust", "Revoke trust"],
		["config", "Settings"],
		["setup", "Provider · step 1 of 2"],
		// The auth title is painted before credential discovery completes. Waiting
		// for a real provider prevents Esc from racing the async panel replacement.
		["auth", "OpenAI Codex (OAuth)"],
	]);
	const immediateCommands = new Set(["fork", "cancel", "interactions"]);
	for (const command of contract.slashCommands) {
		if (command === "exit") continue;
		const mark = output.length;
		await typeKeys(`/${command}`);
		await delay(400);
		terminal.write("\r");
		const label = expected.get(command);
		if (label) await waitFor(() => output.slice(mark).includes(label), `/${command} open`, 15_000);
		else await delay(200);
		if (immediateCommands.has(command)) {
			await waitFor(() => output.slice(mark).includes("Ask Kageko"), `/${command} return to composer`, 15_000);
			if (command === "fork") {
				// The command may finish opening its confirmation after the composer
				// first reappears. Cancel it before sending the next slash command.
				await delay(750);
				terminal.write("\x1b");
				await delay(250);
			}
			continue;
		}
		const closeMark = output.length;
		for (let attempt = 0; attempt < 3; attempt++) {
			terminal.write(command === "shell" && attempt === 0 ? "\x1bOQ" : "\x1b");
			try {
				await waitFor(() => output.slice(closeMark).includes("Ask Kageko"), `/${command} close to composer`, 5_000);
				break;
			} catch (error) {
				if (attempt === 2) throw error;
			}
		}
	}
	const exitMark = output.length;
	await typeKeys("/exit");
	await delay(400);
	terminal.write("\x1bOM");
	await waitFor(() => exited || output.slice(exitMark).includes("Session closed"), "/exit", 15_000);
	console.log("PASS: 30 public + 1 hidden canonical TUI routes are unique; 7 aliases are disjoint (smoke only)");
} catch (error) {
	console.error(error instanceof Error ? error.stack : String(error));
	process.exitCode = 1;
} finally {
	if (terminal && !exited) {
		try {
			terminal.kill();
		} catch {
			/* terminal already closed */
		}
		await delay(500);
		if (!exited) {
			try {
				await execute("taskkill", ["/PID", String(terminal.pid), "/T", "/F"], { windowsHide: true });
			} catch {
				/* the PTY can exit between the check and taskkill */
			}
		}
	}
	await modelServer?.close();
	if (!externalHome) {
		await delay(500);
		try {
			await rm(home, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
		} catch (error) {
			console.error(`Could not clean PTY fixture: ${error instanceof Error ? error.message : String(error)}`);
		}
	}
	// node-pty's WinPTY handle can keep Node's event loop alive after the child
	// process has been force-terminated. This isolated owner has no other work.
	process.exit(process.exitCode ?? 0);
}

async function configureReturningUser() {
	const env = {
		...process.env,
		KAGEKO_HOME: home,
		KAGEKO_DATA_DIR: path.join(home, ".kageko"),
		CODEX_HOME: path.join(home, ".codex"),
		KAGEKO_LOG_LEVEL: "off",
		KAGEKO_MODEL_PROVIDER: "custom",
		KAGEKO_MODEL_NAME: "acceptance-model",
		KAGEKO_API_KEY: "acceptance-key",
		KAGEKO_BASE_URL: modelServer.baseUrl,
		KAGEKO_MAX_CONTEXT_SIZE: "32768",
	};
	for (const args of [
		["config", "set", "model.maxContextSize", "32768"],
		["config", "set", "model.provider", '"custom"'],
		["config", "set", "model.modelName", '"acceptance-model"'],
		["config", "set", "model.baseUrl", JSON.stringify(modelServer.baseUrl)],
		["trust", "grant"],
	])
		await execute(process.execPath, [cli, ...args], { cwd: home, env, windowsHide: true });
}

async function typeKeys(text) {
	terminal.write(`\x1b[200~${text}\x1b[201~`);
	await delay(50);
}

async function waitFor(condition, label, timeoutMs) {
	const deadline = Date.now() + timeoutMs;
	while (!condition()) {
		if (Date.now() >= deadline) throw new Error(`Timed out waiting for ${label}\n${output.slice(-3_000)}`);
		await delay(25);
	}
}

function delay(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

function validateRouteContract(contract) {
	const canonical = contract?.slashCommands;
	const aliases = contract?.aliases;
	if (!Array.isArray(canonical) || !aliases || typeof aliases !== "object" || Array.isArray(aliases)) {
		throw new Error("TUI route contract must contain slashCommands[] and aliases{}");
	}
	if (canonical.length !== 31 || canonical.filter((command) => command !== "interactions").length !== 30) {
		throw new Error(`Expected 30 public and one hidden canonical route, received ${canonical.length}`);
	}
	if (new Set(canonical).size !== canonical.length) throw new Error("Canonical TUI route contract contains duplicates");
	const aliasEntries = Object.entries(aliases);
	if (aliasEntries.length !== 7) throw new Error(`Expected 7 TUI aliases, received ${aliasEntries.length}`);
	for (const [alias, target] of aliasEntries) {
		if (canonical.includes(alias)) throw new Error(`Alias /${alias} duplicates a canonical command`);
		if (!canonical.includes(target)) throw new Error(`Alias /${alias} targets missing canonical command /${target}`);
	}
}

async function startModelServer() {
	const server = createServer((request, response) => {
		if (request.method === "GET" && request.url?.endsWith("/models")) {
			response.writeHead(200, { "content-type": "application/json" });
			response.end(
				JSON.stringify({ data: [{ id: "acceptance-model", context_length: 65_536, max_context_size: 32_768 }] }),
			);
			return;
		}
		response.writeHead(200, { "content-type": "application/json" });
		response.end(
			JSON.stringify({ choices: [{ message: { role: "assistant", content: "ok" }, finish_reason: "stop" }] }),
		);
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	if (!address || typeof address === "string")
		throw new Error("Route-smoke model server did not receive a TCP address");
	return {
		baseUrl: `http://127.0.0.1:${address.port}/v1`,
		close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
	};
}
