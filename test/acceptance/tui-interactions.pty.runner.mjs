import { execFile } from "node:child_process";
import { appendFileSync } from "node:fs";
import { readFile, readdir, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { promisify } from "node:util";
import * as pty from "node-pty";

const root = path.resolve(import.meta.dirname, "../..");
const cli = process.env.KAGEKO_PTY_CLI ?? path.join(root, "apps", "kageko", "dist", "main.mjs");
const execute = promisify(execFile);
const ESC = String.fromCharCode(27);
const BEL = String.fromCharCode(7);
const OSC_SEQUENCE = new RegExp(`${ESC}\\][^${BEL}]*(?:${BEL}|${ESC}\\\\)`, "g");
const CSI_SEQUENCE = new RegExp(`${ESC}\\[[0-?]*[ -/]*[@-~]`, "g");
const batch = process.argv[2] ?? "core";
const fixtureHome = process.env.KAGEKO_PTY_HOME;
if (!fixtureHome) throw new Error("KAGEKO_PTY_HOME is required");
const env = {
	...process.env,
	KAGEKO_HOME: fixtureHome,
	// The TUI input history lives under KAGEKO_DATA_DIR; keep it inside the
	// fixture so submissions never touch the real user home.
	KAGEKO_DATA_DIR: fixtureHome,
	CODEX_HOME: path.join(fixtureHome, ".codex"),
	KAGEKO_LOG_LEVEL: "off",
	// This suite deliberately reaches OAuth cancellation states. It must never
	// open an authorization URL in the developer's real browser while doing so.
	KAGEKO_DISABLE_EXTERNAL_BROWSER: "1",
	KAGEKO_MODEL_PROVIDER: "custom",
	KAGEKO_MODEL_NAME: "acceptance-model",
	KAGEKO_API_KEY: "acceptance-key",
	KAGEKO_BASE_URL: "http://127.0.0.1:9/v1",
	KAGEKO_MAX_CONTEXT_SIZE: "32768",
	// The deterministic provider is process-local. Letting an inherited proxy
	// route loopback traffic can cross-wire concurrent streaming/non-streaming
	// CLI requests and makes the harness test the proxy instead of Kageko.
	NO_PROXY: [process.env.NO_PROXY, "127.0.0.1", "localhost"].filter(Boolean).join(","),
	no_proxy: [process.env.no_proxy, "127.0.0.1", "localhost"].filter(Boolean).join(","),
};
let terminal;
let output = "";
let exited = false;
let currentSessionId;
let learningModel;

try {
	learningModel = await startLearningModel();
	env.KAGEKO_BASE_URL = learningModel.baseUrl;
	await configure();
	await startTui();

	await newSessionJourney();
	if (batch === "core") {
		await themeJourney();
		await memoryJourney();
		await goalJourney();
		await cronJourney();
		await capabilitiesJourney();
	} else if (batch === "management") await managementJourney();
	else if (batch === "lifecycle") await lifecycleJourney();
	else if (batch === "learning") await learningJourney();
	else if (batch === "advanced") await advancedJourney();
	else if (batch === "graph") await graphJourney();
	else if (batch === "matrix") await matrixJourney();
	else if (batch === "routing") await routingJourney();
	else if (batch === "catalog") await catalogJourney();
	else if (batch === "questions") await questionInteractionJourney();
	else if (batch === "approvals") await approvalInteractionJourney();
	else if (batch === "activities") await activityTaskJourney();
	else if (batch === "mouse") await mouseJourney();
	else throw new Error(`Unknown interaction batch: ${batch}`);

	const exitMark = output.length;
	const exitCommand = batch === "matrix" ? "/quit" : "/exit";
	await submitText(exitCommand);
	await waitFor(() => exited || output.slice(exitMark).includes("Session closed"), exitCommand, 15_000);
	console.log(`PASS: ${batch} interactive TUI journeys completed`);
} catch (error) {
	console.error(error instanceof Error ? error.stack : String(error));
	process.exitCode = 1;
} finally {
	if (terminal && !exited) {
		try {
			terminal.kill();
		} catch {
			/* already closed */
		}
		await delay(300);
		if (!exited) {
			try {
				await execute("taskkill", ["/PID", String(terminal.pid), "/T", "/F"], { windowsHide: true });
			} catch {
				/* exited concurrently */
			}
		}
	}
	await learningModel?.close();
	process.exit(process.exitCode ?? 0);
}

async function newSessionJourney() {
	let mark = await open("/new", "New session", "Title (optional)");
	await fillForm("interactive-alpha");
	await waitForText(mark, "Session “interactive-alpha” created.", "new session creation");
	const sessions = await cliJson(["session", "list", "--json"]);
	const created = Array.isArray(sessions) ? sessions.find((entry) => entry.title === "interactive-alpha") : undefined;
	if (!created?.sessionId) throw new Error("New TUI session was not durably renamed");
	currentSessionId = created.sessionId;
}

async function themeJourney() {
	for (const choice of ["Dark", "Light", "System"]) {
		const mark = await open("/theme", "Theme ·");
		await choose(choice);
		await waitForText(mark, `Theme set to ${choice.toLowerCase()}.`, `${choice} theme action`);
	}
}

async function memoryJourney() {
	let mark = await open("/memory", "Memory");
	await choose("Memory status");
	await waitForText(mark, "Back to Memory", "memory status result");
	await choose("Back to Memory");
	pressEscape();
	await waitComposer();

	mark = await open("/memory", "Memory");
	await choose("Search memory");
	await waitForText(mark, "Query", "memory query form");
	const emptyQueryMark = output.length;
	pressEnter();
	await delay(500);
	if (output.slice(emptyQueryMark).includes("Memory search"))
		throw new Error("Empty memory query unexpectedly submitted");
	await fillForm("interactive fact");
	await waitForText(mark, "No relevant memory found.", "empty memory query result");
	await choose("Back to Memory");
	pressEscape();
	await waitComposer();

	mark = await open("/memory", "Memory");
	await choose("Remember a fact");
	await fillForm("PTY interactions are durable");
	await waitForText(mark, "Remembered.", "remember fact");
	const recall = await inspectText(["memory", "recall", "--session", currentSessionId, "PTY interactions"]);
	if (!recall.includes("PTY interactions are durable")) throw new Error("Remembered fact was not durable");

	mark = await open("/memory", "Memory");
	await choose("Index workspace");
	await waitForText(mark, "Workspace indexed.", "workspace indexing");
}

async function goalJourney() {
	// Goal state mutations without an active goal are soft failures, never
	// successes: each action must say so instead of claiming it worked.
	let mark = await open("/goal", "Session goal");
	await choose("Pause goal");
	await waitForText(mark, "No active goal.", "pause without a goal");
	mark = await open("/goal", "Session goal");
	await choose("Resume goal");
	await waitForText(mark, "No goal to resume.", "resume without a goal");
	mark = await open("/goal", "Session goal");
	await choose("Complete goal");
	await waitForText(mark, "Complete the active goal?", "complete without a goal confirmation");
	pressEnter();
	await waitForText(mark, "No active goal.", "complete without a goal");

	mark = await open("/goal", "Session goal");
	await choose("Create or replace goal");
	await waitForText(mark, "Objective", "goal objective form");
	const emptyGoalMark = output.length;
	pressEnter();
	await delay(500);
	if (output.slice(emptyGoalMark).includes("Goal created.")) throw new Error("Empty goal form unexpectedly submitted");
	await fillForm("Exercise every interactive option");
	await waitForText(mark, "Goal created.", "goal creation");
	await assertGoal("active", "Exercise every interactive option");

	mark = await open("/goal", "Session goal");
	await choose("View goal");
	await waitForText(mark, "Goal (active): Exercise every interactive option", "goal status result");
	pressEscape();
	await waitComposer();

	mark = await open("/goal", "Session goal");
	await choose("Pause goal");
	await waitForText(mark, "Goal paused.", "pause goal");
	await assertGoal("paused");

	mark = await open("/goal", "Session goal");
	await choose("Resume goal");
	await waitForText(mark, "Goal resumed.", "resume goal");
	await assertGoal("active");

	mark = await open("/goal", "Session goal");
	await choose("Complete goal");
	await waitForText(mark, "Complete the active goal?", "goal completion confirmation");
	pressEscape();
	await waitComposer();
	await waitForText(mark, "Goal completion cancelled.", "goal completion cancellation");
	await assertGoal("active");

	mark = await open("/goal", "Session goal");
	await choose("Complete goal");
	await waitForText(mark, "Complete the active goal?", "goal completion confirmation retry");
	pressEnter();
	await waitComposer();
	await waitForText(mark, "Goal completed.", "goal completion success");
	const completed = await inspectJson(["goal", "status", "--session", currentSessionId, "--json"]);
	if (completed !== null) throw new Error(`Goal completion was not durable: ${JSON.stringify(completed)}`);
}

async function cronJourney() {
	let mark = await open("/cron", "Scheduled prompts");
	await choose("Create scheduled prompt");
	await fillForm("0 9 * * *");
	await waitForText(mark, "Prompt", "cron prompt form");
	const emptyPromptMark = output.length;
	pressEnter();
	await delay(500);
	if (output.slice(emptyPromptMark).includes("Scheduled prompt created."))
		throw new Error("Empty cron prompt unexpectedly submitted");
	await fillForm("review interactive coverage");
	await waitForText(mark, "Scheduled prompt created.", "cron creation");
	const jobs = await inspectJson(["cron", "list", "--session", currentSessionId, "--json"]);
	const job = Array.isArray(jobs) ? jobs.find((entry) => entry.prompt === "review interactive coverage") : undefined;
	if (!job?.id) throw new Error(`Created cron was not durable: ${JSON.stringify(jobs)}`);

	mark = await open("/cron", "Scheduled prompts");
	await choose("0 9 * * *");
	await waitForText(mark, "Delete this schedule", "cron action menu");
	await choose("Cancel");
	await waitForText(mark, "Scheduled prompts", "cron submenu cancel");
	pressEscape();
	await waitComposer();

	mark = await open("/cron", "Scheduled prompts");
	await choose("0 9 * * *");
	await waitForText(mark, "Delete this schedule", "cron action menu before cancel");
	await choose("Delete this schedule");
	await waitForText(mark, "Delete scheduled prompt", "cron delete confirmation");
	pressEscape();
	await waitComposer();
	await waitForText(mark, "Scheduled prompt deletion cancelled.", "cron delete cancellation");
	const retained = await inspectJson(["cron", "list", "--session", currentSessionId, "--json"]);
	if (!JSON.stringify(retained).includes(job.id)) throw new Error("Cancelled cron deletion removed the job");

	mark = await open("/cron", "Scheduled prompts");
	await choose("0 9 * * *");
	await waitForText(mark, "Delete this schedule", "cron action menu before deletion");
	await choose("Delete this schedule");
	pressEnter();
	await waitForText(mark, "Scheduled prompt deleted.", "cron deletion");
	const removed = await inspectJson(["cron", "list", "--session", currentSessionId, "--json"]);
	if (JSON.stringify(removed).includes(job.id)) throw new Error("Confirmed cron deletion was not durable");
}

async function capabilitiesJourney() {
	for (const [choice, expected] of [
		["All capabilities", "No active capabilities."],
		["Tools", "Tools"],
		["Skills", "Reload skills"],
		["Plugins", "Install plugin"],
		["MCP servers", "Reconnect capabilities"],
	]) {
		const mark = await open("/capabilities", "Capabilities");
		await choose(choice);
		await waitForText(mark, expected, `capabilities ${choice}`);
		if (choice === "All capabilities") {
			await choose("Back to Capabilities");
			await waitForText(mark, "MCP servers", "capabilities parent return");
		}
		pressEscape();
		await waitComposer();
	}
	let mark = await open("/skills", "Skills");
	await choose("Reload skills");
	await waitForText(mark, "Capabilities reloaded.", "skill reload");
	pressEscape();
	await waitComposer();
	mark = await open("/mcp", "Mcp", "Reconnect capabilities", 60_000);
	await choose("Reconnect capabilities");
	await waitForText(mark, "Capabilities reloaded.", "MCP reconnect");
	pressEscape();
	await waitComposer();
}

async function managementJourney() {
	for (const [alias, title] of [
		["/resume", "Sessions"],
		["/title", "Rename session"],
		["/activities", "Activity"],
		["/task", "Activity"],
		["/tasks", "Activity"],
		["/agents", "Agent graph and worker profiles"],
	]) {
		const mark = output.length;
		await submitText(alias);
		await waitForText(mark, title, `${alias} alias`);
		if (alias === "/resume") await waitForText(mark, "Enter resume", "session picker ready");
		await closePanelToComposer();
	}

	for (const [choice, title, ready] of [
		["Current work", "Current work", "Refresh"],
		["Activity history", "Activity history", "No recorded activity history."],
	]) {
		const mark = await open("/activity", "Activity");
		await choose(choice);
		await waitForText(mark, title, `activity ${choice}`);
		await waitForText(mark, ready, `activity ${choice} ready`);
		if (choice === "Current work") {
			const refreshMark = output.length;
			await choose("Refresh");
			await waitForText(refreshMark, "Search: type to filter", "activity Refresh ready state");
			await waitForText(refreshMark, "Refresh", "activity Refresh result");
		}
		await delay(200);
		pressEscape();
		await waitComposer();
	}

	let mark = await open("/learn", "Resident learner");
	await choose("Learner status");
	await waitForText(mark, "Pending proposals: 0", "learner status result");
	const learnerReturnMark = output.length;
	await choose("Back to Learn");
	await waitForText(learnerReturnMark, "Loading learner state", "learner parent reload");
	await waitForText(learnerReturnMark, "pending proposals", "learner parent return");
	await delay(300);
	pressEscape();
	await waitComposer();

	mark = await open("/trust", "Workspace trust");
	await choose("Trust this workspace");
	await waitForText(mark, "Workspace trusted.", "trust grant");
	pressEscape();
	await waitComposer();
	mark = await open("/trust", "Workspace trust");
	await choose("Trusted");
	await waitForText(mark, "Workspace trust status", "trust status action");
	await waitForText(mark, "State: trusted", "trust status detail");
	// A fresh mark plus the loading label prove the parent actually reopened;
	// the old mark could match the previous menu's stale frames.
	const trustReturnMark = output.length;
	await choose("Back to Trust");
	await waitForText(trustReturnMark, "Inspecting workspace trust", "trust parent reload");
	await waitForText(trustReturnMark, "Revoke trust", "trust status parent return");
	pressEscape();
	await waitComposer();
	mark = await open("/trust", "Workspace trust");
	await choose("Revoke trust");
	await waitForText(mark, "Revoke trust for this workspace?", "trust revoke confirmation");
	pressEscape();
	await waitForText(mark, "Workspace trust revocation cancelled.", "trust revoke cancellation");
	mark = await open("/trust", "Workspace trust");
	await choose("Revoke trust");
	pressEnter();
	await waitForText(mark, "Workspace trust revoked.", "trust revoke success");
	await choose("Trust this workspace");
	await waitForText(mark, "Workspace trusted.", "trust restore");
	pressEscape();
	await waitComposer();

	mark = await open("/auth", "Provider credentials");
	await choose("OpenAI API");
	await waitForText(mark, "Credentials · OpenAI API", "OpenAI credential actions");
	await choose("Add API key");
	await waitForText(mark, "API key · OpenAI API", "API key form");
	const emptyKeyMark = output.length;
	pressEnter();
	await delay(500);
	if (output.slice(emptyKeyMark).includes("API credential saved"))
		throw new Error("Empty API key unexpectedly submitted");
	await fillForm("acceptance-secret");
	await waitForText(mark, "API credential saved for OpenAI API.", "API key save");
	await waitForText(mark, "OpenAI API  API ready", "credential parent after API key save");
	const configured = await cliText(["auth", "status", "openai-api"]);
	if (!configured.includes("Credential configured")) throw new Error("API credential was not persisted");
	pressEscape();
	await waitComposer();

	mark = await open("/auth", "Provider credentials");
	await choose("OpenAI API");
	await choose("Remove credential");
	await choose("Remove API key");
	await waitForText(mark, "Remove the API credential for OpenAI API?", "API key removal confirmation");
	pressEscape();
	await waitForText(mark, "API credential removal cancelled for OpenAI API.", "API key removal cancellation");
	mark = await open("/auth", "Provider credentials");
	await choose("OpenAI API");
	await choose("Remove credential");
	await choose("Remove API key");
	pressEnter();
	await waitForText(mark, "API credential removed for OpenAI API.", "API key removal success");
	await waitForText(mark, "OpenAI API  API —", "credential parent after API key removal");
	const removed = await cliText(["auth", "status", "openai-api"]);
	if (!removed.includes("No credential configured")) throw new Error("API credential removal was not persisted");
	pressEscape();
	await waitComposer();

	for (const [choice, title] of [
		["Model routes", "Choose which agent receives the model route"],
		["Agent profiles", "Agent graph and worker profiles"],
		["Provider credentials", "Provider credentials"],
		["Workspace trust", "Workspace trust"],
	]) {
		mark = await open("/config", "Settings");
		await choose(choice);
		await waitForText(mark, title, `settings ${choice}`);
		await closePanelToComposer();
	}

	await settingsJourney();
}

async function settingsJourney() {
	// Sections list with current values; Escape returns from a section to the root.
	let mark = await open("/config", "Settings");
	await waitForText(mark, "Turns & compaction", "settings section list");
	await choose("Telemetry");
	await waitForText(mark, "Settings · Telemetry", "telemetry section");
	await waitForText(mark, "Enabled: off", "telemetry default value");
	let stepMark = output.length;
	pressEscape();
	await waitForText(stepMark, "Turns & compaction", "settings root after section escape");
	pressEscape();
	await waitComposer();

	// Boolean toggle persists through the shared config write path.
	mark = await open("/config", "Settings");
	await choose("Telemetry");
	await waitForText(mark, "Settings · Telemetry", "telemetry section for toggle");
	await choose("Enabled");
	await waitForText(mark, "Set telemetry.enabled to true.", "telemetry toggle write");
	await waitForText(mark, "Enabled: on", "telemetry section refresh after toggle");
	let persisted = await cliJson(["config", "get", "--json"]);
	if (persisted?.telemetry?.enabled !== true) throw new Error("Telemetry toggle was not persisted");
	await closeSettingsToComposer();

	// Enum picker: choose a permission profile, then restore manual.
	mark = await open("/config", "Settings");
	await choose("Permission");
	await waitForText(mark, "Settings · Permission", "permission section");
	await waitForText(mark, "Default profile: manual", "permission default profile value");
	await choose("Default profile");
	await waitForText(mark, "Settings · Default profile", "permission profile picker");
	await choose("workspace");
	await waitForText(mark, "Set permission.defaultProfile to workspace.", "permission profile write");
	await waitForText(mark, "Default profile: workspace", "permission section refresh after profile change");
	persisted = await cliJson(["config", "get", "--json"]);
	if (persisted?.permission?.defaultProfile !== "workspace")
		throw new Error("Permission profile selection was not persisted");
	stepMark = output.length;
	await choose("Default profile");
	await waitForText(stepMark, "Settings · Default profile", "permission profile picker restore");
	await choose("manual");
	await waitForText(stepMark, "Set permission.defaultProfile to manual.", "permission profile restore");
	await closeSettingsToComposer();

	// String list: add then remove an allow-list entry.
	mark = await open("/config", "Settings");
	await choose("Permission");
	await waitForText(mark, "Settings · Permission", "permission section for list edit");
	await choose("Allow list");
	await waitForText(mark, "Settings · Allow list", "allow list editor");
	await waitForText(mark, "No entries", "allow list empty state");
	await choose("Add entry");
	await waitForText(mark, "New entry", "allow list entry form");
	await fillForm("bash(git status)");
	await waitForText(mark, "Added bash(git status) to permission.allowList.", "allow list add");
	persisted = await cliJson(["config", "get", "--json"]);
	if (!persisted?.permission?.allowList?.includes("bash(git status)"))
		throw new Error("Allow-list entry was not persisted");
	await choose("bash(git status)");
	await waitForText(mark, "Remove “bash(git status)” from Allow list?", "allow list removal confirmation");
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Removed bash(git status) from permission.allowList.", "allow list removal");
	await waitForText(stepMark, "No entries", "allow list empty after removal");
	stepMark = output.length;
	pressEscape();
	await waitForText(stepMark, "Settings · Permission", "permission section after list escape");
	await closeSettingsToComposer();

	// Numeric editors: out-of-range input surfaces an inline error and does not
	// write; a valid value persists.
	mark = await open("/config", "Settings");
	await choose("Agents");
	await waitForText(mark, "Settings · Agents", "agents section");
	await choose("Coordinator max steps");
	await waitForText(mark, "Value (1–50)", "coordinator max steps form");
	await fillForm("99");
	await waitForText(mark, "Coordinator max steps must be between 1 and 50.", "out-of-range rejection");
	persisted = await cliJson(["config", "get", "--json"]);
	if (persisted?.agentGraph?.coordinator?.maxSteps !== undefined)
		throw new Error("Out-of-range coordinator maxSteps was persisted");
	stepMark = output.length;
	pressEscape();
	await waitForText(stepMark, "Settings · Agents", "agents section after form escape");
	await choose("Coordinator max steps");
	await waitForText(stepMark, "Value (1–50)", "coordinator max steps form retry");
	await fillForm("12");
	await waitForText(stepMark, "Set agentGraph.coordinator.maxSteps to 12.", "coordinator max steps write");
	await waitForText(stepMark, "Coordinator max steps: 12", "agents section refresh after numeric write");
	persisted = await cliJson(["config", "get", "--json"]);
	if (persisted?.agentGraph?.coordinator?.maxSteps !== 12)
		throw new Error("Coordinator maxSteps was not persisted");
	await closeSettingsToComposer();
}

// Escape from a settings section returns to the Settings root; a second Escape
// reaches the composer. Fresh marks guard against the asynchronous panel
// reopen racing the next key.
async function closeSettingsToComposer() {
	const rootMark = output.length;
	pressEscape();
	await waitForText(rootMark, "Search: type to filter", "settings root return");
	pressEscape();
	await waitComposer();
}

async function lifecycleJourney() {
	let mark = await open("/help", "Help");
	await choose("Keyboard shortcuts");
	await waitForText(mark, "Ctrl+G: editor", "interactive keyboard help");
	await choose("Back to Help");
	await waitForText(mark, "/new (interactive)", "help command list return");
	await choose("/new (interactive)");
	await waitForText(mark, "Help · /new", "interactive command help");
	await waitForText(mark, "Create a new session for this workspace", "command help description");
	await choose("Back to Help");
	pressEscape();
	await waitComposer();

	mark = output.length;
	await submitText("/interactions");
	await waitForText(mark, "No approval or question is waiting.", "empty interaction queue");

	mark = output.length;
	await submitText("/fork");
	await waitForText(mark, "Fork the current session and continue in the new copy?", "session fork confirmation");
	pressEnter();
	await waitForText(mark, "Switched to session", "session fork switch");
	mark = await open("/rename", "Rename session", "New title");
	const emptyRenameMark = output.length;
	pressEnter();
	await delay(400);
	if (output.slice(emptyRenameMark).includes("Session renamed")) throw new Error("Empty rename unexpectedly submitted");
	await fillForm("forked-session");
	await waitForText(mark, "Session renamed to “forked-session”", "fork rename");
	let sessions = await cliJson(["session", "list", "--json"]);
	const forked = sessions.find((entry) => entry.title === "forked-session");
	if (!forked?.sessionId) throw new Error("Forked session was not durably renamed");
	currentSessionId = forked.sessionId;

	mark = await open("/sessions", "Sessions", "Enter resume");
	const sessionSwitchMark = output.length;
	await choose("interactive-alpha");
	await waitForText(sessionSwitchMark, "Resuming selected session", "session picker submission");
	await waitForText(sessionSwitchMark, "Switched to session", "session picker selection");
	await delay(1_000);
	sessions = await cliJson(["session", "list", "--json"]);
	const original = sessions.find((entry) => entry.title === "interactive-alpha");
	if (!original?.sessionId) throw new Error("Original session disappeared from picker journey");
	currentSessionId = original.sessionId;
	await stopTui();
	await cliText(["goal", "create", "--session", currentSessionId, "--objective", "timeline checkpoint"]);
	await startTui();

	mark = await open("/undo", "Session timeline");
	await waitForText(mark, "Kageko state", "restorable timeline entry");
	pressEnter();
	await waitForText(mark, "Restore Kageko to this exact timeline state?", "timeline restore confirmation");
	pressEscape();
	await waitComposer();
	mark = await open("/undo", "Session timeline");
	pressEnter();
	await waitForText(mark, "Restore Kageko to this exact timeline state?", "timeline restore confirmation retry");
	pressEnter();
	await waitForText(mark, "Restored to timeline state", "timeline restore success");
	// The restored session rewrote the timeline, so the panel closes itself; a
	// stale entry must never be reappliable from the old menu.
	await waitForText(mark, "Ask Kageko", "undo panel closes after restore");
	pressEscape();
	await waitComposer();

	// Bracketed paste keeps even one embedded newline intact. The composer uses
	// a compact marker; expansion at submission restores the original text.
	const pasteMark = output.length;
	terminal.write("\x1b[200~single-newline\npaste-check\x1b[201~");
	await waitForText(pasteMark, "[paste #1 +1 lines]", "single-newline paste preservation");
	terminal.write("\x03");
	await delay(300);

	mark = await open("/compact", "Compact context");
	await choose("Cancel");
	await waitComposer();
	mark = await open("/compact", "Compact context");
	await choose("Compact now");
	await waitFor(
		() => output.slice(mark).includes("Context compacted.") || output.slice(mark).includes("Compaction skipped"),
		"compact action result",
		20_000,
	);

	mark = await open("/shell", "Embedded shell", "Type commands; Enter runs");
	await submitText("echo KAGEKO_PTY_SHELL_OK");
	await waitForText(mark, "KAGEKO_PTY_SHELL_OK", "embedded shell command output");
	terminal.write("\x1bOQ");
	await delay(500);

	mark = await open("/archive", "Session archive");
	await closePanelToComposer();
	const preArchive = await cliJson(["session", "list", "--json"]);
	if (!preArchive.some((entry) => entry.sessionId === currentSessionId))
		throw new Error("Archive cancellation changed session state");
	mark = await open("/archive", "Session archive");
	await choose("Archive and start a new session");
	await waitForText(mark, "archived; started a new session.", "session archive action");
	const allAfterArchive = await cliJson(["session", "list", "--all", "--json"]);
	if (!allAfterArchive.some((entry) => entry.sessionId === currentSessionId && entry.archived === true))
		throw new Error("Archived session was not persisted as archived");
	const activeAfterArchive = await cliJson(["session", "list", "--json"]);
	const replacement = activeAfterArchive.find((entry) => entry.sessionId !== forked.sessionId);
	if (!replacement?.sessionId) throw new Error("Archiving did not create a replacement session");
	currentSessionId = replacement.sessionId;

	const deletionTarget = await cliJson(["session", "create", "--title", "deletion-target", "--json"]);
	mark = await open("/delete", "Delete session");
	await choose("deletion-target");
	await waitForText(mark, "Delete session", "delete confirmation");
	pressEscape();
	await waitComposer();
	if (!(await cliJson(["session", "list", "--json"])).some((entry) => entry.sessionId === deletionTarget.sessionId))
		throw new Error("Cancelled session deletion removed its target");
	mark = await open("/delete", "Delete session");
	await choose("deletion-target");
	pressEnter();
	await waitForText(mark, "deleted.", "session deletion success");
	if (
		(await cliJson(["session", "list", "--all", "--json"])).some(
			(entry) => entry.sessionId === deletionTarget.sessionId,
		)
	)
		throw new Error("Confirmed session deletion was not durable");

	// Submitted prompts and slash commands persist to the per-workspace input
	// history file (append-only JSONL), surviving the TUI restarts above.
	const historyDir = path.join(fixtureHome, "user-history");
	let historyText = "";
	const historyDeadline = Date.now() + 10_000;
	while (Date.now() < historyDeadline) {
		const files = await readdir(historyDir).catch(() => []);
		if (files.length) historyText = await readFile(path.join(historyDir, files[0]), "utf8");
		if (historyText.includes("/fork")) break;
		await delay(100);
	}
	if (!historyText.includes("/fork"))
		throw new Error(`Submitted input was not persisted to history: ${JSON.stringify(historyText)}`);
}

async function learningJourney() {
	// Exercise the production resident-learner graph first: the capability gap is
	// emitted by a normal user turn, processed at that turn's boundary, and must
	// become inspectable in the same live TUI process. A close/reopen here would
	// only prove session-shutdown flushing and would hide graph scheduling bugs.
	let mark = output.length;
	await submitText("Please identify a disposable capability candidate for rejection testing.");
	// A cold Windows runtime may spend tens of seconds loading the bundled
	// provider catalog, native PTY and session graph before turn.started. Bound
	// the whole production startup, but do not give the model only the few
	// seconds left over from a 60s wall-clock wait.
	await waitForText(mark, "need_capability", "live capability-gap tool call", 180_000);
	await waitForText(mark, "need_capability recorded for learner review.", "live capability-gap turn", 180_000);
	// turn.end deliberately schedules resident learning in the background. The
	// learner list auto-refreshes in place every few seconds (preserving the
	// user's selection and filter; submenus and dialogs are left untouched), so a
	// completed synthesis appears without reopening. The close-and-reopen loop
	// below remains the real user recovery path and also exercises that refresh.
	const learnerDeadline = Date.now() + 180_000;
	const noticeMark = mark;
	for (;;) {
		mark = await openWhenIdle(
			"/learn",
			"Resident learner",
			"Search: type to filter",
			Math.max(1, learnerDeadline - Date.now()),
		);
		try {
			await waitForText(
				mark,
				"discard-candidate  tool",
				"same-session resident learner output",
				Math.min(5_000, Math.max(1, learnerDeadline - Date.now())),
			);
			break;
		} catch (error) {
			if (Date.now() >= learnerDeadline) throw error;
			await closePanelToComposer();
		}
	}
	await closePanelToComposer();
	// A stashed proposal must notify the user without opening /learn: a learning
	// diagnostic lands in the transcript and the footer badges the pending count.
	await waitForText(noticeMark, "New learning proposal pending: discard-candidate", "learning proposal notice");
	await waitForText(noticeMark, "learn: 1", "learning pending badge");

	await stopTui();
	for (const prompt of [
		"Please identify a reusable capability for concise release notes.",
		"Please identify a reusable capability for the remote test feed.",
	]) {
		const result = await cliText([
			"--session",
			currentSessionId,
			"--prompt",
			prompt,
			"--permission",
			"unrestricted",
			"--interaction",
			"unattended",
		]);
		if (!result.includes("need_capability")) throw new Error(`Learning prompt did not request a capability: ${result}`);
	}
	await startTui();
	await waitForOutputIdle(1_000, 25_000);
	let pending = await cliJson(["learning", "pending", "--session", currentSessionId, "--json"]);
	const discard = pending.find((entry) => entry.output?.name === "discard-candidate");
	const tool = pending.find((entry) => entry.output?.kind === "tool" && entry.output?.name === "release-note");
	const mcp = pending.find((entry) => entry.output?.kind === "mcp");
	if (!discard || !tool || !mcp)
		throw new Error(`Required learning proposals are missing or malformed: ${JSON.stringify(pending)}`);

	mark = await open("/learn", "Resident learner");
	await waitForText(mark, "discard-candidate  tool", "loaded disposable learning proposal");
	await choose("discard-candidate");
	await waitForText(mark, "Learning proposal ·", "learning proposal action menu");
	// The proposal must be inspectable before approval.
	await choose("View details");
	await waitForText(mark, "Full proposal:", "learning proposal details");
	await waitForText(mark, "Source: capability_gap", "learning proposal detail source");
	await choose("Back to Learn");
	await waitForText(mark, "Learner status", "learning proposal details return");
	await choose("discard-candidate");
	await waitForText(mark, "Learning proposal ·", "learning proposal action menu return");
	await choose("Cancel");
	await waitForText(mark, "Learner status", "learning proposal submenu cancel");
	await closePanelToComposer();

	mark = await open("/learn", "Resident learner");
	await waitForText(mark, "discard-candidate  tool", "reloaded disposable learning proposal");
	await choose("discard-candidate");
	await choose("Reject");
	await waitForText(mark, "Reject this learning proposal?", "learning rejection confirmation");
	pressEscape();
	await waitForText(mark, "Learning proposal rejection cancelled.", "learning rejection cancellation");
	pending = await inspectJson(["learning", "pending", "--session", currentSessionId, "--json"]);
	if (!pending.some((entry) => entry.event.id === discard.event.id))
		throw new Error("Cancelled rejection removed the proposal");

	// A stale proposal action must surface the resolver failure, not claim
	// success: drop the entry from the pending queue behind the panel's back
	// (another process resolving it has the same observable effect; a real
	// cross-process resolve cannot run here because the TUI owns the session
	// runtime lease), then attempt the approval in the TUI.
	mark = await open("/learn", "Resident learner");
	await waitForText(mark, "discard-candidate  tool", "stale-test disposable proposal");
	await choose("discard-candidate");
	await waitForText(mark, "Learning proposal ·", "stale proposal action menu");
	const pendingPath = path.join(fixtureHome, ".kageko", "learning", "pending.jsonl");
	const pendingSnapshot = await readFile(pendingPath, "utf8");
	const keptLines = pendingSnapshot
		.split("\n")
		.filter((line) => line.trim() && !line.includes(discard.event.id))
		.join("\n");
	await writeFile(pendingPath, pendingSnapshot.endsWith("\n") ? `${keptLines}\n` : keptLines);
	await choose("Approve");
	await waitForText(mark, "Could not approve: pending entry not found", "stale approval failure", 30_000);
	if (visibleText(output.slice(mark)).includes("Learning proposal approved."))
		throw new Error("Stale approval unexpectedly reported success");
	// Restore the queue so the rejection flow below still owns its proposal.
	await writeFile(pendingPath, pendingSnapshot);
	await closePanelToComposer();

	mark = await open("/learn", "Resident learner");
	await waitForText(mark, "discard-candidate  tool", "disposable proposal before rejection");
	await choose("discard-candidate");
	await choose("Reject");
	pressEnter();
	await waitForText(mark, "Learning proposal rejected.", "learning rejection success");
	await closePanelToComposer();

	mark = await open("/learn", "Resident learner");
	await waitForText(mark, "release-note  tool", "tool proposal before approval");
	await choose("release-note");
	await choose("Approve");
	await waitForText(mark, "Learning proposal approved.", "tool proposal approval", 30_000);
	await closePanelToComposer();
	mark = await open("/tools", "Tools");
	await paste("auto__release_note");
	await waitFor(
		() => /auto__release_note\s+project_auto/.test(visibleText(output.slice(mark))),
		"approved tool hot-loaded without restart",
		30_000,
	);
	await closePanelToComposer();
	mark = output.length;
	await submitText("Invoke the learned release-note tool for the benchmark subject.");
	await waitForText(mark, "Run this command?", "learned tool approval", 120_000);
	terminal.write("1");
	await waitForText(mark, "release-note:benchmark", "learned tool execution result", 120_000);
	await waitForText(mark, "Learned tool result verified.", "learned tool result consumed by agent", 90_000);

	mark = await openWhenIdle("/learn", "Resident learner", "Search: type to filter", 120_000);
	await waitForText(mark, "release-feed  mcp", "MCP proposal before approval");
	await choose("release-feed");
	await choose("Approve");
	await waitForText(mark, "Learning proposal approved.", "MCP proposal approval", 30_000);
	await closePanelToComposer();
	mark = await open("/mcp", "Mcp", "Reconnect capabilities", 60_000);
	await choose("release-feed");
	await waitForText(mark, "MCP server · release-feed", "approved MCP hot-loaded without restart", 30_000);
	await choose("Back to Mcp");
	await closePanelToComposer();
	mark = output.length;
	await submitText("Invoke the learned release-feed MCP tool now.");
	await waitFor(
		() => {
			const visible = visibleText(output.slice(mark));
			return visible.includes("Run this command?") || visible.includes("Learned MCP result verified: ok");
		},
		"learned MCP invocation or approval",
		120_000,
	);
	if (visibleText(output.slice(mark)).includes("Run this command?")) terminal.write("1");
	await waitForText(mark, "Learned MCP result verified: ok", "learned MCP result consumed by agent", 120_000);
	mark = await openWhenIdle("/learn", "Resident learner", "Search: type to filter", 120_000);
	await closePanelToComposer();
	mark = output.length;
	await submitText("Generate a reusable release-validation skill from this completed task.");
	await waitFor(
		() => {
			const visible = visibleText(output.slice(mark));
			return visible.includes("Run this command?") || visible.includes('Generated skill "release-validation"');
		},
		"live generated-skill invocation or approval",
		120_000,
	);
	if (visibleText(output.slice(mark)).includes("Run this command?")) terminal.write("1");
	await waitForText(mark, 'Generated skill "release-validation"', "live generated skill tool result", 120_000);
	await waitForText(mark, "Learned skill generation verified.", "generated skill result consumed by agent", 90_000);
	mark = await openWhenIdle("/learn", "Resident learner", "Search: type to filter", 120_000);
	await closePanelToComposer();

	await stopTui();
	await cliText(["trust", "grant"]);

	const toolManifestPath = path.join(fixtureHome, ".kageko", "tools", "auto", "release-note", "manifest.json");
	const mcpManifestPath = path.join(fixtureHome, ".kageko", "mcp", "auto", "release-feed", "manifest.json");
	const skillPath = path.join(fixtureHome, ".kageko", "skills", "auto", "release-validation", "SKILL.md");
	const toolManifest = JSON.parse(await readFile(toolManifestPath, "utf8"));
	const mcpManifest = JSON.parse(await readFile(mcpManifestPath, "utf8"));
	const skill = await readFile(skillPath, "utf8");
	if (
		toolManifest.command !== "node" ||
		toolManifest.parameters?.required?.join(",") !== "subject" ||
		toolManifest.args?.length !== 2 ||
		!toolManifest.args[0]?.endsWith("tool.cjs") ||
		toolManifest.args[1] !== "{{__args_json}}"
	)
		throw new Error(`Generated tool manifest failed quality checks: ${JSON.stringify(toolManifest)}`);
	if (mcpManifest.command !== "node" || mcpManifest.args?.length !== 1 || !mcpManifest.args[0]?.endsWith("server.cjs"))
		throw new Error(`Generated MCP manifest failed quality checks: ${JSON.stringify(mcpManifest)}`);
	if (
		!skill.startsWith("---\nname: release-validation\ndescription:") ||
		!skill.includes("Run the product acceptance suite.")
	)
		throw new Error(`Generated skill failed quality checks: ${skill}`);

	const tools = await cliJson(["capability", "list", "--session", currentSessionId, "--kind", "tool", "--json"]);
	if (!tools.some((entry) => entry.name === "auto__release_note")) throw new Error("Approved tool was not loadable");
	const mcps = await cliJson(["mcp", "list", "--session", currentSessionId, "--json"]);
	if (!mcps.some((entry) => entry.id === "release-feed")) throw new Error("Approved MCP was not loadable");
	const skills = await cliJson(["skill", "list", "--session", currentSessionId, "--json"]);
	if (!skills.some((entry) => entry.id === "release-validation")) throw new Error("Generated skill was not loadable");
	await startTui();

	// Restart restores the session immediately, while summary/learning flushes from
	// the preceding CLI inspections can still own RuntimeSession briefly. Wait on
	// the menu's actual loaded state instead of racing its "Loading capabilities"
	// placeholder with the old generic 15s panel timeout.
	mark = await openWhenIdle("/tools", "Tools", "read  builtin", 120_000);
	await paste("auto__release_note");
	await waitForText(mark, "auto__release_note  project_auto", "generated tool in TUI");
	await closePanelToComposer();
	mark = await openWhenIdle("/mcp", "Mcp", "Reconnect capabilities", 120_000);
	await choose("release-feed");
	await waitForText(mark, "MCP server · release-feed", "generated MCP detail action");
	await choose("View server details");
	await waitForText(mark, "Authentication: not required", "generated MCP authentication classification");
	await choose("Back to Mcp");
	await waitForText(mark, "Reconnect capabilities", "generated MCP detail parent return");
	await closePanelToComposer();

	mark = await openWhenIdle("/skills", "Skills", "Reload skills", 120_000);
	await choose("release-validation");
	await waitForText(mark, "Remove skill release-validation?", "skill removal confirmation");
	terminal.write("\x03");
	await waitForText(mark, "Skill release-validation removal cancelled.", "skill removal cancellation");
	if (
		!(await inspectJson(["skill", "list", "--session", currentSessionId, "--json"])).some(
			(entry) => entry.id === "release-validation",
		)
	)
		throw new Error("Cancelled skill removal removed the skill");
	mark = await openWhenIdle("/skills", "Skills", "Reload skills", 120_000);
	await choose("release-validation");
	pressEnter();
	await waitForText(mark, "Skill release-validation removed.", "skill removal success");
	await stopTui();
	await cliText(["trust", "grant"]);
	const remainingSkills = await cliJson(["skill", "list", "--session", currentSessionId, "--json"]);
	if (remainingSkills.some((entry) => entry.id === "release-validation"))
		throw new Error("Confirmed skill removal was not durable");
	await startTui();
}

async function advancedJourney() {
	await planJourney();
	await pluginJourney();
	await modelJourney();
	await setupJourney();
}

async function matrixJourney() {
	await setupRouteMatrixJourney();
}

async function routingJourney() {
	await modelTargetMatrixJourney();
	await graphResetMatrixJourney();
}

async function catalogJourney() {
	await helpEntryMatrixJourney();
	await authEntryMatrixJourney();
}

async function questionInteractionJourney() {
	let mark = output.length;
	await submitText("PTY question alpha");
	await waitForText(mark, "Which runtime option?", "question option prompt", 120_000);
	await waitForText(mark, "1. Alpha", "question option ownership", 120_000);
	let closeMark = output.length;
	pressEscape();
	await waitForText(closeMark, "Ask Kageko", "question Escape returns to composer");
	mark = output.length;
	await submitText("/interactions");
	await waitForText(mark, "Which runtime option?", "question reopened after Escape");
	await delay(200);
	pressEnter();
	await waitForText(mark, "Runtime observed Alpha", "first question option reaches model", 120_000);
	await waitForOutputIdle(400, 10_000);

	mark = output.length;
	await submitText("PTY question beta");
	await waitForText(mark, "Which runtime option?", "second question prompt", 120_000);
	await waitForText(mark, "1. Alpha", "second question option ownership", 120_000);
	closeMark = output.length;
	terminal.write("\x04");
	await waitForText(closeMark, "Ask Kageko", "question Ctrl+D returns to composer");
	mark = output.length;
	await submitText("/interactions");
	await waitForText(mark, "Which runtime option?", "question reopened after Ctrl+D");
	await delay(200);
	pressDown();
	pressEnter();
	await waitForText(mark, "Runtime observed Beta", "second question option reaches model", 120_000);
	await waitForOutputIdle(400, 10_000);

	mark = output.length;
	await submitText("PTY question other");
	await waitForText(mark, "Which runtime option?", "custom question prompt", 120_000);
	await waitForText(mark, "1. Alpha", "custom question option ownership", 120_000);
	pressDown(2);
	await paste("Gamma detail");
	pressEnter();
	await waitForText(mark, "Runtime observed Gamma detail", "custom question answer reaches model", 120_000);
	await waitForOutputIdle(400, 10_000);
}

async function approvalInteractionJourney() {
	let mark = await requestApproval("once");
	terminal.write("1");
	await waitForText(mark, "Runtime approval once observed", "approval once result", 120_000);
	await waitForOutputIdle(400, 10_000);
	mark = await requestApproval("once-repeat", "once");
	terminal.write("1");
	await waitForText(mark, "Runtime approval once-repeat observed", "one-time approval asks again", 120_000);
	await waitForOutputIdle(400, 10_000);

	mark = await requestApproval("session");
	terminal.write("\t");
	await paste("session-note");
	await waitForText(mark, "Feedback (typing): session-note", "approval feedback editor");
	pressEnter();
	terminal.write("\x07");
	await waitForText(mark, "Preview", "approval preview toggle");
	terminal.write("\x0f");
	await waitForText(mark, "Tool output", "approval expanded output toggle");
	terminal.write("2");
	await waitForText(mark, "Runtime approval session observed", "approval session result", 120_000);
	await waitForText(mark, "feedback=session-note", "approval feedback reaches the model", 120_000);
	await waitForOutputIdle(400, 10_000);
	mark = output.length;
	await submitText("PTY approval session-repeat");
	await waitForText(
		mark,
		"Runtime approval session-repeat observed",
		"session approval reused without prompting",
		240_000,
	);
	if (visibleText(output.slice(mark)).includes("Run this command?")) {
		throw new Error("Session approval unexpectedly prompted again for the exact command");
	}
	await waitForOutputIdle(400, 10_000);

	mark = await requestApproval("deny");
	terminal.write("\t");
	await paste("deny-note");
	await waitForText(mark, "Feedback (typing): deny-note", "denial feedback editor");
	pressEnter();
	terminal.write("3");
	await waitForText(mark, "Runtime approval deny observed", "approval deny option result", 120_000);
	await waitForText(mark, "deny-note", "denial feedback reaches the model", 120_000);
	await waitForOutputIdle(400, 10_000);

	mark = await requestApproval("escape-deny");
	pressEscape();
	await waitForText(mark, "Runtime approval escape-deny observed", "approval Escape denial result", 120_000);
	await waitForOutputIdle(400, 10_000);
}

async function requestApproval(label, commandLabel = label) {
	const mark = output.length;
	await submitText(`PTY approval ${label}`);
	await waitForText(mark, "Run this command?", `approval ${label} prompt`, 120_000);
	await waitForText(mark, "1-3 choose", `approval ${label} supported choices`);
	if (visibleText(output.slice(mark)).includes("always")) {
		throw new Error(`Approval ${label} exposed an unsupported persistent choice`);
	}
	await waitForText(mark, `approval-${commandLabel}`, `approval ${label} preview`);
	return mark;
}

async function activityTaskJourney() {
	let mark = output.length;
	await submitText("PTY background activity");
	await waitForText(mark, "Run this command?", "background task approval", 120_000);
	terminal.write("1");
	await waitForText(mark, "Background activity started.", "background task model completion", 120_000);
	await delay(500);

	mark = await open("/activity", "Activity");
	await choose("Current work");
	await waitForText(mark, "Current work", "active task browser");
	await waitForText(mark, "running  process", "running process row", 30_000);
	await choose("running  process");
	await waitForText(mark, "Task ·", "active task actions");
	await waitForText(mark, "Open output", "active task action ownership");
	await choose("Open output");
	await waitForText(mark, "Result", "task output result panel", 30_000);
	await waitForText(mark, "PTY_ACTIVITY_OUTPUT", "captured task output", 30_000);
	await waitForText(mark, "Close", "task output close action");
	await delay(200);
	let closeMark = output.length;
	await choose("Close");
	await waitForText(closeMark, "Ask Kageko", "output result closes to composer");

	mark = await open("/activity", "Activity");
	await choose("Current work");
	await waitForText(mark, "running  process", "running process row before stop cancellation", 30_000);
	await choose("running  process");
	await waitForText(mark, "Task ·", "task actions before stop cancellation");
	await choose("Stop task");
	await waitForText(mark, "Choose whether to continue:", "stop-task confirmation");
	closeMark = output.length;
	pressEscape();
	await waitForText(closeMark, "Ask Kageko", "cancelled stop returns to composer");

	mark = await open("/activity", "Activity");
	await choose("Current work");
	await waitForText(mark, "running  process", "task retained after stop cancellation");
	await choose("running  process");
	await waitForText(mark, "Task ·", "task actions before stop success");
	await choose("Stop task");
	await waitForText(mark, "Choose whether to continue:", "stop-task success confirmation");
	pressEnter();
	await waitForText(mark, "Stop requested for", "stop-task success", 30_000);
	await waitForText(mark, "Current work", "current-work return after stop");
	closeMark = output.length;
	pressEscape();
	await waitForText(closeMark, "Ask Kageko", "stopped-task browser closes to composer");

	mark = await open("/activity", "Activity");
	await choose("Activity history");
	await waitForText(mark, "Activity history", "task history browser");
	await waitForText(mark, "cancelled  process", "stopped task history row", 30_000);
	await choose("cancelled  process");
	await waitForText(mark, "Task ·", "historical task actions");
	await waitForText(mark, "Back", "historical task Back ownership");
	await choose("Back");
	await waitForText(mark, "Activity history", "historical task Back action");
	pressEscape();
	await waitComposer();
}

async function mouseJourney() {
	let mark = await open("/theme", "Theme ·");
	terminal.write("\x1b[<0;4;45M\x1b[<0;4;45m\x1b[<65;4;45M");
	await delay(300);
	if (visibleText(output.slice(mark)).includes("Theme set to"))
		throw new Error("Mouse input unexpectedly selected a theme");
	pressEnter();
	await waitForText(mark, "Theme set to system.", "keyboard selects System after ignored mouse input");

	mark = await open("/theme", "Theme ·");
	pressDown();
	pressEnter();
	await waitForText(mark, "Theme set to dark.", "keyboard selects Dark theme");
}

async function helpEntryMatrixJourney() {
	const commands = [
		"new",
		"sessions",
		"fork",
		"rename",
		"archive",
		"delete",
		"exit",
		"help",
		"cancel",
		"activity",
		"theme",
		"undo",
		"capabilities",
		"cron",
		"shell",
		"goal",
		"plan",
		"compact",
		"memory",
		"learn",
		"skills",
		"mcp",
		"plugins",
		"tools",
		"model",
		"graph",
		"config",
		"auth",
		"setup",
		"trust",
	];
	for (const command of commands) {
		let mark = await open("/help", "Help", "Keyboard shortcuts");
		await choose(`/${command}`);
		await waitForText(mark, `Help · /${command}`, `help entry /${command}`);
		mark = output.length;
		pressEscape();
		await waitForText(mark, "Keyboard shortcuts", `help return from /${command}`);
		pressEscape();
		await waitComposer();
	}
}

async function authEntryMatrixJourney() {
	const providers = [
		"OpenAI Codex (OAuth)",
		"OpenAI API",
		"OpenRouter",
		"Kimi / Moonshot",
		"Kimi / Moonshot (China)",
		"Kimi Code (OAuth)",
		"DeepSeek",
		"Xiaomi MiMo",
		"Custom (OpenAI-compatible)",
	];
	for (const provider of providers) {
		let mark = await open("/auth", "Provider credentials", "OpenAI Codex (OAuth)");
		await choose(provider);
		await waitForText(mark, `Credentials · ${provider}`, `credential entry ${provider}`);
		await waitForText(mark, "Remove credential", `credential actions ${provider}`);
		mark = output.length;
		pressEscape();
		await waitForText(mark, "Provider credentials", `credential parent ${provider}`);
		pressEscape();
		await waitComposer();
	}

	let mark = await open("/auth", "Provider credentials", "OpenAI Codex (OAuth)");
	await choose("Add another provider…");
	await waitForText(mark, "Provider · step 1 of 2", "auth to setup integration");
	pressEscape();
	await waitForText(mark, "Setup cancelled. Existing provider routes remain available", "auth setup cancellation");
}

async function modelTargetMatrixJourney() {
	const targets = [
		["Coordinator", 0, 2, 3],
		["Learner", 1, 1, 2],
		["coder", 2, 2, 3],
		["explore", 3, 2, 3],
		["plan", 4, 2, 3],
	];
	for (const [label, targetIndex, retryIndex, backIndex] of targets) {
		let mark = await open("/model", "Choose model", "Choose which agent receives the model route");
		pressDown(Number(targetIndex));
		pressEnter();
		await waitForText(mark, "Custom (OpenAI-compatible) · api", `${label} route picker`);
		let stepMark = output.length;
		pressUp();
		await waitForText(stepMark, "Xiaomi MiMo · api", `${label} unavailable route selection`);
		await delay(150);
		stepMark = output.length;
		pressEnter();
		await delay(200);
		pressDown();
		await waitForText(stepMark, "Custom (OpenAI-compatible) · api", `${label} unavailable route rejection`);
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "acceptance-model", `${label} model discovery`, 30_000);
		await delay(400);
		stepMark = output.length;
		pressRight();
		await waitForText(stepMark, "[ high ]", `${label} reasoning high`);
		stepMark = output.length;
		pressLeft();
		await waitForText(stepMark, "[ low ]", `${label} reasoning low`);
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "Apply permanently", `${label} model actions`);
		pressDown(Number(retryIndex));
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "Refreshing models from Custom", `${label} retry discovery`);
		await waitForText(stepMark, "acceptance-model", `${label} retry result`, 30_000);
		await delay(400);
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "Apply permanently", `${label} actions after retry`);
		pressDown(Number(backIndex));
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "Choose a model", `${label} choose-another-model action`);
		stepMark = output.length;
		pressEnter();
		await waitForText(stepMark, "Apply permanently", `${label} final model actions`);
		stepMark = output.length;
		pressEnter();
		await waitForText(
			stepMark,
			`${label} now uses Custom (OpenAI-compatible) · acceptance-model.`,
			`${label} permanent model application`,
			30_000,
		);
	}

	// Subagent confirmations have one additional branch: edit the selected
	// worker's policy and return to the graph rather than applying a route.
	let mark = await open("/model", "Choose model", "Choose which agent receives the model route");
	pressDown(2);
	pressEnter();
	await waitForText(mark, "Custom (OpenAI-compatible) · api", "coder policy route");
	let stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "acceptance-model", "coder policy model discovery", 30_000);
	await delay(400);
	pressEnter();
	stepMark = output.length;
	pressDown(1);
	pressEnter();
	await waitForText(stepMark, "Agent graph and worker profiles", "edit agent policy branch", 30_000);
	pressEscape();
	await waitComposer();
}

async function graphResetMatrixJourney() {
	for (const profile of ["coder", "explore", "plan"]) {
		let mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
		await choose(profile);
		pressDown(13);
		pressEnter();
		await waitForText(mark, `Restore built-in worker ${profile} to its defaults?`, `${profile} reset confirmation`);
		pressEscape();
		await waitComposer();

		mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
		await choose(profile);
		pressDown(13);
		pressEnter();
		await waitForText(
			mark,
			`Restore built-in worker ${profile} to its defaults?`,
			`${profile} reset confirmation retry`,
		);
		pressEnter();
		await waitForText(mark, `Built-in worker ${profile} restored to defaults.`, `${profile} reset success`, 30_000);
		pressEscape();
		await waitComposer();
	}
}

async function setupRouteMatrixJourney() {
	const routes = [
		["OpenAI Codex (OAuth)", "oauth"],
		["OpenAI API", "api"],
		["OpenRouter", "api"],
		["Kimi / Moonshot", "api"],
		["Kimi / Moonshot (China)", "api"],
		["Kimi Code (OAuth)", "oauth"],
		["DeepSeek", "api"],
		["Xiaomi MiMo", "api"],
		["Custom (OpenAI-compatible)", "baseUrl"],
	];
	for (let index = 0; index < routes.length; index += 1) {
		const [label, kind] = routes[index];
		if (kind === "oauth") continue;
		let mark = output.length;
		await submitText("/setup");
		await waitForText(mark, "Provider · step 1 of 2", `setup route ${label}`);
		await waitForText(mark, `${label}  ${kind === "oauth" ? "OAuth" : "API key"}`, `setup menu entry ${label}`);
		// Both OAuth choices are visible here. Device authorization is deliberately
		// left untouched because it would contact a real external auth service.
		await waitForText(mark, "OpenAI Codex (OAuth)  OAuth", "OpenAI OAuth menu entry");
		await waitForText(mark, "Kimi Code (OAuth)  OAuth", "Kimi OAuth menu entry");
		await delay(700);
		if (visibleText(output.slice(mark)).includes("Requesting device code"))
			throw new Error("Opening /setup unexpectedly started an OAuth network flow");
		pressDown(index);
		await delay(500);
		mark = output.length;
		pressEnter();
		if (kind === "none") {
			await waitForText(mark, `API credential connected for ${label}.`, `credential-chain route ${label}`, 30_000);
			continue;
		}
		const expected = kind === "baseUrl" ? "Base URL:" : `API key for ${label}`;
		await waitForText(mark, expected, `setup authentication screen ${label}`);
		mark = output.length;
		pressEscape();
		await waitForText(mark, "Provider · step 1 of 2", `setup back navigation ${label}`);
		mark = output.length;
		pressEscape();
		await waitForText(
			mark,
			"Setup cancelled. Existing provider routes remain available",
			`setup cancellation ${label}`,
		);
	}
}

async function planJourney() {
	let completedTurns = await completedTurnCount();
	let modelCalls = modelCompletionCount();
	let mark = await open("/plan", "Coordinator plan");
	await choose("Draft a plan");
	await waitForText(mark, "Objective", "plan objective form");
	const emptyMark = output.length;
	pressEnter();
	await delay(200);
	if (output.slice(emptyMark).includes("Instruction sent to the coordinator."))
		throw new Error("Empty plan objective was submitted");
	await fillForm("Ship a verified release");
	await waitForText(mark, "Instruction sent to the coordinator.", "plan draft submission", 30_000);
	await waitForCompletedTurn(completedTurns, "plan draft completion");
	if (modelCompletionCount() <= modelCalls) throw new Error("Plan draft never reached the model");
	completedTurns += 1;
	modelCalls = modelCompletionCount();
	await waitForText(mark, "Coordinator plan acceptance response.", "plan draft response");

	mark = await open("/plan", "Coordinator plan");
	await choose("Approve current plan");
	await waitForText(mark, "Instruction sent to the coordinator.", "plan approval", 30_000);
	await waitForCompletedTurn(completedTurns, "plan approval completion");
	if (modelCompletionCount() <= modelCalls) throw new Error("Plan approval never reached the model");
	completedTurns += 1;
	modelCalls = modelCompletionCount();
	await waitForText(mark, "Coordinator plan acceptance response.", "plan approval response");

	mark = await openWhenIdle("/plan", "Coordinator plan", "Search: type to filter", 60_000);
	await choose("Request revision");
	await waitForText(mark, "Feedback", "plan revision form");
	pressEnter();
	await delay(200);
	if (output.slice(mark).includes("Instruction sent to the coordinator."))
		throw new Error("Empty plan feedback was submitted");
	await fillForm("Split verification from publishing");
	try {
		await waitForText(mark, "Instruction sent to the coordinator.", "plan revision first submission", 5_000);
	} catch {
		// The empty-form Enter can still own the panel when the next Enter arrives.
		// Retry once after it releases input ownership.
		pressEnter();
	}
	await waitForText(mark, "Instruction sent to the coordinator.", "plan revision", 120_000);
	await waitForCompletedTurn(completedTurns, "plan revision completion");
	if (modelCompletionCount() <= modelCalls) throw new Error("Plan revision never reached the model");
	await waitForText(mark, "Coordinator plan acceptance response.", "plan revision response");
	await waitForPlanIdle();

	mark = await open("/plan", "Coordinator plan");
	await choose("Cancel plan turn");
	// The plan turns above already completed, so there is no live turn to cancel;
	// the panel must say so instead of claiming a cancellation.
	await waitForText(mark, "No plan turn is running.", "plan cancellation without a live turn");
	if (visibleText(output.slice(mark)).includes("Plan turn cancelled."))
		throw new Error("Plan cancel claimed success without a live turn");
}

async function waitForPlanIdle() {
	for (let attempt = 0; attempt < 10; attempt += 1) {
		const mark = await open("/plan", "Coordinator plan");
		await choose("Plan status");
		await waitForText(mark, "Coordinator turn:", "plan status after completion");
		const idle = visibleText(output.slice(mark)).includes("Coordinator turn: idle");
		await closePanelToComposer();
		if (idle) return;
		await delay(1_000);
	}
	throw new Error("Coordinator turn did not become idle after durable completion");
}

async function pluginJourney() {
	const archive = path.join(fixtureHome, "acceptance-plugin.tar");
	await writeFile(
		archive,
		tarArchive({
			"kageko-plugin.json": JSON.stringify({
				name: "Acceptance Plugin",
				version: "1.0.0",
				description: "A real local archive used by the PTY acceptance journey.",
			}),
		}),
	);
	let mark = await open("/plugins", "Plugins", "Install plugin");
	await choose("Install plugin");
	await waitForText(mark, "Source", "plugin source form");
	pressEnter();
	await delay(200);
	if (!visibleText(output.slice(mark)).includes("Source")) throw new Error("Empty plugin source escaped its form");
	await fillForm(`file://${archive.replaceAll("\\", "/")}`);
	await waitForText(mark, "Plugin acceptance_plugin installed.", "plugin installation", 30_000);
	await waitForText(mark, "acceptance_plugin", "installed plugin menu");

	await choose("acceptance_plugin");
	await waitForText(mark, "Uninstall plugin acceptance_plugin?", "plugin uninstall confirmation");
	pressEscape();
	await waitForText(mark, "Plugin acceptance_plugin removal cancelled.", "plugin uninstall cancellation");
	await choose("acceptance_plugin");
	await waitForText(mark, "Uninstall plugin acceptance_plugin?", "plugin uninstall confirmation retry");
	pressEnter();
	await waitForText(mark, "Plugin acceptance_plugin removed.", "plugin uninstall success");
	await stopTui();
	await cliText(["trust", "grant"]);
	const remaining = await cliJson(["capability", "list", "--session", currentSessionId, "--kind", "plugin", "--json"]);
	if (remaining.some((entry) => entry.id === "acceptance_plugin")) throw new Error("Plugin uninstall was not durable");
	await startTui();
}

async function modelJourney() {
	await stopTui();
	const configured = await cliJson(["config", "get", "--json"]);
	if (configured?.model?.baseUrl !== env.KAGEKO_BASE_URL)
		throw new Error(`Custom model baseUrl was not durable before the picker: ${JSON.stringify(configured?.model)}`);
	await startTui();
	let mark = await open("/model", "Choose model", "Choose which agent receives the model route");
	pressEnter();
	await waitForText(mark, "Custom (OpenAI-compatible) · api", "model route step");
	await waitForText(mark, "credential ready", "configured model route");
	pressEnter();
	await waitForText(mark, "Choose a model", "model discovery", 30_000);
	await waitForText(mark, "acceptance-model", "discovered acceptance model", 30_000);
	await paste("does-not-exist");
	await waitForText(mark, "No models match this search.", "model search empty state");
	let stepMark = output.length;
	pressEscape();
	await waitForText(stepMark, "acceptance-model", "model search clear");
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Apply permanently", "model confirmation choices");
	pressDown(3);
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Choose a model", "model confirmation back");
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Apply permanently", "model confirmation retry");
	pressDown(1);
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Coordinator now uses", "session-only model application", 30_000);

	await open("/model", "Choose model", "Choose which agent receives the model route");
	pressEnter();
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "acceptance-model", "permanent model rediscovery", 30_000);
	await delay(400);
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Apply permanently", "permanent model confirmation");
	stepMark = output.length;
	pressEnter();
	await waitForText(stepMark, "Coordinator now uses", "permanent model application", 30_000);
}

async function graphJourney() {
	const edits = [
		[0, "Description", "PTY coding worker", "description"],
		[1, "When to use", "Use for verified implementation", "whenToUse"],
		[4, "Provider context window", "64000", "contextLength"],
		[5, "Local context limit", "32000", "maxContextSize"],
		[6, "Output limit", "4096", "maxOutputTokens"],
		[7, "Maximum steps", "18", "maxSteps"],
		[8, "Run timeout", "120000", "timeoutMs"],
		[9, "System prompt", "Return verified evidence.", "systemPrompt"],
	];
	for (const [index, label, value, field] of edits) {
		const mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
		await choose("coder");
		await waitForText(mark, "Policy · coder", `coder ${field} policy`);
		pressDown(Number(index));
		pressEnter();
		await waitFor(
			() => new RegExp(`${label}\\r?\\n\\s*╭`).test(visibleText(output.slice(mark))),
			`coder ${field} editor`,
			15_000,
		);
		terminal.write("\x7f".repeat(600));
		await paste(String(value));
		pressEnter();
		await waitForText(mark, `coder ${field} updated.`, `coder ${field} persistence`, 30_000);
		pressEscape();
		await waitComposer();
	}
	for (const [index, field, value] of [
		[10, "Permission profile", "manual"],
		[11, "Interaction mode", "interactive"],
	]) {
		const mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
		await choose("coder");
		await waitForText(mark, "Policy · coder", `coder ${field} policy`);
		pressDown(Number(index));
		pressEnter();
		await waitForText(mark, `Worker · ${field}`, `coder ${field} choices`);
		await choose(String(value));
		await waitForText(mark, `coder ${field} set to ${value}.`, `coder ${field} persistence`, 30_000);
		await closePanelToComposer();
	}
	{
		const mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
		await choose("coder");
		await waitForText(mark, "Policy · coder", "coder tools policy");
		pressDown(12);
		pressEnter();
		await waitForText(mark, "Worker tools · coder", "coder tool picker", 30_000);
		await choose("Clear selection");
		pressEscape();
		await choose("read");
		pressEscape();
		await choose("grep");
		pressEscape();
		await choose("Save selection");
		await waitForText(mark, "coder tool access updated (2 selected).", "coder tools persistence", 30_000);
		await closePanelToComposer();
	}

	let mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
	await choose("coder");
	pressDown(2);
	pressEnter();
	await waitForText(mark, "Custom (OpenAI-compatible) · api", "graph model-route integration");
	let stepMark = output.length;
	pressEscape();
	await waitForText(stepMark, "Agent graph and worker profiles", "graph return from model route");
	pressEscape();
	await waitComposer();

	mark = await open("/graph", "Agent graph and worker profiles", "Add subagent profile");
	await choose("Add subagent profile");
	await waitForText(mark, "Profile id", "new graph profile form");
	await fillForm("coordinator");
	await waitForText(mark, "reserved system name", "reserved graph profile rejection");
	terminal.write("\x7f".repeat(100));
	await fillForm("release_worker");
	await waitForText(mark, "Subagent profile release_worker created.", "graph profile creation");
	await waitForText(mark, "Policy · release_worker", "new graph profile policy");
		pressDown(13);
	pressEnter();
	await waitForText(mark, "Delete subagent profile release_worker?", "graph profile delete confirmation");
	pressEscape();
	await delay(300);
	// Cancellation returns to the composer because confirmations replace panels.
	mark = await open("/graph", "Agent graph and worker profiles", "release_worker");
	await choose("release_worker");
		pressDown(13);
	pressEnter();
	await waitForText(mark, "Delete subagent profile release_worker?", "graph profile delete confirmation retry");
	pressEnter();
	await waitForText(mark, "Subagent profile release_worker deleted.", "graph profile deletion", 30_000);
	pressEscape();
	await waitComposer();
}

async function setupJourney() {
	let mark = output.length;
	await submitText("/setup");
	await waitForText(mark, "Provider · step 1 of 2", "setup provider picker");
	pressEscape();
	await waitForText(mark, "Setup cancelled. Existing provider routes remain available", "setup cancellation");

	mark = output.length;
	await submitText("/setup");
	await waitForText(mark, "Provider · step 1 of 2", "setup provider picker retry");
	// The first route is OAuth. Acceptance must never start a live provider
	// login, so exercise the maintained OpenAI API-key route instead.
	pressDown(1);
	pressEnter();
	await waitForText(mark, "API key for OpenAI API", "setup API credential step");
	pressEnter();
	await waitForText(mark, "API key must not be empty", "setup empty API key rejection");
	await paste("acceptance-setup-key");
	pressEnter();
	await waitForText(mark, "API credential connected for OpenAI API.", "setup credential completion", 30_000);
}

async function open(command, title, readyText = "Search: type to filter", timeoutMs = 15_000) {
	const mark = output.length;
	await submitText(command);
	await waitForText(mark, title, `${command} panel`, timeoutMs);
	await waitForText(mark, readyText, `${command} input ownership`, timeoutMs);
	if (command === "/config") {
		await waitFor(() => {
			const rendered = visibleText(output.slice(mark));
			const loading = rendered.lastIndexOf("Loading settings…");
			return loading >= 0 && rendered.lastIndexOf("Turns & compaction") > loading;
		}, "loaded settings sections", timeoutMs);
	}
	await delay(300);
	return mark;
}
async function openWhenIdle(command, title, readyText, timeoutMs) {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		const mark = output.length;
		await submitText(command);
		try {
			await waitForText(mark, title, `${command} panel`, Math.min(5_000, Math.max(1, deadline - Date.now())));
		} catch {
			// The composer can render before RuntimeSession has committed the
			// terminal turn state. Retry the actual user command until the panel,
			// rather than treating a transient unavailable notice as success.
			continue;
		}
		await waitForText(mark, readyText, `${command} input ownership`, Math.max(1, deadline - Date.now()));
		await delay(300);
		return mark;
	}
	throw new Error(`Timed out waiting for ${command} after the turn became idle\n${output.slice(-4_000)}`);
}
function modelCompletionCount() {
	return learningModel.requests.filter((request) => request.method === "POST" && request.url === "/v1/chat/completions").length;
}
async function completedTurnCount() {
	const journal = path.join(fixtureHome, ".kageko", "sessions", currentSessionId, "journal.jsonl");
	try {
		return (await readFile(journal, "utf8")).split("\n").filter((line) => line.includes('"type":"turn.end"')).length;
	} catch (error) {
		if (error.code === "ENOENT") return 0;
		throw error;
	}
}
async function waitForCompletedTurn(previousCount, label) {
	const deadline = Date.now() + 120_000;
	while (Date.now() < deadline) {
		if ((await completedTurnCount()) > previousCount) return;
		await delay(500);
	}
	throw new Error(`Timed out waiting for ${label}; ${await completedTurnCount()} completed turns, ${modelCompletionCount()} model calls\n${output.slice(-4_000)}`);
}
async function choose(label) {
	await paste(label);
	pressEnter();
	await delay(250);
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
function pressEscape() {
	terminal.write("\x1b");
}
function pressDown(count = 1) {
	terminal.write("\x1b[B".repeat(count));
}
function pressUp(count = 1) {
	terminal.write("\x1b[A".repeat(count));
}
function pressLeft() {
	terminal.write("\x1b[D");
}
function pressRight() {
	terminal.write("\x1b[C");
}
async function closePanelToComposer() {
	// Menu actions often record their status before their async finally block
	// releases input ownership. Do not race a close/new command into that tail.
	await waitForOutputIdle(400, 10_000);
	const mark = output.length;
	// Some actions leave a nested panel after closing the topmost selection.
	// Ctrl+C closes one owner at a time; wait for the composer before retrying.
	for (let attempt = 0; attempt < 3; attempt++) {
		terminal.write("\x03");
		try {
			await waitForText(mark, "Ask Kageko", "panel return to composer", 5_000);
			return;
		} catch (error) {
			if (attempt === 2) throw error;
		}
	}
}
async function waitComposer() {
	await delay(150);
}

async function assertGoal(status, objective) {
	const goal = await inspectJson(["goal", "status", "--session", currentSessionId, "--json"]);
	if (!goal || goal.status !== status || (objective && goal.objective !== objective))
		throw new Error(`Unexpected durable goal: ${JSON.stringify(goal)}`);
}
async function cliJson(args) {
	const result = await execute(process.execPath, [cli, ...args], { cwd: fixtureHome, env, windowsHide: true });
	return JSON.parse(result.stdout);
}
async function cliText(args) {
	const result = await execute(process.execPath, [cli, ...args], { cwd: fixtureHome, env, windowsHide: true });
	return result.stdout;
}
async function inspectJson(args) {
	return JSON.parse(await inspectText(args));
}
async function inspectText(args) {
	await stopTui();
	try {
		return await cliText(args);
	} finally {
		await startTui();
	}
}
async function startTui() {
	exited = false;
	const mark = output.length;
	const args = [
		cli,
		...(currentSessionId ? ["--session", currentSessionId] : []),
		...(batch === "learning" ? ["--permission", "unrestricted"] : []),
	];
	terminal = pty.spawn(process.execPath, args, {
		cwd: fixtureHome,
		env,
		name: "xterm-256color",
		cols: 140,
		rows: 50,
		useConpty: batch === "mouse",
		useConptyDll: batch === "mouse",
	});
	terminal.onData((chunk) => {
		output += chunk;
		if (process.env.KAGEKO_PTY_STREAM_LOG)
			appendFileSync(process.env.KAGEKO_PTY_STREAM_LOG, chunk);
	});
	terminal.onExit(() => {
		exited = true;
	});
	await waitForText(mark, "Ask Kageko", "TUI composer after start");
}
async function stopTui() {
	// Ctrl+C is the product's global cancel/close key: first dismiss any active
	// panel, then close an empty composer. This avoids treating `/exit` as a menu
	// search when an action intentionally returns to its parent panel.
	await delay(500);
	for (let attempt = 0; attempt < 4 && !exited; attempt += 1) {
		terminal.write("\x03");
		await delay(500);
	}
	await waitFor(() => exited, "TUI release for durable inspection", 60_000);
	await delay(300);
}
async function configure() {
	for (const args of [
		["config", "set", "model.maxContextSize", "32768"],
		["config", "set", "model.provider", '"custom"'],
		["config", "set", "model.modelName", '"acceptance-model"'],
		["config", "set", "model.baseUrl", JSON.stringify(env.KAGEKO_BASE_URL)],
		["trust", "grant"],
	])
		await execute(process.execPath, [cli, ...args], { cwd: fixtureHome, env, windowsHide: true });
}
async function waitForText(mark, text, label, timeoutMs = 15_000) {
	await waitFor(() => visibleText(output.slice(mark)).includes(text), label, timeoutMs);
}
async function waitFor(condition, label, timeoutMs) {
	const deadline = Date.now() + timeoutMs;
	while (!condition()) {
		if (Date.now() >= deadline)
			throw new Error(
				`Timed out waiting for ${label}\n${output.slice(-8_000)}\nModel requests: ${JSON.stringify(learningModel?.requests ?? [])}`,
			);
		await delay(25);
	}
}
function delay(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}
function visibleText(value) {
	return value.replace(OSC_SEQUENCE, "").replace(CSI_SEQUENCE, "");
}

async function waitForOutputIdle(idleMs, timeoutMs) {
	const deadline = Date.now() + timeoutMs;
	let previousLength = output.length;
	let unchangedSince = Date.now();
	while (Date.now() < deadline) {
		await delay(100);
		if (output.length !== previousLength) {
			previousLength = output.length;
			unchangedSince = Date.now();
		} else if (Date.now() - unchangedSince >= idleMs) return;
	}
	throw new Error(`Timed out waiting for PTY output ownership to settle\n${output.slice(-4_000)}`);
}

async function startLearningModel() {
	const requests = [];
	const server = createServer(async (request, response) => {
		requests.push({ at: Date.now(), method: request.method, url: request.url });
		if (request.method === "GET" && request.url?.endsWith("/models")) {
			response.writeHead(200, { "content-type": "application/json", connection: "close" });
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
		let body = "";
		for await (const chunk of request) body += String(chunk);
		const input = JSON.parse(body);
		const transcript = JSON.stringify(input.messages ?? []);
		const messages = Array.isArray(input.messages) ? input.messages : [];
		const latestUserIndex = messages.findLastIndex((message) => message?.role === "user");
		const latestUserContent = messages[latestUserIndex]?.content ?? "";
		const latestUserText = JSON.stringify(latestUserContent);
		const latestUserPlain = typeof latestUserContent === "string" ? latestUserContent : latestUserText;
		const turnMessages = messages.slice(latestUserIndex + 1);
		const currentTurnHasToolResult = turnMessages.some((message) => message?.role === "tool");
		const latestToolContent = turnMessages.findLast((message) => message?.role === "tool")?.content ?? "";
		const latestToolText =
			typeof latestToolContent === "string" ? latestToolContent : JSON.stringify(latestToolContent);
		requests.push({
			at: Date.now(),
			capabilitySynthesis: transcript.includes("safe external-command wrapper"),
			skillSynthesis: transcript.includes("Derive one genuinely reusable procedural skill"),
			hasToolResult: currentTurnHasToolResult,
			stream: input.stream === true,
			latestUser: latestUserPlain.slice(0, 120),
		});
		// Classify internal synthesis by the current prompt before inspecting any
		// user-task phrases. These prompts embed the session transcript, so broad
		// `includes` checks below would otherwise recursively replay a historical
		// user request instead of answering the synthesizer.
		if (latestUserPlain.startsWith("You are designing a safe external-command wrapper")) {
			const isDiscard = latestUserPlain.includes("Description: Disposable rejection-test capability");
			const isMcp = latestUserPlain.includes("Description: Read a remote test feed");
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
							name: isDiscard ? "discard-candidate" : "release-note",
							description: "Create one concise release note.",
							parameters: { type: "object", properties: { subject: { type: "string" } }, required: ["subject"] },
							command: "node",
							args: ["{{__args_json}}"],
						},
						code: "const { subject = 'release' } = JSON.parse(process.argv[2] ?? '{}'); console.log(`release-note:${subject}`);",
					});
			return sendCompletion(response, content, input.stream === true);
		}
		if (latestUserPlain.startsWith("You are the resident learner for an AI agent. Derive one genuinely reusable procedural skill"))
			return sendCompletion(
				response,
				"name: release-validation\ndescription: Validate a release before it is published.\n---\n1. Run the product acceptance suite.\n2. Inspect the generated artifacts.\n3. Report only verified results.",
				input.stream === true,
			);
		// The resident learner agent conversation carries only the five learner
		// tools; answer its proposal call with description-only args so the
		// resident synthesizer path (keyed above) still executes unchanged.
		const requestToolNames = Array.isArray(input.tools)
			? input.tools.map((tool) => String(tool?.function?.name ?? ""))
			: [];
		if (requestToolNames.includes("propose_capability") || requestToolNames.includes("propose_skill")) {
			if (currentTurnHasToolResult)
				return sendCompletion(response, "Learner run completed.", input.stream === true);
			if (requestToolNames.includes("propose_capability")) {
				const learnerMcp = latestUserPlain.includes("remote test feed");
				const learnerDiscard = latestUserPlain.includes("Disposable rejection-test capability");
				return sendToolCall(
					response,
					"propose_capability",
					{
						description: learnerMcp
							? "Read a remote test feed for recurring release checks"
							: learnerDiscard
								? "Disposable rejection-test capability"
								: "Create a concise release note for repeated release work",
						context: learnerMcp ? "remote test feed" : learnerDiscard ? "disposable capability" : "release validation workflow",
						proposedKind: learnerMcp ? "mcp" : "tool",
					},
					input.stream === true,
				);
			}
			return sendCompletion(response, "No durable skill is justified by the evidence.", input.stream === true);
		}
		if (latestUserPlain.startsWith("Summarize the following coding-agent session"))
			return sendCompletion(response, "Verified learning acceptance session summary.", input.stream === true);
		if (latestUserText.includes("PTY question")) {
			if (currentTurnHasToolResult)
				return sendCompletion(response, `Runtime observed ${latestToolText}`, input.stream === true);
			return sendToolCall(
				response,
				"ask_user",
				{
					question: "Which runtime option?",
					options: ["Alpha", "Beta"],
				},
				input.stream === true,
			);
		}
		if (latestUserText.includes("PTY approval")) {
			const label = /PTY approval ([^"\\]+)/.exec(latestUserText)?.[1] ?? "unknown";
			const commandLabel = label.endsWith("-repeat") ? label.slice(0, -"-repeat".length) : label;
			if (currentTurnHasToolResult) {
				const feedback = turnMessages.find(
					(message) => message?.role === "system" && String(message.content).includes("User approval feedback"),
				);
				const feedbackText = feedback ? /: ([\s\S]*)$/.exec(String(feedback.content))?.[1] : undefined;
				return sendCompletion(
					response,
					`Runtime approval ${label} observed ${latestToolText}${feedbackText ? ` feedback=${feedbackText}` : ""}`,
					input.stream === true,
				);
			}
			return sendToolCall(
				response,
				"bash",
				{
					command: `node -e "console.log('approval-${commandLabel}')"`,
				},
				input.stream === true,
			);
		}
		if (latestUserText.includes("PTY background activity")) {
			if (currentTurnHasToolResult)
				return sendCompletion(response, "Background activity started.", input.stream === true);
			return sendToolCall(
				response,
				"bash",
				{
					command: "node -e \"console.log('PTY_ACTIVITY_OUTPUT'); setTimeout(() => {}, 120000)\"",
					background: true,
				},
				input.stream === true,
			);
		}
		if (latestUserText.includes("Invoke the learned release-note tool")) {
			if (currentTurnHasToolResult)
				return sendCompletion(
					response,
					latestToolText.includes("release-note:benchmark")
						? "Learned tool result verified."
						: `Learned tool result invalid: ${latestToolText}`,
					input.stream === true,
				);
			return sendToolCall(response, "auto__release_note", { subject: "benchmark" }, input.stream === true);
		}
		if (latestUserText.includes("Invoke the learned release-feed MCP tool")) {
			if (currentTurnHasToolResult)
				return sendCompletion(
					response,
					`Learned MCP result verified: ${latestToolText.includes("ok") ? "ok" : latestToolText}`,
					input.stream === true,
				);
			return sendToolCall(response, "mcp__release-feed__latest_release", {}, input.stream === true);
		}
		if (latestUserText.includes("Generate a reusable release-validation skill")) {
			if (currentTurnHasToolResult)
				return sendCompletion(response, "Learned skill generation verified.", input.stream === true);
			return sendToolCall(response, "generate_skill", { name: "release-validation" }, input.stream === true);
		}
		if (
			transcript.includes("Draft an execution plan for:") ||
			transcript.includes("approved the current coordinator plan") ||
			transcript.includes("Revise the current execution plan")
		)
			return sendCompletion(response, "Coordinator plan acceptance response.", input.stream === true);
		if (currentTurnHasToolResult)
			return sendCompletion(response, "need_capability recorded for learner review.", input.stream === true);
		const isDiscard = latestUserPlain.includes("disposable capability");
		const isMcp = latestUserPlain.includes("remote test feed");
		return sendToolCall(
			response,
			"need_capability",
			{
				description: isMcp
					? "Read a remote test feed for recurring release checks"
					: isDiscard
						? "Disposable rejection-test capability"
						: "Create a concise release note for repeated release work",
				context: isMcp ? "remote test feed" : isDiscard ? "disposable capability" : "release validation workflow",
				proposedKind: isMcp ? "mcp" : "tool",
				evidence: {
					scope: isMcp ? "external_service" : "workflow",
					futureTasks: ["weekly release", "hotfix release"],
					alternativesChecked: ["existing built-in tools"],
				},
			},
			input.stream === true,
		);
	});
	await new Promise((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	if (!address || typeof address === "string") throw new Error("Learning model did not receive a TCP address");
	return {
		baseUrl: `http://127.0.0.1:${address.port}/v1`,
		requests,
		close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
	};
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
	const id = `capability-${Date.now()}`;
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
function mcpServerCode() {
	return [
		"const readline = require('node:readline');",
		"readline.createInterface({ input: process.stdin }).on('line', (line) => {",
		"  const request = JSON.parse(line);",
		"  if (request.id === undefined) return;",
		"  const result = request.method === 'initialize' ? { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'release-feed', version: '1.0.0' } } : request.method === 'tools/list' ? { tools: [{ name: 'latest_release', description: 'Return release status', inputSchema: { type: 'object' } }] } : { content: [{ type: 'text', text: 'ok' }] };",
		"  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, result }) + '\\n');",
		"});",
	].join("\n");
}

function tarArchive(files) {
	const chunks = [];
	for (const [name, source] of Object.entries(files)) {
		const data = Buffer.from(source);
		const header = Buffer.alloc(512);
		header.write(name, 0, 100, "utf8");
		header.write("0000644\0", 100, 8, "ascii");
		header.write("0000000\0", 108, 8, "ascii");
		header.write("0000000\0", 116, 8, "ascii");
		header.write(`${data.length.toString(8).padStart(11, "0")}\0`, 124, 12, "ascii");
		header.write(
			`${Math.floor(Date.now() / 1000)
				.toString(8)
				.padStart(11, "0")}\0`,
			136,
			12,
			"ascii",
		);
		header.fill(0x20, 148, 156);
		header[156] = "0".charCodeAt(0);
		header.write("ustar\0", 257, 6, "ascii");
		header.write("00", 263, 2, "ascii");
		const checksum = header.reduce((sum, byte) => sum + byte, 0);
		header.write(`${checksum.toString(8).padStart(6, "0")}\0 `, 148, 8, "ascii");
		chunks.push(header, data, Buffer.alloc((512 - (data.length % 512)) % 512));
	}
	chunks.push(Buffer.alloc(1024));
	return Buffer.concat(chunks);
}
