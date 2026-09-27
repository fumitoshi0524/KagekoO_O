import { describe, expect, it, vi } from "vitest";
import path from "node:path";
import type { KagekoClient } from "@kageko/node-sdk";
import { TerminalController, VirtualTerminal, decodeInput } from "@kageko/tui-kit";
import { win32ConsoleModeCandidates } from "../../../packages/tui-kit/src/terminal.js";

import {
	commandPanelPrefills,
	commandPanelQuery,
	historySafeInput,
	KagekoTui,
	splitCommandArguments,
} from "../src/tui/app.js";
import { findSlashCommand, slashCommands } from "../src/tui/commands/registry.js";
import type { CommandContext, InteractivePanelName } from "../src/tui/commands/types.js";

describe("TUI audit regressions", () => {
	it("uses Kimi's standard Windows VT input helper path", () => {
		const candidates = win32ConsoleModeCandidates("C:\\app\\dist", "C:\\node\\node.exe");
		expect(candidates).toHaveLength(3);
		expect(candidates.every((candidate) => path.basename(candidate) === "win32-console-mode.node")).toBe(true);
	});

	it("discards a late panel result after its signal is cancelled", async () => {
		let resolveConfiguration!: (value: unknown) => void;
		const getConfiguration = vi.fn(
			() =>
				new Promise<unknown>((resolve) => {
					resolveConfiguration = resolve;
				}),
		);
		const tui = new KagekoTui({ client: { getConfiguration } as unknown as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			panelAbort: AbortController;
			panelRequest(method: (...args: never[]) => Promise<unknown>, args: readonly never[]): Promise<unknown>;
		};
		const abort = new AbortController();
		internals.panelAbort = abort;
		const request = internals.panelRequest(getConfiguration as (...args: never[]) => Promise<unknown>, []);
		abort.abort(new Error("cancelled"));
		resolveConfiguration({});

		await expect(request).rejects.toThrow("cancelled");
	});

	it("queries pending interactions only for the active session", async () => {
		const listPendingInteractions = vi.fn(async () => []);
		const tui = new KagekoTui({ client: { listPendingInteractions } as unknown as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			session: { id: string };
			pendingInteractions: readonly unknown[];
			render(): void;
			refreshPendingInteractions(): Promise<void>;
		};
		internals.session = { id: "current-session" };
		internals.pendingInteractions = [{ request: { id: "stale-request" } }];
		internals.render = () => {};

		await internals.refreshPendingInteractions();

		expect(listPendingInteractions).toHaveBeenCalledWith("current-session");
		expect(internals.pendingInteractions).toEqual([]);
	});

	it("preserves a single pasted newline instead of silently joining the text", () => {
		const tui = new KagekoTui({ client: {} as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			editor: { text: string };
			refreshCompletionAfterEdit(): void;
			handleKey(key: unknown): void;
			expandPastes(text: string): string;
		};
		internals.refreshCompletionAfterEdit = () => {};

		internals.handleKey({ name: "paste", sequence: "", text: "first\nsecond" });

		expect(internals.expandPastes(internals.editor.text)).toBe("first\nsecond");
	});

	it("suppresses OAuth browser launch when the headless safety flag is enabled", () => {
		const previous = process.env["KAGEKO_DISABLE_EXTERNAL_BROWSER"];
		process.env["KAGEKO_DISABLE_EXTERNAL_BROWSER"] = "1";
		try {
			const openExternal = vi.fn();
			const tui = new KagekoTui({
				client: {} as KagekoClient,
				cwd: process.cwd(),
				openExternal,
			});
			const internals = tui as unknown as { openOAuthUrl(url: string): void };

			internals.openOAuthUrl("https://claude.ai/oauth/authorize");

			expect(openExternal).not.toHaveBeenCalled();
		} finally {
			if (previous === undefined) delete process.env["KAGEKO_DISABLE_EXTERNAL_BROWSER"];
			else process.env["KAGEKO_DISABLE_EXTERNAL_BROWSER"] = previous;
		}
	});

	it("routes every registered panel command through the guided surface and preserves its arguments", async () => {
		const panelCommands = slashCommands.filter(
			(command) => !["exit", "cancel", "interactions", "shell", "setup"].includes(command.name),
		);
		for (const command of panelCommands) {
			const openPanel = vi.fn();
			const context = {
				client: {},
				session: { cancel: vi.fn() },
				cwd: process.cwd(),
				notice: vi.fn(),
				showLines: vi.fn(),
				showDetails: vi.fn(),
				showOverlay: vi.fn(),
				showInteractions: vi.fn(),
				openShell: vi.fn(),
				openSetup: vi.fn(),
				openOAuthSetup: vi.fn(),
				openPanel,
				refreshLearningPending: vi.fn(),
				confirm: vi.fn(async () => true),
				switchSession: vi.fn(),
				quit: vi.fn(),
			} as unknown as CommandContext;
			const args = command.argumentHint === "(no arguments)" ? [] : ["audit-marker", "value"];

			await command.run(args, context);

			expect(openPanel, `${command.name} must enter an interactive panel`).toHaveBeenCalledOnce();
			expect(openPanel.mock.calls[0]?.[1]).toEqual(command.name === "permission" ? ["permission"] : args);
			for (const alias of command.aliases ?? []) expect(findSlashCommand(alias)).toBe(command);
		}
	});

	it("renders every public slash command as an actionable /help row", async () => {
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			openInteractivePanel(panel: InteractivePanelName): Promise<void>;
			panelActions: Map<string, () => Promise<void> | void>;
			showPanelResult: ReturnType<typeof vi.fn>;
			render: ReturnType<typeof vi.fn>;
		};
		internals.render = vi.fn();
		internals.showPanelResult = vi.fn();

		await internals.openInteractivePanel("help");

		const publicCommands = slashCommands.filter((command) => !command.hidden);
		const panel = (tui as unknown as { panel: { kind: string; items?: readonly { id: string; label: string }[] } })
			.panel;
		expect(panel.kind).toBe("menu");
		expect(panel.items?.map((item) => item.id)).toEqual(["keyboard", ...publicCommands.map((command) => command.name)]);
		for (const command of publicCommands) expect(internals.panelActions.has(command.name)).toBe(true);
		await internals.panelActions.get("memory")?.();
		expect(internals.showPanelResult).toHaveBeenCalledWith(
			expect.arrayContaining(["Command: /memory"]),
			"Help · /memory",
			"help",
		);
	});

	it("keeps provider auth commands scoped to Kageko's unified credential flows", async () => {
		expect(findSlashCommand("settings")).toBe(findSlashCommand("config"));
		expect(findSlashCommand("provider")).toBeUndefined();
		expect(findSlashCommand("providers")).toBeUndefined();
		expect(findSlashCommand("login")).toBeUndefined();
		expect(findSlashCommand("logout")).toBeUndefined();
		expect(findSlashCommand("disconnect")).toBeUndefined();
		expect(findSlashCommand("permissions")).toBe(findSlashCommand("permission"));

		const openPanel = vi.fn();
		const permission = findSlashCommand("permission")!;
		await permission.run([], {
			client: {} as KagekoClient,
			session: undefined,
			cwd: process.cwd(),
			notice: vi.fn(),
			showLines: vi.fn(),
			showDetails: vi.fn(),
			showOverlay: vi.fn(),
			showInteractions: vi.fn(),
			openShell: vi.fn(),
			openSetup: vi.fn(),
			openPanel,
			refreshLearningPending: vi.fn(),
			confirm: vi.fn(async () => true),
			switchSession: vi.fn(),
			quit: vi.fn(),
		});
		expect(openPanel).toHaveBeenCalledWith("config", ["permission"]);

		const tui = new KagekoTui({
			client: { getConfiguration: vi.fn(async () => ({})) } as unknown as KagekoClient,
			cwd: process.cwd(),
		});
		const internals = tui as unknown as {
			openSettingsSection(section: { id: string }): Promise<void>;
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
		};
		internals.openSettingsSection = vi.fn(async () => {});
		await internals.openCommandPanel("config", ["permission"]);
		expect(internals.openSettingsSection).toHaveBeenCalledWith(expect.objectContaining({ id: "permission" }));
	});

	it("labels graph roles, built-in workers, and custom workers separately", async () => {
		const tui = new KagekoTui({
			client: {
				getConfiguration: vi.fn(async () => ({
					agentGraph: {
						subagents: {
							coder: { description: "Built-in implementation worker" },
							analyst: { description: "Project-specific worker" },
						},
					},
				})),
			} as unknown as KagekoClient,
			cwd: process.cwd(),
		});
		const internals = tui as unknown as {
			openGraphPanel(): Promise<void>;
			render(): void;
			panel: { title: string; items: readonly { id: string; detail?: string }[] };
		};
		internals.render = () => {};
		await internals.openGraphPanel();

		expect(internals.panel.title).toBe("Agent graph and worker profiles");
		expect(internals.panel.items.find((item) => item.id === "coordinator")?.detail).toContain("Graph role");
		expect(internals.panel.items.find((item) => item.id === "subagent:coder")?.detail).toContain("Built-in worker");
		expect(internals.panel.items.find((item) => item.id === "subagent:analyst")?.detail).toContain("Custom worker");
	});

	it("reserves built-in worker ids for graph-managed built-in profiles", async () => {
		const updateConfiguration = vi.fn();
		const tui = new KagekoTui({
			client: { updateConfiguration } as unknown as KagekoClient,
			cwd: process.cwd(),
		});
		const internals = tui as unknown as {
			openNewSubagentProfileForm(): void;
			openFormPanel: ReturnType<typeof vi.fn>;
			record: ReturnType<typeof vi.fn>;
		};
		internals.openFormPanel = vi.fn();
		internals.record = vi.fn();
		internals.openNewSubagentProfileForm();
		const submit = internals.openFormPanel.mock.calls[0]?.[3] as (value: string) => Promise<void>;

		await submit("coder");

		expect(updateConfiguration).not.toHaveBeenCalled();
		expect(internals.record).toHaveBeenCalledWith("warning", expect.stringContaining("reserved system name"));
	});

	it.each([
		["exit", "quit"],
		["cancel", "cancel"],
		["interactions", "showInteractions"],
		["shell", "openShell"],
		["setup", "openSetup"],
	] as const)("keeps /%s on its dedicated TUI surface", async (name, expectedCall) => {
		const calls = {
			quit: vi.fn(async () => {}),
			cancel: vi.fn(async () => {}),
			showInteractions: vi.fn(),
			openShell: vi.fn(async () => {}),
			openSetup: vi.fn(async () => {}),
		};
		const command = findSlashCommand(name)!;
		const context = {
			client: {},
			session: { cancel: calls.cancel },
			cwd: process.cwd(),
			notice: vi.fn(),
			showLines: vi.fn(),
			showDetails: vi.fn(),
			showOverlay: vi.fn(),
			showInteractions: calls.showInteractions,
			openShell: calls.openShell,
			openSetup: calls.openSetup,
			openOAuthSetup: vi.fn(),
			openPanel: vi.fn(),
			refreshLearningPending: vi.fn(),
			confirm: vi.fn(async () => true),
			switchSession: vi.fn(),
			quit: calls.quit,
		} as unknown as CommandContext;

		await command.run([], context);

		expect(calls[expectedCall]).toHaveBeenCalledOnce();
	});

	it("routes API-key login into the credential form and OAuth login into setup", async () => {
		const openPanel = vi.fn();
		const openOAuthSetup = vi.fn(async () => {});
		const notice = vi.fn();
		const context = {
			client: {},
			session: undefined,
			cwd: process.cwd(),
			notice,
			showLines: vi.fn(),
			showDetails: vi.fn(),
			showOverlay: vi.fn(),
			showInteractions: vi.fn(),
			openShell: vi.fn(async () => {}),
			openSetup: vi.fn(async () => {}),
			openOAuthSetup,
			openPanel,
			refreshLearningPending: vi.fn(),
			confirm: vi.fn(async () => true),
			switchSession: vi.fn(),
			quit: vi.fn(async () => {}),
		} as unknown as CommandContext;
		const auth = findSlashCommand("auth")!;

		await auth.run(["login", "openai-api"], context);
		expect(openPanel).toHaveBeenCalledWith("auth", ["set", "openai-api"]);
		expect(notice).not.toHaveBeenCalled();

		await auth.run(["login", "openai-codex"], context);
		expect(openOAuthSetup).toHaveBeenCalledWith("openai-codex");
	});

	it.each([
		["sessions", ["session-id"], "session-id"],
		["delete", ["session-id"], "session-id"],
		["help", ["memory"], "/memory"],
		["theme", ["dark"], "dark"],
		["archive", ["off"], "restore"],
		["activity", ["current"], "current"],
		["activity", ["history"], "history"],
		["activity", ["task-id"], "task-id"],
		["capabilities", ["mcp"], "mcp"],
		["cron", ["create", "0 9 * * *", "Review"], "create"],
		["cron", ["delete", "cron-id"], "cron-id"],
		["cron", ["list"], ""],
		["goal", ["status"], "status"],
		["goal", ["pause"], "pause"],
		["goal", ["resume"], "resume"],
		["goal", ["complete"], "complete"],
		["goal", ["create", "ship", "feature"], "create"],
		["plan", ["status"], "status"],
		["plan", ["approve"], "approve"],
		["plan", ["cancel"], "cancel"],
		["plan", ["revise", "add", "tests"], "revise"],
		["compact", ["preserve", "tests"], "preserve tests"],
		["memory", ["status"], "status"],
		["memory", ["query", "cache", "bug"], "search"],
		["memory", ["remember", "use", "pnpm"], "remember"],
		["memory", ["recall", "code style"], "recall"],
		["memory", ["index"], "index"],
		["learn", ["status"], "status"],
		["learn", ["pending"], ""],
		["learn", ["approve", "proposal-id"], "proposal-id"],
		["learn", ["reject", "proposal-id"], "proposal-id"],
		["skills", ["list"], ""],
		["skills", ["reload"], "reload"],
		["skills", ["remove", "skill-id"], "skill-id"],
		["mcp", ["list"], ""],
		["mcp", ["add", "server"], "add"],
		["mcp", ["remove", "server-id"], "server-id"],
		["mcp", ["auth", "server-id"], "server-id"],
		["plugins", ["list"], ""],
		["plugins", ["install", "source"], "install"],
		["plugins", ["uninstall", "plugin-id"], "plugin-id"],
		["tools", ["unexpected"], "unexpected"],
		["model", ["show"], "show"],
		["model", ["discover", "openai"], "discover"],
		["model", ["set", "openai", "gpt-5"], "set"],
		["graph", ["set", "worker", "maxSteps", "5"], ""],
		["config", ["get"], ""],
		["config", ["path", "user"], ""],
		["config", ["set", "model.maxContextSize", "64000"], ""],
		["auth", ["status", "openai"], "openai"],
		["auth", ["set", "openai"], "openai"],
		["auth", ["remove", "openai"], "openai"],
		["auth", ["login", "openai"], "openai"],
		["trust", ["status"], "status"],
		["trust", ["grant"], "grant"],
		["trust", ["revoke"], "revoke"],
		["graph", ["show"], ""],
	] as const)("maps /%s %j to its visible guided action", (panel, args, expected) => {
		expect(commandPanelQuery(panel as InteractivePanelName, args)).toBe(expected);
	});

	it.each([
		["new", ["A", "session"], ["A session"]],
		["rename", ["A", "title"], ["A title"]],
		["cron", ["create", "0 9 * * *", "Review", "PR"], ["0 9 * * *", "Review PR"]],
		["goal", ["create", "Ship", "feature"], ["Ship feature"]],
		["plan", ["revise", "Add", "tests"], ["Add tests"]],
		["memory", ["query", "slow", "tests"], ["slow tests"]],
		["plugins", ["install", "owner/repo"], ["owner/repo"]],
	] as const)("prefills %s form steps", (panel, args, expected) => {
		expect(commandPanelPrefills(panel as InteractivePanelName, args)).toEqual(expected);
	});

	it("splits slash arguments with quoted spaces, preserves Windows paths, and reports unclosed quotes", () => {
		expect(splitCommandArguments('--path "folder with spaces" --flag')).toEqual([
			"--path",
			"folder with spaces",
			"--flag",
		]);
		expect(splitCommandArguments('cron create "0 9 * * *" "Review PR"')).toEqual([
			"cron",
			"create",
			"0 9 * * *",
			"Review PR",
		]);
		expect(splitCommandArguments("C:\\tools\\server.exe")).toEqual(["C:\\tools\\server.exe"]);
		expect(() => splitCommandArguments('--path "unfinished')).toThrow("Unclosed quote");
	});

	it("preserves quoted cron arguments through slash dispatch", async () => {
		const tui = new KagekoTui({ client: {} as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			runCommand(command: string): Promise<void>;
			openCommandPanel: ReturnType<typeof vi.fn>;
			refreshRuntimeModel: ReturnType<typeof vi.fn>;
			session: { id: string } | undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.openCommandPanel = vi.fn();
		internals.refreshRuntimeModel = vi.fn(async () => {});
		internals.session = { id: "active" };
		internals.render = vi.fn();

		await internals.runCommand('/cron create "0 9 * * *" "Review pull requests"');

		expect(internals.openCommandPanel).toHaveBeenCalledWith("cron", ["create", "0 9 * * *", "Review pull requests"]);
	});

	it.each(["/auth set openai sk-secret-value", '/config set model.apiKey "sk-secret-value"'])(
		"redacts credential-bearing command history for %s",
		(command) => {
			expect(historySafeInput(command)).not.toContain("sk-secret-value");
			expect(historySafeInput(command)).toMatch(/\[redacted\]$/);
		},
	);

	it("keeps confirmation choice visible and lets Enter confirm or cancel", async () => {
		const tui = new KagekoTui({ client: {} as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			pendingConfirm: { message: string; resolve(value: boolean): void } | undefined;
			confirmChoice: number;
			handleConfirmKey(key: { name: string; sequence: string }): void;
			render(): void;
		};
		internals.render = vi.fn();
		const result = new Promise<boolean>((resolve) => {
			internals.pendingConfirm = { message: "Proceed?", resolve };
		});
		internals.confirmChoice = 0;

		internals.handleConfirmKey({ name: "down", sequence: "" });
		expect(internals.confirmChoice).toBe(1);
		internals.handleConfirmKey({ name: "enter", sequence: "\r" });
		await expect(result).resolves.toBe(false);
	});

	it("edits form text at the cursor instead of appending every character", async () => {
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			openFormPanel(title: string, label: string, value: string, submit: (value: string) => void): void;
			handlePanelKey(key: { name: string; sequence: string; text?: string }): Promise<void>;
			panel: { kind: "form"; value: string; cursorIndex: number } | undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.render = vi.fn();
		internals.openFormPanel("Edit value", "Value", "abcd", vi.fn());

		await internals.handlePanelKey({ name: "left", sequence: "" });
		await internals.handlePanelKey({ name: "character", sequence: "X", text: "X" });

		expect(internals.panel?.value).toBe("abcXd");
		expect(internals.panel?.cursorIndex).toBe(4);
		await internals.handlePanelKey({ name: "backspace", sequence: "" });
		expect(internals.panel?.value).toBe("abcd");
		expect(internals.panel?.cursorIndex).toBe(3);
	});

	it("keeps mouse reporting disabled while retaining terminal mouse sequence decoding", () => {
		expect(decodeInput("\x1b[<0;4;7M")[0]).toMatchObject({
			name: "mouse",
			mouse: { action: "press", button: 0, col: 4, row: 7 },
		});
		expect(decodeInput("\x1b[<0;4;7m")[0]?.mouse?.action).toBe("release");
		expect(decodeInput("\x1b[<65;4;7M")[0]).toMatchObject({
			name: "wheeldown",
			mouse: { action: "wheel", row: 7 },
		});

		const input = new VirtualTerminal();
		const output = new VirtualTerminal();
		const terminal = new TerminalController(input, output);
		terminal.start();
		terminal.stop();

		expect(output.writes.join("")).not.toMatch(/\x1b\[\?(?:9|100[0-3]|1005|1006|1015|1016)[hl]/);
	});

	it("requires confirmation for fork and archive-off routes and keeps memory recall interactive", async () => {
		const archiveSession = vi.fn(async () => {});
		const forkSession = vi.fn(async () => ({ id: "forked" }));
		const recallProfile = vi.fn(async () => [{ scope: "user", fact: "Use pnpm" }]);
		const tui = new KagekoTui({
			client: { archiveSession, forkSession, recallProfile } as unknown as KagekoClient,
			cwd: process.cwd(),
		});
		const internals = tui as unknown as {
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			session: { id: string };
			askConfirm(message: string): Promise<boolean>;
			switchSession(session: unknown): Promise<void>;
			openFormPanel: ReturnType<typeof vi.fn>;
			panelRequestOptions(): object;
			showPanelResult: ReturnType<typeof vi.fn>;
		};
		internals.session = { id: "source" };
		internals.askConfirm = vi.fn(async () => false);
		internals.switchSession = vi.fn(async () => {});
		internals.openFormPanel = vi.fn();
		internals.panelRequestOptions = () => ({});
		internals.showPanelResult = vi.fn();

		await internals.openCommandPanel("fork", []);
		await internals.openCommandPanel("archive", ["off"]);
		expect(internals.askConfirm).toHaveBeenCalledTimes(2);
		expect(forkSession).not.toHaveBeenCalled();
		expect(archiveSession).not.toHaveBeenCalled();

		await internals.openCommandPanel("memory", ["recall", "team", "conventions"]);
		expect(internals.openFormPanel).toHaveBeenCalledWith(
			"Recall profile memory",
			"Query",
			"team conventions",
			expect.any(Function),
		);
		const submit = internals.openFormPanel.mock.calls[0]?.[3] as (query: string) => Promise<void>;
		await submit("team conventions");
		expect(recallProfile).toHaveBeenCalledWith("source", "team conventions", {});
		expect(internals.showPanelResult).toHaveBeenCalledWith(["user · Use pnpm"], "Profile memory", "memory");
	});

	it("opens MCP add as a guided three-field form instead of parsing JSON", async () => {
		const tui = new KagekoTui({ client: {} as KagekoClient, cwd: process.cwd() });
		const internals = tui as unknown as {
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			openMcpAddWizard(args: readonly string[]): void;
		};
		internals.openMcpAddWizard = vi.fn();

		await internals.openCommandPanel("mcp", ["add", "filesystem", "npx", "--yes", "@mcp/server-filesystem"]);

		expect(internals.openMcpAddWizard).toHaveBeenCalledWith(["filesystem", "npx", "--yes", "@mcp/server-filesystem"]);
	});

	it("keeps quoted MCP argument values grouped in the guided form", async () => {
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			openMcpAddWizard(args: readonly string[]): void;
			panelSubmit: ((value: string) => Promise<void>) | undefined;
			panel: { kind: "form"; value: string } | undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.render = vi.fn();
		internals.openMcpAddWizard(["filesystem", "npx", "--path", "folder with spaces"]);
		await internals.panelSubmit?.("filesystem");
		await internals.panelSubmit?.("npx");

		expect(internals.panel?.value).toBe('--path "folder with spaces"');
	});

	it("opens /graph set in a validated field editor with the typed value prefilled", async () => {
		const updateConfiguration = vi.fn(async () => {});
		const input = new VirtualTerminal();
		const output = new VirtualTerminal();
		const tui = new KagekoTui({
			client: {
				getConfiguration: vi.fn(async () => ({ agentGraph: { subagents: { worker: { maxSteps: 3 } } } })),
				updateConfiguration,
			} as unknown as KagekoClient,
			cwd: process.cwd(),
			input,
			output,
		});
		const internals = tui as unknown as {
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			panel: { kind: "graph"; target: { profileId?: string }; editing?: { field: string; value: string } } | undefined;
			handleGraphPanelKey(key: { name: string; sequence: string; text?: string }): Promise<void>;
		};

		await internals.openCommandPanel("graph", ["set", "worker", "maxSteps", "5"]);

		expect(internals.panel?.kind).toBe("graph");
		expect(internals.panel?.target.profileId).toBe("worker");
		expect(internals.panel?.editing).toMatchObject({ field: "maxSteps", value: "5" });
		expect(updateConfiguration).not.toHaveBeenCalled();
		await internals.handleGraphPanelKey({ name: "left", sequence: "" });
		await internals.handleGraphPanelKey({ name: "character", sequence: "0", text: "0" });
		expect(internals.panel?.editing?.value).toBe("05");
	});

	it("opens worker tools as a selectable checklist and saves only selected tools", async () => {
		const updateConfiguration = vi.fn(async () => {});
		const listTools = vi.fn(async () => [
			{ name: "write_file", provenance: { kind: "builtin", ownerId: "filesystem" } },
			{ name: "read_file", provenance: { kind: "builtin", ownerId: "filesystem" } },
		]);
		const config = { agentGraph: { subagents: { worker: { tools: ["read_file"] } } } };
		const tui = new KagekoTui({
			client: {
				getConfiguration: vi.fn(async () => config),
				listTools,
				updateConfiguration,
			} as unknown as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			session: { id: string };
			openGraphSetPanel(args: readonly string[]): Promise<void>;
			handlePanelKey(key: { name: string; sequence: string; text?: string }): Promise<void>;
			panel:
				| {
						kind: string;
						title?: string;
						query?: string;
						items?: readonly { id: string; label: string }[];
						selected?: number;
				  }
				| undefined;
			interactivePanelLines(): readonly { spans: readonly { text: string }[] }[];
			render: ReturnType<typeof vi.fn>;
			refreshRuntimeModel: () => Promise<void>;
			reopenAgentProfilePanel: () => Promise<void>;
			record: ReturnType<typeof vi.fn>;
		};
		internals.session = { id: "session-1" };
		internals.render = vi.fn();
		internals.refreshRuntimeModel = vi.fn(async () => {});
		internals.reopenAgentProfilePanel = vi.fn(async () => {});
		internals.record = vi.fn();

		await internals.openGraphSetPanel(["worker", "tools", "typed_tool_name"]);

		expect(internals.panel).toMatchObject({
			kind: "menu",
			title: "Worker tools · worker",
			query: "typed_tool_name",
		});
		expect(internals.panel?.items?.map((item) => item.id)).toContain("worker-tools:tool:write_file");
		expect(internals.panel?.items?.map((item) => item.id)).not.toContain("worker-tools:tool:typed_tool_name");
		expect(
			internals
				.interactivePanelLines()
				.flatMap((line) => line.spans.map((span) => span.text))
				.join("\n"),
		).toContain("No matching actions.");
		expect(listTools).toHaveBeenCalledWith("session-1", expect.any(Object));
		expect(updateConfiguration).not.toHaveBeenCalled();
		await internals.handlePanelKey({ name: "escape", sequence: "\x1b" });
		expect(internals.panel?.query).toBe("");

		const menu = internals.panel!;
		menu.selected = menu.items!.findIndex((item) => item.id === "worker-tools:tool:write_file");
		await internals.handlePanelKey({ name: "enter", sequence: "\r" });
		expect(internals.panel?.items?.find((item) => item.id === "worker-tools:tool:write_file")?.label).toContain("☑");

		const updatedMenu = internals.panel!;
		updatedMenu.selected = updatedMenu.items!.findIndex((item) => item.id === "worker-tools:save");
		await internals.handlePanelKey({ name: "enter", sequence: "\r" });

		expect(updateConfiguration).toHaveBeenCalledWith(
			{ agentGraph: { subagents: { worker: { tools: ["read_file", "write_file"] } } } },
			"user",
			expect.objectContaining({ signal: expect.any(AbortSignal) }),
		);
	});

	it("opens worker permission and interaction modes as fixed option lists", async () => {
		const updateConfiguration = vi.fn(async () => {});
		const config = {
			agentGraph: {
				subagents: { worker: { permissionProfile: "workspace", interactionMode: "interactive" } },
			},
		};
		const tui = new KagekoTui({
			client: {
				getConfiguration: vi.fn(async () => config),
				updateConfiguration,
			} as unknown as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const target = {
			id: "subagent:worker",
			label: "worker",
			detail: "Custom worker profile",
			kind: "subagent" as const,
			profileId: "worker",
		};
		const internals = tui as unknown as {
			openGraphSetPanel(args: readonly string[]): Promise<void>;
			openAgentProfilePanel(
				target: { id: string; label: string; detail: string; kind: "subagent"; profileId: string },
				config: Record<string, unknown>,
			): void;
			handleGraphPanelKey(key: { name: string; sequence: string }): Promise<void>;
			panel:
				| {
						kind: string;
						fields?: readonly string[];
						fieldIndex?: number;
						items?: readonly { id: string; label: string }[];
				  }
				| undefined;
			render: ReturnType<typeof vi.fn>;
			refreshRuntimeModel: () => Promise<void>;
			reopenAgentProfilePanel: () => Promise<void>;
			record: ReturnType<typeof vi.fn>;
		};
		internals.render = vi.fn();
		internals.refreshRuntimeModel = vi.fn(async () => {});
		internals.reopenAgentProfilePanel = vi.fn(async () => {});
		internals.record = vi.fn();

		await internals.openGraphSetPanel(["worker", "permissionProfile", "arbitrary_value"]);
		expect(internals.panel?.kind).toBe("menu");
		expect(internals.panel?.items?.map((item) => item.id)).toEqual(["manual", "workspace", "unrestricted"]);
		expect(updateConfiguration).not.toHaveBeenCalled();

		internals.openAgentProfilePanel(target, config);
		internals.panel!.fieldIndex = internals.panel!.fields!.indexOf("interactionMode");
		await internals.handleGraphPanelKey({ name: "enter", sequence: "\r" });
		expect(internals.panel?.items?.map((item) => item.id)).toEqual(["interactive", "unattended"]);
		expect(updateConfiguration).not.toHaveBeenCalled();
	});

	it("renders worker name and free-text fields in the shared framed input style", () => {
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const target = {
			id: "subagent:worker",
			label: "worker",
			detail: "Custom worker profile",
			kind: "subagent" as const,
			profileId: "worker",
		};
		const internals = tui as unknown as {
			openNewSubagentProfileForm(): void;
			openAgentProfilePanel(
				target: { id: string; label: string; detail: string; kind: "subagent"; profileId: string },
				config: Record<string, unknown>,
			): void;
			interactivePanelLines(): readonly { spans: readonly { text: string }[] }[];
			panel:
				| {
						kind: string;
						editing?: { field: string; value: string; cursorIndex: number };
				  }
				| undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.render = vi.fn();

		internals.openNewSubagentProfileForm();
		const nameInput = internals
			.interactivePanelLines()
			.map((line) => line.spans.map((span) => span.text).join(""))
			.join("\n");
		expect(nameInput).toContain("╭");
		expect(nameInput).toContain("security-review");
		expect(nameInput).toContain("Starts with a letter");

		internals.openAgentProfilePanel(target, { agentGraph: { subagents: { worker: {} } } });
		internals.panel!.editing = { field: "description", value: "", cursorIndex: 0 };
		const descriptionInput = internals
			.interactivePanelLines()
			.map((line) => line.spans.map((span) => span.text).join(""))
			.join("\n");
		expect(descriptionInput).toContain("╭");
		expect(descriptionInput).toContain("Short summary shown to the coordinator.");
	});

	it("routes /graph set provider/model requests into the reviewed model picker", async () => {
		const getConfiguration = vi.fn(async () => ({ agentGraph: { subagents: { worker: {} } } }));
		const input = new VirtualTerminal();
		const output = new VirtualTerminal();
		const tui = new KagekoTui({
			client: { getConfiguration } as unknown as KagekoClient,
			cwd: process.cwd(),
			input,
			output,
		});
		const internals = tui as unknown as {
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			panel: { kind: "model"; step: string; routeIndex: number; routes: readonly { provider: string }[] } | undefined;
			requestedModelQuery: string | undefined;
		};

		await internals.openCommandPanel("graph", ["set", "worker", "openai-api", "gpt-5"]);

		expect(internals.panel?.kind).toBe("model");
		expect(internals.panel?.step).toBe("route");
		expect(internals.panel?.routes[internals.panel.routeIndex]?.provider).toBe("openai-api");
		expect(internals.requestedModelQuery).toBe("gpt-5");
	});

	it("preserves model auth and context arguments in the model review panel", async () => {
		const input = new VirtualTerminal();
		const output = new VirtualTerminal();
		const tui = new KagekoTui({
			client: { getConfiguration: vi.fn(async () => ({})) } as unknown as KagekoClient,
			cwd: process.cwd(),
			input,
			output,
		});
		const internals = tui as unknown as {
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			panel:
				| {
						kind: "model";
						step: string;
						routeIndex: number;
						routes: readonly { provider: string; authMode: string }[];
						contextLimitOverride?: number;
				  }
				| undefined;
			requestedModelQuery: string | undefined;
		};

		await internals.openCommandPanel("model", ["set", "openai-api", "gpt-5", "64000", "api"]);

		expect(internals.panel?.kind).toBe("model");
		expect(internals.panel?.routes[internals.panel.routeIndex]).toMatchObject({
			provider: "openai-api",
			authMode: "api",
		});
		expect(internals.panel?.contextLimitOverride).toBe(64000);
		expect(internals.requestedModelQuery).toBe("gpt-5");
	});

	it("allows /new to create an untitled session", async () => {
		const createSession = vi.fn(async () => ({ id: "created-session" }));
		const renameSession = vi.fn(async () => {});
		const tui = new KagekoTui({
			client: { createSession, renameSession } as unknown as KagekoClient,
			cwd: "F:/workspace",
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			openInteractivePanel(panel: InteractivePanelName): Promise<void>;
			handlePanelKey(key: { name: string; sequence: string }): Promise<void>;
			switchSession: ReturnType<typeof vi.fn>;
			panelRequestOptions(): object;
			record: ReturnType<typeof vi.fn>;
			closePanel: ReturnType<typeof vi.fn>;
			render: ReturnType<typeof vi.fn>;
			panel: { kind: string; title?: string; value?: string } | undefined;
		};
		internals.switchSession = vi.fn(async () => {});
		internals.panelRequestOptions = () => ({});
		internals.record = vi.fn();
		internals.closePanel = vi.fn();
		internals.render = vi.fn();

		await internals.openInteractivePanel("new");
		expect(internals.panel).toMatchObject({ kind: "form", title: "New session", value: "" });
		await internals.handlePanelKey({ name: "enter", sequence: "\r" });

		expect(createSession).toHaveBeenCalledWith({ cwd: "F:/workspace" }, {});
		expect(renameSession).not.toHaveBeenCalled();
		expect(internals.switchSession).toHaveBeenCalledWith({ id: "created-session" });
	});

	it("Esc returns child forms to their parent and closes top-level forms", async () => {
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			openFormPanel(
				title: string,
				label: string,
				value: string,
				submit: (value: string) => void,
				masked?: boolean,
				parent?: InteractivePanelName,
			): void;
			handlePanelKey(key: { name: string; sequence: string }): Promise<void>;
			openInteractivePanel: ReturnType<typeof vi.fn>;
			closePanel: ReturnType<typeof vi.fn>;
			render: ReturnType<typeof vi.fn>;
		};
		internals.openInteractivePanel = vi.fn(async () => {});
		internals.closePanel = vi.fn();
		internals.render = vi.fn();

		internals.openFormPanel("Add MCP server", "Arguments", "", () => {}, false, "mcp");
		await internals.handlePanelKey({ name: "escape", sequence: "\x1b" });
		expect(internals.openInteractivePanel).toHaveBeenCalledWith("mcp");

		internals.openFormPanel("Rename session", "New title", "", () => {});
		await internals.handlePanelKey({ name: "escape", sequence: "\x1b" });
		expect(internals.closePanel).toHaveBeenCalledOnce();
	});

	it("renders /tools as a searchable menu and opens a selected tool detail view", async () => {
		const listTools = vi.fn(async () => [
			{ name: "read_file", provenance: { kind: "builtin", ownerId: "filesystem" } },
			{ name: "search", provenance: { kind: "mcp", ownerId: "repo-tools" } },
		]);
		const tui = new KagekoTui({
			client: { listTools } as unknown as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			session: { id: string };
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			handlePanelKey(key: { name: string; sequence: string }): Promise<void>;
			panel:
				| {
						kind: string;
						title?: string;
						query?: string;
						items?: readonly { id: string; label: string }[];
						selected?: number;
				  }
				| undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.session = { id: "session-1" };
		internals.render = vi.fn();

		await internals.openCommandPanel("tools", ["read_file"]);

		expect(internals.panel).toMatchObject({ kind: "menu", title: "Tools", query: "read_file" });
		expect(internals.panel?.selected).toBe(0);
		expect(listTools).toHaveBeenCalledWith("session-1", expect.any(Object));
		await internals.handlePanelKey({ name: "enter", sequence: "\r" });
		expect(internals.panel).toMatchObject({ kind: "menu", title: "Tool · read_file" });
		expect(internals.panel?.items?.map((item) => item.label)).toEqual([
			"Name: read_file",
			"Source: builtin",
			"Owner: filesystem",
			"Back to Tools",
		]);
	});

	it("shows missing and empty /tools results inside the TUI menu", async () => {
		const listTools = vi.fn(async () => []);
		const tui = new KagekoTui({
			client: { listTools } as unknown as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			session: { id: string };
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			panel:
				{ kind: string; title?: string; query?: string; items?: readonly { id: string; label: string }[] } | undefined;
			panelActionError: string | undefined;
			render: ReturnType<typeof vi.fn>;
		};
		internals.session = { id: "session-1" };
		internals.render = vi.fn();

		await internals.openCommandPanel("tools", ["missing"]);

		expect(internals.panel).toMatchObject({ kind: "menu", title: "Tools", query: "missing" });
		expect(internals.panelActionError).toContain("No guided action matches");
		await internals.openCommandPanel("tools", []);
		expect(internals.panel).toMatchObject({ kind: "menu", title: "Tools" });
		expect(internals.panel?.items?.map((item) => item.label)).toEqual(["No tools available."]);
	});

	it("confirms replacing an active goal and keeps the objective when replacement is cancelled", async () => {
		const getGoal = vi.fn(async () => ({ status: "active", objective: "Old objective" }));
		const updateGoal = vi.fn(async () => ({}));
		const createGoal = vi.fn(async () => ({}));
		const tui = new KagekoTui({
			client: {} as KagekoClient,
			cwd: process.cwd(),
			input: new VirtualTerminal(),
			output: new VirtualTerminal(),
		});
		const internals = tui as unknown as {
			session: { getGoal: typeof getGoal; updateGoal: typeof updateGoal; createGoal: typeof createGoal };
			openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void>;
			openFormPanel: ReturnType<typeof vi.fn>;
			panelRequestOptions(): object;
			askConfirm: ReturnType<typeof vi.fn>;
			record: ReturnType<typeof vi.fn>;
			render: ReturnType<typeof vi.fn>;
		};
		internals.session = { getGoal, updateGoal, createGoal };
		internals.openFormPanel = vi.fn();
		internals.panelRequestOptions = () => ({});
		internals.askConfirm = vi.fn(async () => false);
		internals.record = vi.fn();
		internals.render = vi.fn();

		await internals.openCommandPanel("goal", ["Ship", "the", "feature"]);
		const submit = internals.openFormPanel.mock.calls[0]?.[3] as (value: string) => Promise<void>;
		await submit("Ship the feature");

		expect(internals.askConfirm).toHaveBeenCalledWith("Replace the active goal with this objective?");
		expect(updateGoal).not.toHaveBeenCalled();
		expect(createGoal).not.toHaveBeenCalled();
		expect(internals.openFormPanel).toHaveBeenLastCalledWith(
			"Session goal",
			"Objective",
			"Ship the feature",
			expect.any(Function),
		);
		internals.askConfirm.mockResolvedValueOnce(true);
		await submit("Ship the feature");
		expect(updateGoal).toHaveBeenCalledWith({ status: "completed" }, {});
		expect(createGoal).toHaveBeenCalledWith({ objective: "Ship the feature" }, {});
	});

	it("searches other workspaces when a typed session id is not in the current workspace", async () => {
		const listSessions = vi.fn(async (filter?: { cwd?: string }) =>
			filter?.cwd
				? [{ sessionId: "local-session", cwd: filter.cwd }]
				: [{ sessionId: "remote-session", cwd: "F:/other" }],
		);
		const tui = new KagekoTui({ client: { listSessions } as unknown as KagekoClient, cwd: "F:/current" });
		const internals = tui as unknown as {
			showSessions(query?: string): Promise<void>;
			sessionScope: "cwd" | "all";
			sessionPicker: { visible(): readonly { sessionId: string }[] } | undefined;
			showModal: ReturnType<typeof vi.fn>;
			ensureSelectedSessionVisible: ReturnType<typeof vi.fn>;
		};
		internals.showModal = vi.fn();
		internals.ensureSelectedSessionVisible = vi.fn();

		await internals.showSessions("remote-session");

		expect(listSessions).toHaveBeenCalledTimes(2);
		expect(internals.sessionScope).toBe("all");
		expect(internals.sessionPicker?.visible().map((session) => session.sessionId)).toEqual(["remote-session"]);
	});

	it.each(slashCommands.filter((command) => command.argumentHint === "(no arguments)").map((command) => command.name))(
		"rejects extra arguments on /%s in the rendered TUI",
		async (commandName) => {
			const tui = new KagekoTui({ client: {} as KagekoClient, cwd: process.cwd() });
			const internals = tui as unknown as {
				runCommand(command: string): Promise<void>;
				record: ReturnType<typeof vi.fn>;
				render: ReturnType<typeof vi.fn>;
				closed: boolean;
			};
			internals.record = vi.fn();
			internals.render = vi.fn();
			internals.closed = false;

			await internals.runCommand(`/${commandName} extra`);

			expect(internals.record).toHaveBeenCalledWith(
				"warning",
				`/${commandName} takes no arguments. Open /help for its guided controls.`,
			);
			expect(internals.closed).toBe(false);
		},
	);
});
