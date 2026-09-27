import { spawn } from "node:child_process";
import { readdir, realpath, stat } from "node:fs/promises";
import path from "node:path";
import {
	type Event,
	type DiscoveredModel,
	type KagekoClient,
	type PendingInteraction,
	type PromptPart,
	type SessionClient,
	type SessionSummary,
	type WorkspaceTrustStatus,
} from "@kageko/node-sdk";
import {
	Renderer,
	OverlayStack,
	PasteBurst,
	resolveTheme,
	SelectableList,
	TerminalController,
	TextEditor,
	Viewport,
	displayWidth,
	graphemeCount,
	renderRowText,
	sanitizeTerminalText,
	sliceGraphemes,
	truncateDisplay,
	wrapDisplay,
	type KeyInput,
	type InteractiveComponent,
	type OverlayStackHandle,
	type RenderRow,
	type TerminalPort,
	row,
	wrapRenderRows,
} from "@kageko/tui-kit";
import { editDraft, resolveEditorCommand } from "./external-editor.js";
import { resolveShellEncoding, ShellCodec } from "./shell-codec.js";
import { appendInputHistory, inputHistoryFile, loadInputHistory } from "./utils/input-history.js";
import { projectSessionEvent } from "./controllers/session-event-projector.js";
import { initialTuiState, reduceTui } from "./tui-state.js";
import type { Overlay, QueuedPrompt, TranscriptRecord, TuiState } from "./types.js";
import { transcriptPhysicalRowCount, transcriptPhysicalSlice } from "./views/transcript-view.js";
import { welcomeLines } from "./views/welcome-view.js";
import { composerLines } from "./views/composer-view.js";
import { footerLines, formatTokenCount } from "./views/status-view.js";
import { activityLines, ACTIVITY_TIPS } from "./views/activity-view.js";
import { queueLines } from "./views/queue-view.js";
import { allocateLayout } from "./views/layout.js";
import { helpDialogLines } from "./dialogs/help-dialog.js";
import { findSlashCommand, slashCommands } from "./commands/registry.js";
import type { CommandContext, InteractivePanelName } from "./commands/types.js";
import { approvalDecision } from "./dialogs/approval-dialog.js";
import {
	filterDiscoveredModels,
	metadataOriginLabel,
	modelMetadataStatus,
	reasoningConfigForModel,
} from "./dialogs/model-picker.js";
import { sessionSearchLabel } from "./dialogs/session-picker.js";
import { isQuestionAnswer } from "./dialogs/question-dialog.js";
import {
	applyCompletion,
	completionFor,
	fileCompletionCandidates,
	moveCompletion,
	shouldQueuePrompt,
	slashCompletionCommands,
} from "./controllers/composer-controller.js";
import { LiveTranscriptController } from "./controllers/live-transcript-controller.js";
import { SessionEventStream } from "./session-event-stream.js";
import {
	SetupController,
	SETUP_PROVIDERS,
	type SetupModelOption,
	type SetupResult,
} from "./controllers/setup-controller.js";
import { buildConfigPatch } from "../cli/config-patch.js";
import {
	formatSettingValue,
	parseSettingInput,
	readSettingValue,
	SETTINGS_NEW_SESSION_NOTE,
	SETTINGS_SECTIONS,
	settingsSectionSummary,
	type SettingField,
	type SettingsSection,
} from "./settings-catalog.js";

type AgentTarget = {
	readonly id: string;
	readonly label: string;
	readonly detail: string;
	readonly kind: "coordinator" | "learner" | "subagent";
	readonly profileId?: string;
	readonly builtin?: boolean;
	readonly legacyExecutor?: boolean;
};
type PanelMenuItem = { readonly id: string; readonly label: string; readonly detail?: string };
// Capability ids are user-controlled and may legitimately contain underscores.
// Keep internal menu actions outside the filesystem-valid identifier space.
const PANEL_ACTION_RELOAD = "\u0000kageko:reload";
const PANEL_ACTION_INSTALL = "\u0000kageko:install";
type LearningPendingEntry = {
	readonly id?: string;
	readonly event?: { readonly id?: string; readonly source?: string; readonly timestamp?: number };
	readonly kind?: string;
	readonly decision?: { readonly target?: string };
	readonly output?: {
		readonly kind?: string;
		readonly name?: string;
		readonly description?: string;
		readonly command?: string;
		readonly args?: readonly unknown[];
		readonly parameters?: unknown;
	};
};
type OAuthPromptState = {
	message: string;
	placeholder?: string;
	value: string;
	options?: readonly { readonly id: string; readonly label: string; readonly description?: string }[];
	selectedIndex: number;
	resolve: (value: string | undefined) => void;
};
type ModelPanelState = {
	kind: "model";
	step: "role" | "route" | "model" | "confirm";
	targets: readonly AgentTarget[];
	targetIndex: number;
	routes: readonly { provider: string; label: string; authMode: "api" | "oauth"; ready: boolean; baseUrl?: string }[];
	routeIndex: number;
	models: readonly DiscoveredModel[];
	modelQuery: string;
	contextLimitOverride?: number;
	modelIndex: number;
	reasoningIndex: number;
	confirmIndex: number;
	busy: boolean;
	busyLabel?: string;
	error?: string;
};
type GraphField =
	| "description"
	| "whenToUse"
	| "route"
	| "baseUrl"
	| "contextLength"
	| "maxContextSize"
	| "maxOutputTokens"
	| "maxSteps"
	| "timeoutMs"
	| "runTimeoutMs"
	| "maxQueuedRuns"
	| "systemPrompt"
	| "permissionProfile"
	| "interactionMode"
	| "tools"
	| "reset"
	| "remove";
type GraphEditableField = Exclude<
	GraphField,
	"route" | "reset" | "remove" | "permissionProfile" | "interactionMode" | "tools"
>;
type GraphPanelState = {
	kind: "graph";
	target: AgentTarget;
	fieldIndex: number;
	fields: readonly GraphField[];
	config: Record<string, Record<string, unknown>>;
	editing?: { field: GraphEditableField; value: string; cursorIndex: number };
	busy: boolean;
	busyLabel?: string;
	error?: string;
};
type MenuPanelState = {
	kind: "menu";
	title: string;
	items: readonly PanelMenuItem[];
	query: string;
	selected: number;
	parent?: InteractivePanelName;
};
type FormPanelState = {
	kind: "form";
	title: string;
	label: string;
	value: string;
	cursorIndex: number;
	masked?: boolean;
	placeholder?: string;
	hint?: string;
	parent?: InteractivePanelName;
};
type FormPanelOptions = {
	readonly placeholder?: string;
	readonly hint?: string;
};
type PanelState = ModelPanelState | GraphPanelState | MenuPanelState | FormPanelState;
/** Identifies one panel load/operation; `panel` pins the surface when a guard
 * belongs to a specific panel instance (model/graph returns), not just a load. */
type PanelOperationGuard = {
	readonly operationId: number;
	readonly signal?: AbortSignal;
	readonly panel?: PanelState;
};

export interface KagekoTuiOptions {
	readonly client: KagekoClient;
	readonly cwd: string;
	/** Optional terminal ports for host embeddings and black-box terminal tests. */
	readonly input?: TerminalPort;
	readonly output?: TerminalPort;
	readonly sessionId?: string;
	readonly resumePicker?: boolean;
	readonly model?: string;
	readonly setup?: boolean;
	/** Host-owned browser launch. Tests and embedded hosts may replace it. */
	readonly openExternal?: (url: string) => void;
	readonly subscribeDiagnostics?: (
		listener: (diagnostic: { readonly code: string; readonly message: string; readonly error?: unknown }) => void,
	) => () => void;
}

/** Thin lifecycle coordinator: SDK calls remain here; state, projection, and views are pure modules. */
export class KagekoTui {
	private terminal: TerminalController;
	private renderer: Renderer;
	private state: TuiState = initialTuiState();
	private readonly viewport = new Viewport();
	private readonly modalViewport = new Viewport();
	private editor = new TextEditor();
	private readonly questionEditor = new TextEditor();
	private readonly liveTranscript = new LiveTranscriptController({
		dispatch: (action) => this.dispatch(action),
		addRecord: (record) => this.addRecord(record),
	});
	private session: SessionClient | undefined;
	/** Optimistic credential state for changes made during this TUI session. */
	private readonly credentialReadiness = new Map<string, { api: boolean; oauth: boolean }>();
	private sessionPicker: SelectableList<SessionSummary> | undefined;
	private sessionScope: "cwd" | "all" = "cwd";
	private sessionReloadBusy = false;
	private activityLines: string[] = [];
	private pendingInteractions: readonly PendingInteraction[] = [];
	private readonly history: string[] = [];
	private readonly historyFile: string;
	private historyWriteTask: Promise<void> = Promise.resolve();
	private historyIndex = -1;
	private historyDraft: { readonly text: string; readonly cursorIndex: number } | undefined;
	private interactionChoice = 2;
	private approvalFeedback = "";
	private approvalEditing = false;
	private approvalPreview = false;
	private approvalOutputExpanded = false;
	private collapsed = new Set<string>();
	private completion: { kind: "/" | "@"; values: readonly string[]; selected: number; start: number } | undefined;
	private completionRequestId = 0;
	private completionDebounceTimer: ReturnType<typeof setTimeout> | undefined;
	private completionAbort: AbortController | undefined;
	private closed = false;
	private disposeActivities: (() => void) | undefined;
	private pasteCounter = 0;
	private readonly pastes = new Map<number, string>();
	private readonly pasteBurst = new PasteBurst();
	private confirmChoice = 0;
	private pendingConfirm: { message: string; resolve: (value: boolean) => void } | undefined;
	private shellProcess: ReturnType<typeof spawn> | undefined;
	private shellLines: string[] = [];
	private shellCodec = new ShellCodec("utf8");
	private runtimeModel: {
		provider?: string;
		modelName?: string;
		contextLength?: number;
		contextLimit?: number;
		contextUsed?: number;
		capabilities?: readonly string[];
		authMode?: string;
		contextLengthSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		contextLimitSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
		contextUsedSource?: "authoritative" | "catalog" | "configured" | "estimated" | "unknown";
	} = {};
	private runtimePolicies: {
		permissionProfile?: "manual" | "workspace" | "unrestricted";
		interactionMode?: "interactive" | "unattended";
	} = {};
	private themeName: "dark" | "light" | "system" = "system";
	private startupTrust:
		{ status: WorkspaceTrustStatus; choice: number; error?: string; resolve: (granted: boolean) => void } | undefined;
	private trustAbort: AbortController | undefined;
	private setupWizard:
		| {
				controller: SetupController;
				/** Resolves true when a credential/model route was actually established, false on cancellation. */
				resolve: (completed: boolean) => void;
				busy: boolean;
				credentialReady: boolean;
				credentialOnly?: boolean;
				oauthAbort?: AbortController;
				oauthPrompt?: OAuthPromptState;
				oauthUrl?: string;
				oauthCode?: string;
				oauthInstructions?: string;
		  }
		| undefined;
	private panel: PanelState | undefined;
	private panelReturn: InteractivePanelName | undefined;
	/** Sub-panel return override for panels that reopen a computed view (e.g. a settings section) instead of a named panel. */
	private panelReturnAction: (() => Promise<void> | void) | undefined;
	private panelActions = new Map<string, () => Promise<void> | void>();
	private panelSubmit: ((value: string) => Promise<void> | void) | undefined;
	private panelOperationId = 0;
	private panelAbort: AbortController | undefined;
	private panelActionError: string | undefined;
	/** Remaining typed slash arguments used to seed guided forms. */
	private panelCommandPrefills: string[] = [];
	private requestedModelQuery: string | undefined;
	private learnRefreshTimer: ReturnType<typeof setInterval> | undefined;
	private learnRefreshBusy = false;
	private learningPendingCount: number | undefined;
	private learningPendingBusy = false;
	private readonly recentLearningDiagnostics = new Map<string, number>();
	private immediateInputDepth = 0;
	private immediateRenderPending = false;
	private inputDispatchDepth = 0;
	private inputRenderPending = false;
	private immediateRenderTimer: ReturnType<typeof setTimeout> | undefined;
	private renderRateLimitActive = false;
	private renderTimer: ReturnType<typeof setTimeout> | undefined;
	private renderPending = false;
	private lastRenderAt = 0;
	/** Zero-based terminal row where the modal frame starts in the last frame. */
	/** Zero-based row where the composer starts in the last rendered frame. */
	private lastComposerTop = -1;
	/** Normal TUI overlays use a Kimi-style focus/capture stack. Setup has its own
	 * focused owner because it also hosts the provider login lifecycle. */
	private readonly normalOverlayStack = new OverlayStack();
	private readonly normalOverlayComponents = new Map<string, InteractiveComponent>();
	private readonly normalOverlayHandles = new Map<string, OverlayStackHandle>();
	private eventTask: Promise<void> | undefined;
	private eventGeneration = 0;
	private releasingQueuedPrompt = false;
	private tickCount = 0;
	private leased = false;
	private readonly eventStream: SessionEventStream;
	private disposeDiagnostics: (() => void) | undefined;
	private setupOperationId = 0;
	private effectQueue: Promise<void> = Promise.resolve();
	private effectQueueBusy = 0;
	/** Commit guards for queue-free input: keys dispatch synchronously to the
	 * focused overlay (kimi/pi-tui model), so re-entrant commits are guarded
	 * inside the handlers rather than by parking keys in a queue. */
	private sessionActionBusy = false;
	private interactionBusy = false;
	private trustBusy = false;
	private panelActionBusy = false;
	private resolveClosed!: () => void;
	private readonly closedPromise = new Promise<void>((resolve) => {
		this.resolveClosed = resolve;
	});
	constructor(private readonly options: KagekoTuiOptions) {
		const input = options.input ?? (process.stdin as unknown as TerminalPort);
		const output = options.output ?? (process.stdout as unknown as TerminalPort);
		this.terminal = new TerminalController(input, output);
		this.renderer = new Renderer(output, () => this.terminal.size());
		this.historyFile = inputHistoryFile(options.cwd);
		this.disposeDiagnostics = options.subscribeDiagnostics?.((diagnostic) => this.handleDiagnostic(diagnostic));
		this.eventStream = new SessionEventStream({
			isActive: (session, generation) =>
				!this.closed && session === this.session && generation === this.eventGeneration,
			onEvent: (event) => this.handleEvent(event),
			onReconnect: (resumeFromSequence) => {
				this.dispatch({ type: "connection", value: "reconnecting" });
				this.record("warning", `Live stream caught up from event ${resumeFromSequence}.`);
				this.render();
			},
			onError: (error) => {
				this.dispatch({ type: "connection", value: "failed" });
				this.finishStreaming();
				this.record("error", `Event stream stopped: ${messageOf(error)}`);
				this.render();
			},
		});
	}

	async start(): Promise<void> {
		try {
			this.terminal.on("input", (keys) => {
				this.inputDispatchDepth += 1;
				try {
					for (const key of keys) {
						// Match Kimi's terminal ownership: the TUI never captures pointer input.
						if (key.name === "mouse" || key.name === "wheelup" || key.name === "wheeldown") continue;
						// Kitty reports key-up separately. It is useful to components that
						// explicitly opt into it, but Kageko's command/editor layer is
						// press/repeat based and must never turn a release into a second action.
						if (key.eventType === "release") continue;
						// kimi/pi-tui ownership model: every key dispatches synchronously
						// to the focused component; async tails detach and re-entrant
						// commits are guarded inside the handlers. No key queues behind
						// another key, so a held key cannot build a backlog and a fresh
						// key (Escape, Ctrl+C, arrows) always takes effect immediately.
						if (this.setupWizard) {
							this.dispatchSetupInput(key);
							continue;
						}
						if (this.normalOverlayStack.hasVisible()) {
							this.dispatchFocusedOverlayInput(key);
							continue;
						}
						// Single-lane Kimi model: handleKey runs synchronously, so composer
						// edits (text, cursor, history, paste) apply in arrival order and
						// never wait behind the effect queue; only side effects (submit,
						// slash commands, shell, external editor) re-enter the queue from
						// inside handleKey. One escape hatch stays off that lane: Ctrl+C
						// while a turn or queued effect is running, where it is turn
						// cancellation and must stay responsive.
						if (key.name === "ctrl-c" && (this.state.turnLive || this.state.submitting || this.effectQueueBusy > 0)) {
							this.dispatchImmediateKey(key);
							continue;
						}
						try {
							this.handleKey(key);
						} catch (error) {
							this.record("error", `Input failed: ${messageOf(error)}`);
							this.render();
						}
					}
				} finally {
					this.inputDispatchDepth -= 1;
					if (this.inputDispatchDepth === 0 && this.inputRenderPending) {
						this.inputRenderPending = false;
						this.render();
					}
				}
			});
			this.terminal.on("resize", () => this.render());
			this.terminal.on("focus", () => this.render());
			const shouldRunStartupGates = Boolean(
				this.options.setup || this.options.client.inspectWorkspaceTrust || this.options.client.getConfiguration,
			);
			if (shouldRunStartupGates) {
				this.terminal.start();
				this.renderRateLimitActive = true;
				if (this.closed) {
					await this.close();
					return;
				}
				if (!(await this.runStartupGates())) return;
			}
			if (this.closed) return;
			const session = this.options.sessionId
				? this.options.client.session(this.options.sessionId)
				: this.options.resumePicker
					? undefined
					: await this.options.client.createSession({ cwd: this.options.cwd });
			if (this.closed) return;
			this.session = session;
			this.dispatch({ type: "session", value: session?.id });
			await this.loadHistory();
			this.disposeActivities = this.options.client.watchActivities((event) => this.handleActivityEvent(event));
			if (this.closed) {
				this.disposeActivities?.();
				return;
			}
			if (!shouldRunStartupGates) {
				this.terminal.start();
				this.renderRateLimitActive = true;
				if (this.closed) {
					await this.close();
					return;
				}
			}
			// Empty sessions render the dedicated welcome surface; do not pollute the transcript with startup metadata.
			if (session) this.eventTask = this.consumeEvents(session, this.eventGeneration);
			await this.refreshPendingInteractions();
			await this.refreshRuntimeModel();
			if (this.options.resumePicker) await this.showSessions();
			this.render();
		} catch (error) {
			await this.close();
			throw error;
		}
	}
	private dispatchSetupInput(key: KeyInput): void {
		void this.handleSetupKey(key).catch((error) => {
			this.record("error", `Setup failed: ${messageOf(error)}`);
			this.render();
		});
	}
	/** kimi-style direct dispatch: the handler's synchronous prefix applies
	 * immediately and its async tail detaches. There is deliberately no key queue
	 * here — queuing keys behind in-flight I/O made held keys replay a stale
	 * backlog after release and blocked fresh keys from interrupting. Re-entrant
	 * commits are guarded inside the individual handlers (sessionActionBusy,
	 * interactionBusy, trustBusy, panelActionBusy, panel.busy, wizard.busy). */
	private dispatchFocusedOverlayInput(key: KeyInput): void {
		// A key arriving during close() must not fire into a torn-down overlay stack.
		if (this.closed) return;
		void this.deliverOverlayKey(key).catch((error) => {
			this.record("error", `Overlay input failed: ${messageOf(error)}`);
			this.render();
		});
	}
	/** Focused-overlay delivery with default cancel semantics: when the overlay
	 * does not handle Ctrl+C (handleInput returns false), dismiss the top overlay. */
	private async deliverOverlayKey(key: KeyInput): Promise<void> {
		const handled = await this.normalOverlayStack.handleInput(key);
		if (!handled && key.name === "ctrl-c") {
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
		}
	}
	async close(): Promise<void> {
		if (this.closed) return;
		this.closed = true;
		if (this.immediateRenderTimer) clearTimeout(this.immediateRenderTimer);
		this.immediateRenderTimer = undefined;
		this.immediateInputDepth = 0;
		this.immediateRenderPending = false;
		if (this.renderTimer) clearTimeout(this.renderTimer);
		this.renderTimer = undefined;
		this.renderPending = false;
		this.panelOperationId += 1;
		this.stopLearnRefresh();
		this.panelAbort?.abort(new Error("TUI closed while a panel operation was pending."));
		this.panelAbort = undefined;
		this.trustAbort?.abort(new Error("TUI closed while workspace trust was pending."));
		this.trustAbort = undefined;
		this.setupOperationId += 1;
		this.cancelCompletionRequest();
		this.eventGeneration++;
		this.disposeActivities?.();
		this.disposeDiagnostics?.();
		if (this.pendingConfirm) {
			const pending = this.pendingConfirm;
			this.pendingConfirm = undefined;
			pending.resolve(false);
		}
		if (this.startupTrust) {
			const pending = this.startupTrust;
			this.startupTrust = undefined;
			pending.resolve(false);
		}
		if (this.setupWizard) {
			const wizard = this.setupWizard;
			this.setupWizard = undefined;
			wizard.oauthPrompt?.resolve(undefined);
			wizard.oauthAbort?.abort(new Error("TUI closed while OAuth login was pending."));
			wizard.resolve(false);
		}
		await this.closeEmbeddedShell();
		// A prompt may be submitted immediately before Ctrl+D. Keep shutdown from
		// racing the append-only history write and losing that final entry.
		await this.historyWriteTask;
		await this.terminal.drainInput();
		this.renderer.stop();
		this.terminal.stop();
		try {
			await this.eventStream.stop();
			await this.eventTask?.catch(() => {});
		} finally {
			this.resolveClosed();
		}
	}
	wait(): Promise<void> {
		return this.closedPromise;
	}
	private dispatch(action: Parameters<typeof reduceTui>[1]): void {
		// A normal overlay owns input through the stack. When a modal closes,
		// remove only the focused top entry and let the stack restore its parent;
		// setup remains outside this path and keeps its Hermes-style wizard owner.
		if (action.type === "overlay" && action.value === "none") {
			this.normalOverlayStack.hide();
			const restored = this.normalOverlayStack.topId();
			if (restored) action = { ...action, value: restored as Overlay };
		}
		this.state = reduceTui(this.state, action);
	}
	private handleDiagnostic(diagnostic: {
		readonly code: string;
		readonly message: string;
		readonly error?: unknown;
	}): void {
		if (this.setupWizard && this.state.overlay === "setup" && diagnostic.code === "core.diagnostic") {
			this.setupWizard.controller.status = diagnostic.message;
			this.render();
			return;
		}
		if (diagnostic.code === "learning") {
			// listPending re-reports an unreadable queue on every read; reacting to
			// a repeat with another queue read would self-sustain a diagnostic loop.
			const now = Date.now();
			const lastSeen = this.recentLearningDiagnostics.get(diagnostic.message);
			const repeat = lastSeen !== undefined && now - lastSeen < LEARNING_DIAGNOSTIC_DEDUPE_MS;
			this.recentLearningDiagnostics.set(diagnostic.message, now);
			if (this.recentLearningDiagnostics.size > 32)
				for (const [message, at] of this.recentLearningDiagnostics)
					if (now - at >= LEARNING_DIAGNOSTIC_DEDUPE_MS) this.recentLearningDiagnostics.delete(message);
			if (repeat) return;
			// Learning diagnostics carry proposal notices and pending-queue
			// problems. Surface them through the transcript (never raw stderr in
			// fullscreen mode); only a proposal notice triggers a queue refresh.
			this.record(diagnostic.error ? "warning" : "status", diagnostic.message);
			this.render();
			if (diagnostic.message.startsWith("New learning proposal pending:")) {
				void this.refreshLearningPending();
				void this.refreshLearnPanel();
			}
		}
	}
	private openOAuthUrl(url: string): void {
		// PTY/CI owners can exercise the OAuth state machine without granting a
		// test process permission to launch the user's default browser. The URL
		// remains rendered in the wizard, so this only suppresses the side effect.
		if (process.env["KAGEKO_DISABLE_EXTERNAL_BROWSER"] === "1") return;
		if (this.options.openExternal) {
			this.options.openExternal(url);
			return;
		}
		try {
			const target = new URL(url);
			if (target.protocol !== "https:" && target.protocol !== "http:") return;
			const command = process.platform === "win32" ? "cmd" : process.platform === "darwin" ? "open" : "xdg-open";
			const args = process.platform === "win32" ? ["/c", "start", "", target.toString()] : [target.toString()];
			const child = spawn(command, args, { detached: true, stdio: "ignore" });
			child.unref();
		} catch {
			// The verified URL remains visible in the setup modal for manual opening.
		}
	}
	private enqueue(operation: () => Promise<void>): void {
		const run = async () => {
			this.effectQueueBusy += 1;
			try {
				await operation();
			} finally {
				this.effectQueueBusy = Math.max(0, this.effectQueueBusy - 1);
			}
		};
		this.effectQueue = this.effectQueue.then(run, run).catch((error) => {
			this.record("error", `Operation failed: ${messageOf(error)}`);
			this.render();
		});
	}
	private dispatchImmediateKey(key: KeyInput, operation: () => Promise<void> = async () => this.handleKey(key)): void {
		this.immediateInputDepth += 1;
		void operation()
			.catch((error) => {
				this.record("error", `Input failed: ${messageOf(error)}`);
				this.immediateRenderPending = true;
			})
			.finally(() => {
				this.immediateInputDepth = Math.max(0, this.immediateInputDepth - 1);
				if (this.immediateInputDepth === 0 && this.immediateRenderPending) this.scheduleImmediateRender();
			});
	}
	/** Async modal handlers stay off the effect queue; failures surface like the queue's catch. */
	private detachInput(operation: () => Promise<void>): void {
		void operation().catch((error) => {
			this.record("error", `Input failed: ${messageOf(error)}`);
			this.render();
		});
	}
	private scheduleImmediateRender(): void {
		if (this.immediateRenderTimer || this.closed) return;
		this.immediateRenderTimer = setTimeout(() => {
			this.immediateRenderTimer = undefined;
			if (this.immediateInputDepth > 0) {
				this.scheduleImmediateRender();
				return;
			}
			if (!this.immediateRenderPending) return;
			this.immediateRenderPending = false;
			this.render();
		}, 16);
		this.immediateRenderTimer.unref?.();
	}

	private async consumeEvents(session: SessionClient, generation = this.eventGeneration): Promise<void> {
		return this.eventStream.start(session, generation);
	}
	private handleEvent(event: Event): void {
		this.dispatch({ type: "connection", value: "ready" });
		const projection = projectSessionEvent(event);
		if (event.type === "usage.updated") {
			this.runtimeModel.contextUsed =
				typeof event.data.promptTokens === "number" ? event.data.promptTokens : this.runtimeModel.contextUsed;
			this.runtimeModel.contextUsedSource = "authoritative";
		}
		this.liveTranscript.apply(event, projection);
		for (const item of projection.activities ?? []) this.dispatch({ type: "activity", value: item });
		if (projection.turnLive !== undefined) this.dispatch({ type: "turn", value: projection.turnLive });
		if (event.type === "turn.end" || event.type === "turn.failed" || event.type === "turn.interrupted") {
			void this.releaseQueuedPrompt();
			void this.refreshRuntimeModel();
			// No learning-badge refresh here: this handler also replays journal
			// history at startup, and listing pending proposals composes the
			// session runtime — far too heavy for replay. The badge refreshes
			// from proposal diagnostics and /learn panel activity instead.
		}
		this.render();
	}
	private finishStreaming(): void {
		this.liveTranscript.finish();
	}
	private addRecord(record: TranscriptRecord): void {
		this.dispatch({ type: "record", value: record });
		// A zero offset follows the tail naturally. A non-zero offset belongs to
		// the reader and must survive newly arriving records.
		if (this.viewport.scrollOffset === 0) this.viewport.reset();
	}
	private record(kind: TranscriptRecord["kind"], text: string): void {
		this.addRecord({
			id: `local-${Date.now()}-${this.state.transcript.length}`,
			kind,
			text: sanitizeTerminalText(text),
		});
	}
	private handleActivityEvent(event: Event): void {
		if (["subagent.started", "process.started", "turn.failed", "session.status.changed"].includes(event.type))
			this.enqueue(() => this.refreshPendingInteractions());
	}
	private async refreshPendingInteractions(): Promise<void> {
		try {
			const previousId = this.pendingInteractions[0]?.request.id;
			// Pending requests are scoped to a runtime session. Querying the global
			// mailbox after a session switch can resurrect an approval belonging to
			// the previous session.
			this.pendingInteractions = this.session ? await this.options.client.listPendingInteractions(this.session.id) : [];
			const pending = this.pendingInteractions[0];
			// Approvals and questions are part of the active turn, not a mailbox the
			// user should have to discover through a slash command. Reopen only for a
			// newly observed request and never replace a surface the user is using.
			if (pending && pending.request.id !== previousId && this.state.overlay === "none")
				this.showModal(pending.kind === "approval" ? "approval" : "question");
		} catch {
			return;
		}
		this.render();
	}
	private async refreshRuntimeModel(): Promise<void> {
		try {
			const config = await this.options.client.getConfiguration();
			const model = config.model as Record<string, unknown>;
			const permission = isObjectValue(config.permission) ? config.permission : {};
			const interaction = isObjectValue(config.interaction) ? config.interaction : {};
			this.runtimePolicies = {
				permissionProfile: isPermissionProfile(permission["defaultProfile"]) ? permission["defaultProfile"] : undefined,
				interactionMode: isInteractionMode(interaction["defaultMode"]) ? interaction["defaultMode"] : undefined,
			};
			const snapshot = await this.session?.snapshot().catch(() => undefined);
			const provider = typeof model["provider"] === "string" ? model["provider"] : undefined;
			const baseUrl = typeof model["baseUrl"] === "string" ? model["baseUrl"] : undefined;
			const authMode =
				snapshot?.authMode ??
				(typeof model["authMode"] === "string" ? (model["authMode"] as "api" | "oauth") : undefined);
			let discovered: readonly DiscoveredModel[] = [];
			if (provider && authMode && typeof this.options.client.discoverModels === "function") {
				try {
					discovered = await this.options.client.discoverModels(provider, {
						authMode,
						baseUrl,
						includeProvenance: true,
					});
				} catch (error) {
					this.runtimeModel = {
						provider,
						modelName: typeof model["modelName"] === "string" ? model["modelName"] : this.options.model,
						authMode,
					};
					this.record("error", `Live model discovery failed for ${provider}: ${messageOf(error)}`);
					return;
				}
			}
			const configuredModelName = String(model["modelName"] ?? this.options.model ?? "");
			const selected = discovered.find((entry) => modelIdsMatch(provider ?? "", entry.id, configuredModelName));
			const configuredCapabilities = Array.isArray(model["capabilities"])
				? model["capabilities"].filter((value): value is string => typeof value === "string")
				: undefined;
			this.runtimeModel = {
				provider,
				modelName: typeof model["modelName"] === "string" ? model["modelName"] : this.options.model,
				contextLength:
					typeof selected?.contextLength === "number"
						? selected.contextLength
						: typeof snapshot?.contextLength === "number"
							? snapshot.contextLength
							: typeof model["contextLength"] === "number"
								? model["contextLength"]
								: undefined,
				contextLimit:
					typeof selected?.contextLimit === "number"
						? selected.contextLimit
						: typeof snapshot?.contextLimit === "number"
							? snapshot.contextLimit
							: typeof model["maxContextSize"] === "number"
								? model["maxContextSize"]
								: undefined,
				contextUsed: typeof snapshot?.contextUsed === "number" ? snapshot.contextUsed : this.runtimeModel.contextUsed,
				capabilities: selected?.capabilities ?? snapshot?.model?.capabilities ?? configuredCapabilities,
				authMode,
				contextLengthSource:
					snapshot?.model?.provenance?.contextLength ??
					selected?.provenance?.contextLength ??
					(typeof model["contextLength"] === "number" ? "configured" : "unknown"),
				contextLimitSource:
					selected?.provenance?.maxContextSize ??
					snapshot?.contextLimitSource ??
					snapshot?.model?.provenance?.maxContextSize ??
					(typeof model["maxContextSize"] === "number" ? "configured" : "unknown"),
				contextUsedSource:
					snapshot?.contextUsedSource ??
					(typeof snapshot?.contextUsed === "number"
						? "authoritative"
						: (this.runtimeModel.contextUsedSource ?? "unknown")),
			};
		} catch {
			/* render the shell even when configuration is temporarily unavailable */
		}
	}

	/** Startup gates run before any session exists; false means the user chose to exit. */
	private async runStartupGates(): Promise<boolean> {
		const status = await (this.options.client.inspectWorkspaceTrust?.() ?? Promise.resolve(undefined)).catch(
			() => undefined,
		);
		if (status && status.hasSecurityConfiguration && !status.trusted) {
			const granted = await new Promise<boolean>((resolve) => {
				this.startupTrust = { status, choice: 0, resolve };
				this.showModal("trust");
				this.render();
			});
			this.startupTrust = undefined;
			if (!granted || this.closed) {
				await this.close();
				return false;
			}
		}
		const config = await (this.options.client.getConfiguration?.() ?? Promise.resolve(undefined)).catch(
			() => undefined,
		);
		const provider = typeof config?.model?.["provider"] === "string" ? config.model["provider"] : undefined;
		const authMode =
			config?.model?.["authMode"] === "api" || config?.model?.["authMode"] === "oauth"
				? config.model["authMode"]
				: undefined;
		const currentRouteReady =
			// The generic KAGEKO_API_KEY is intentionally absent here: it only
			// authenticates the custom provider, in which case the config loader
			// already surfaces it as model.apiKey.
			Boolean(config?.model?.["apiKey"]) ||
			(provider
				? await (this.options.client.hasCredential?.(provider, authMode) ?? Promise.resolve(false)).catch(() => false)
				: false);
		const anyRouteReady = currentRouteReady || (await this.hasAnyConfiguredCredential());
		if (this.options.setup || (config !== undefined && !anyRouteReady)) await this.runSetupWizard();
		else if (config !== undefined && provider && !currentRouteReady)
			this.record(
				"warning",
				`Current route ${provider} is unavailable; existing provider credentials remain usable. Use /model or /setup to switch routes.`,
			);
		return !this.closed;
	}

	private async hasAnyConfiguredCredential(): Promise<boolean> {
		// KAGEKO_API_KEY is custom-provider-only; a custom route with that key is
		// already reported ready by the caller through config.model.apiKey.
		if (hasUsableEnvSecret(process.env["OPENAI_API_KEY"]) || hasUsableEnvSecret(process.env["ANTHROPIC_API_KEY"]))
			return true;
		if (typeof this.options.client.hasCredential !== "function") return false;
		const routes = SETUP_PROVIDERS.flatMap((entry) => [
			{ provider: entry.id, authMode: entry.authMode },
			...(entry.authMode === "api" ? [{ provider: entry.id, authMode: "oauth" as const }] : []),
		]);
		const readiness = await Promise.all(
			routes.map((route) => this.options.client.hasCredential(route.provider, route.authMode).catch(() => false)),
		);
		return readiness.some(Boolean);
	}

	private runSetupWizard(providerId?: string, authMode?: "api" | "oauth", credentialOnly = true): Promise<boolean> {
		return new Promise((resolve) => {
			const controller = new SetupController();
			if (providerId && authMode) controller.selectRoute(providerId, authMode);
			this.setupWizard = { controller, resolve, busy: false, credentialReady: false, credentialOnly };
			this.showModal("setup");
			this.render();
			if (
				providerId && credentialOnly &&
				(controller.provider.authMode === "oauth" || controller.provider.credentialMode === "none")
			) {
				controller.acceptProvider();
				void this.prepareSetupRoute();
			}
		});
	}
	private normalOverlayComponent(id: string): InteractiveComponent {
		const existing = this.normalOverlayComponents.get(id);
		if (existing) return existing;
		const component: InteractiveComponent = {
			focused: false,
			handleInput: (key) => this.handleNormalOverlayInput(id, key),
		};
		this.normalOverlayComponents.set(id, component);
		return component;
	}
	private async handleNormalOverlayInput(id: string, key: KeyInput): Promise<boolean> {
		if (id === "shell") {
			await this.handleShellKey(key);
			return true;
		}
		// KimiCode's focused overlay owns cancellation. Do this before dispatching
		// to the individual panel so Ctrl+C cannot disappear in a component that
		// only understands navigation keys.
		if (key.name === "ctrl-c") {
			if (id === "approval") {
				await this.answerInteractionGuarded("deny");
				return true;
			}
			if (id === "question") {
				this.questionEditor.clear();
				this.dispatch({ type: "overlay", value: "none" });
				this.render();
				return true;
			}
			if (id === "confirm") {
				this.handleConfirmKey(key);
				return true;
			}
			if (id === "sessions") this.sessionPicker = undefined;
			if (id === "trust" && this.startupTrust) {
				const pending = this.startupTrust;
				this.startupTrust = undefined;
				this.dispatch({ type: "overlay", value: "none" });
				pending.resolve(false);
				return true;
			}
			if (id === "panel") {
				this.closePanel();
				return true;
			}
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return true;
		}
		if (id === "panel") {
			await this.handlePanelKey(key);
			return true;
		}
		if (id === "trust") {
			await this.handleTrustKey(key);
			return true;
		}
		if (id === "sessions") {
			await this.handleSessionKey(key);
			return true;
		}
		if (id === "approval" || id === "question") {
			await this.handleInteractionKey(key);
			return true;
		}
		if (id === "confirm") {
			this.handleConfirmKey(key);
			return true;
		}
		if (id === "help" || id === "details" || id === "activities") {
			if (key.name === "escape") {
				this.dispatch({ type: "overlay", value: "none" });
				this.render();
				return true;
			}
			if (key.name === "pageup" || key.name === "pagedown") {
				this.scrollModal((key.name === "pageup" ? -1 : 1) * 8);
			}
			this.render();
			return true;
		}
		return false;
	}
	private handleKey(key: KeyInput): void {
		const isPlainPrintable = Boolean(key.text && !key.text.includes("\n") && !key.sequence.startsWith("\x1b[200~"));
		if (!isPlainPrintable && key.name !== "enter" && key.name !== "newline") this.pasteBurst.reset();
		if (isPlainPrintable && key.text && graphemeCount(key.text) === 1) this.pasteBurst.onPlainChar(Date.now());
		if (key.name === "f2") {
			this.enqueue(async () => {
				if (this.state.overlay === "shell") await this.closeEmbeddedShell();
				else if (this.state.overlay === "none") await this.openShell();
			});
			return;
		}
		if (key.name === "ctrl-c") {
			if (this.state.turnLive || this.state.submitting) {
				// Cancellation must stay responsive even while the effect queue is busy.
				void Promise.resolve(this.session?.cancel()).then(
					() => {
						this.record("warning", "Cancellation requested.");
						this.render();
					},
					(error) => {
						this.record("error", `Cancellation failed: ${messageOf(error)}`);
						this.render();
					},
				);
				return;
			}
			if (this.state.overlay !== "none") {
				if (this.state.overlay === "sessions") this.sessionPicker = undefined;
				if (this.pendingConfirm) {
					const pending = this.pendingConfirm;
					this.pendingConfirm = undefined;
					pending.resolve(false);
				}
				if (this.startupTrust) {
					const pending = this.startupTrust;
					this.startupTrust = undefined;
					pending.resolve(false);
				}
				if (this.setupWizard) {
					const wizard = this.setupWizard;
					this.setupWizard = undefined;
					wizard.resolve(false);
				}
				if (this.state.overlay === "question") this.questionEditor.clear();
				if (this.normalOverlayStack.hasVisible()) this.normalOverlayStack.hide();
				this.dispatch({ type: "overlay", value: "none" });
				this.render();
				return;
			}
			if (this.editor.text) {
				this.clearEditor();
				this.render();
				return;
			}
			void this.close().catch((error) => {
				this.record("error", `Shutdown failed: ${messageOf(error)}`);
			});
			return;
		}
		if (this.normalOverlayStack.hasVisible()) {
			void this.normalOverlayStack.handleInput(key).catch((error) => {
				this.record("error", `Input failed: ${messageOf(error)}`);
				this.render();
			});
			return;
		}
		if (key.name === "ctrl-o" && this.state.overlay === "none") {
			const target = [...this.state.transcript]
				.reverse()
				.find((record) => record.kind === "tool" || record.kind === "tool-result" || record.kind === "thinking");
			if (target) {
				const expanded = this.collapsed.has(target.id);
				if (expanded) this.collapsed.delete(target.id);
				else this.collapsed.add(target.id);
				this.dispatch({ type: "replace", id: target.id, patch: { expanded: !expanded } });
			}
			this.render();
			return;
		}
		if (key.name === "ctrl-t" && this.state.overlay === "none") {
			this.enqueue(() => this.openInteractivePanel("activity"));
			return;
		}
		if (key.name === "ctrl-g" && this.state.overlay === "none") {
			this.enqueue(() => this.openEditor());
			return;
		}
		if (key.name === "ctrl-d" && this.state.overlay === "none" && !this.editor.text) {
			void this.close().catch((error) => {
				this.record("error", `Shutdown failed: ${messageOf(error)}`);
			});
			return;
		}
		if (key.name === "ctrl-z") {
			this.enqueue(() => this.suspend());
			return;
		}
		if (key.name === "pageup" || key.name === "pagedown") {
			const direction = key.name === "pageup" ? -1 : 1;
			if (this.state.overlay === "none") this.scrollTranscript(-direction * 8);
			else this.scrollModal(direction * 8);
			this.render();
			return;
		}
		if (this.state.overlay === "trust") {
			this.detachInput(() => this.handleTrustKey(key));
			return;
		}
		if (this.state.overlay === "setup") {
			this.detachInput(() => this.handleSetupKey(key));
			return;
		}
		if (this.state.overlay === "sessions") {
			this.detachInput(() => this.handleSessionKey(key));
			return;
		}
		if (this.state.overlay === "approval" || this.state.overlay === "question") {
			this.detachInput(() => this.handleInteractionKey(key));
			return;
		}
		if (this.state.overlay === "confirm") {
			this.handleConfirmKey(key);
			return;
		}
		if (this.completion) {
			if (key.name === "escape") {
				this.cancelCompletionRequest();
				this.completion = undefined;
				this.render();
				return;
			}
			if (key.name === "up" || key.name === "down") {
				this.completion = moveCompletion(this.completion, key.name === "up" ? -1 : 1);
				this.render();
				return;
			}
			if (key.name === "shift-tab") {
				this.completion = moveCompletion(this.completion, -1);
				this.render();
				return;
			}
			// Enter is the primary send action advertised in the footer. Completion
			// is an assistive picker, so only Tab accepts it; otherwise typing a
			// complete slash command and pressing Enter gets trapped in the picker
			// instead of running the command.
			if (key.name === "tab") {
				this.acceptCompletion();
				this.render();
				return;
			}
		}
		if (key.name === "escape" && this.state.overlay !== "none") {
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return;
		}
		if (this.state.overlay !== "none") {
			if (key.name === "up") this.scrollModal(-1);
			if (key.name === "down") this.scrollModal(1);
			this.render();
			return;
		}
		if (key.name === "escape" && (this.state.turnLive || this.state.submitting)) {
			// kimi parity: Escape interrupts the running turn from the composer too;
			// Ctrl+C remains the hard cancel/exit path.
			void Promise.resolve(this.session?.cancel()).then(
				() => {
					this.record("warning", "Cancellation requested.");
					this.render();
				},
				(error) => {
					this.record("error", `Cancellation failed: ${messageOf(error)}`);
					this.render();
				},
			);
			return;
		}
		if (key.name === "up" && (this.historyIndex > -1 || this.editorAtLineStart())) {
			this.cancelCompletionRequest();
			this.historyMove(-1);
			this.render();
			return;
		}
		if (key.name === "down" && (this.historyIndex > -1 || this.editorAtLineEnd())) {
			this.cancelCompletionRequest();
			this.historyMove(1);
			this.render();
			return;
		}
		if (key.name === "enter") {
			if (this.pasteBurst.shouldInsertNewlineInsteadOfSubmit(Date.now())) {
				this.pasteBurst.extendWindow(Date.now());
				this.editor.handle({ name: "newline", sequence: "\n" });
				this.refreshCompletionAfterEdit();
				this.render();
				return;
			}
			// Snapshot and clear the draft at arrival so keystrokes after Enter can
			// never leak into the queued submission; the composer clears immediately.
			// A busy session queues instead of dropping (submit decides).
			const text = this.expandPastes(this.editor.text).trim();
			if (!text) return;
			if (!text.startsWith("/") && !this.session) {
				this.record("warning", "Select a session with /sessions or create one with /new before sending a prompt.");
				this.render();
				return;
			}
			this.clearEditor();
			this.render();
			this.enqueue(() => this.submit(text));
			return;
		}
		if (key.text && key.text.includes("\n") && this.state.overlay === "none") {
			// TextEditor correctly accepts explicit newline keys but strips newlines
			// from text payloads. Keep every multi-line paste intact, including the
			// one-line-break case, instead of silently joining its two halves.
			this.pasteIntoEditor(key.text);
			this.refreshCompletionAfterEdit();
			return;
		}
		if (this.editor.handle(key)) {
			this.refreshCompletionAfterEdit();
		}
	}
	private async loadHistory(): Promise<void> {
		const loaded = await loadInputHistory(this.historyFile);
		for (const entry of loaded) if (this.history.at(-1) !== entry) this.history.push(entry);
		if (this.history.length > 100) this.history.splice(0, this.history.length - 100);
	}
	private rememberHistory(text: string): void {
		const safeText = historySafeInput(text);
		if (this.history.at(-1) === safeText) return;
		this.history.push(safeText);
		if (this.history.length > 100) this.history.splice(0, this.history.length - 100);
		this.historyWriteTask = this.historyWriteTask
			.then(() => appendInputHistory(this.historyFile, safeText, undefined).then(() => undefined))
			.catch((error) => {
				// Persistence is best-effort, but a silent loss must not masquerade as saved.
				this.record("warning", `Input history could not be persisted: ${messageOf(error)}`);
				this.render();
			});
	}
	private historyMove(delta: number): void {
		if (!this.history.length) return;
		if (delta > 0 && this.historyIndex < 0) return;
		if (delta < 0 && this.historyIndex < 0) {
			this.historyDraft = { text: this.editor.text, cursorIndex: this.editor.cursorIndex };
		}
		if (delta > 0 && this.historyIndex === this.history.length - 1) {
			this.historyIndex = -1;
			const draft = this.historyDraft;
			this.historyDraft = undefined;
			if (draft) this.editor.setWithCursor(draft.text, draft.cursorIndex);
			else this.editor.clear();
			return;
		}
		this.historyIndex = Math.max(
			0,
			Math.min(this.history.length - 1, this.historyIndex < 0 ? this.history.length - 1 : this.historyIndex + delta),
		);
		const value = this.history[this.historyIndex] ?? "";
		this.editor.setWithCursor(value, delta < 0 ? 0 : graphemeCount(value));
	}
	private editorAtLineStart(): boolean {
		const before = sliceGraphemes(this.editor.text, 0, this.editor.cursorIndex);
		return graphemeCount(before.slice(before.lastIndexOf("\n") + 1)) === 0;
	}
	private editorAtLineEnd(): boolean {
		const after = sliceGraphemes(this.editor.text, this.editor.cursorIndex);
		return !after.includes("\n");
	}
	private async handleSessionKey(key: KeyInput): Promise<void> {
		const picker = this.sessionPicker;
		if (!picker) {
			this.dispatch({ type: "overlay", value: "none" });
			return;
		}
		if (key.name === "ctrl-a") {
			this.sessionScope = this.sessionScope === "cwd" ? "all" : "cwd";
			await this.reloadSessionPicker(picker);
			return;
		}
		if (key.name === "ctrl-d") {
			this.sessionPicker = undefined;
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return;
		}
		if (key.name === "pageup" || key.name === "pagedown") {
			// Page navigation belongs to the picker selection, not the frame's raw
			// scroll offset. This keeps the highlighted session and the visible page
			// moving together like KimiCode's picker.
			picker.move((key.name === "pageup" ? -1 : 1) * Math.max(1, this.bodyRows() - 6));
			this.ensureSelectedSessionVisible();
			this.render();
			return;
		}
		if (key.name === "enter") {
			// Commit guard: keys are no longer queued, so a resume already in flight
			// swallows further Enter presses instead of racing a second resume.
			const chosen = picker.chosen();
			if (!chosen || this.sessionActionBusy) return;
			this.sessionActionBusy = true;
			this.render();
			try {
				await this.options.client.resumeSession(chosen.sessionId);
				// Staleness: navigation and Escape stayed live while the resume was in
				// flight; if the picker was dismissed or replaced, discard the result.
				if (this.sessionPicker !== picker || this.closed) return;
				await this.switchSession(this.options.client.session(chosen.sessionId));
			} catch (error) {
				this.record("error", messageOf(error));
				this.render();
			} finally {
				this.sessionActionBusy = false;
				this.render();
			}
			return;
		}
		await picker.handleInput(key);
		this.ensureSelectedSessionVisible();
		this.render();
	}
	private async handleInteractionKey(key: KeyInput): Promise<void> {
		const pending = this.pendingInteractions[0];
		if (key.name === "escape") {
			if (pending?.kind === "approval") await this.answerInteractionGuarded("deny");
			else {
				this.dispatch({ type: "overlay", value: "none" });
				this.render();
			}
			return;
		}
		if (pending?.kind === "approval") {
			if (key.name === "tab") {
				this.approvalEditing = !this.approvalEditing;
				this.render();
				return;
			}
			if (key.name === "ctrl-g") {
				this.approvalPreview = !this.approvalPreview;
				this.render();
				return;
			}
			if (this.approvalEditing) {
				if (key.name === "backspace") this.approvalFeedback = [...this.approvalFeedback].slice(0, -1).join("");
				else if (key.name === "enter") this.approvalEditing = false;
				else if (key.text && !key.text.includes("\n")) this.approvalFeedback += key.text;
				this.render();
				return;
			}
			if (key.name === "ctrl-d") {
				await this.answerInteractionGuarded("deny");
				return;
			}
			if (key.name === "ctrl-o") {
				if (pending.request.preview) {
					this.approvalOutputExpanded = !this.approvalOutputExpanded;
					this.approvalPreview = this.approvalOutputExpanded;
					this.render();
				} else this.toggleLatestExpandableRecord();
				return;
			}
			if (key.text && /^[1-3]$/.test(key.text)) {
				await this.answerInteractionGuarded(["once", "session", "deny"][Number(key.text) - 1]!);
				return;
			}
			if (key.name === "up" || key.name === "down") {
				const previous = key.name === "up";
				this.interactionChoice = (this.interactionChoice + (previous ? 2 : 1)) % 3;
				this.render();
				return;
			}
			if (key.name === "enter") {
				await this.answerInteractionGuarded(["once", "session", "deny"][this.interactionChoice]!);
				return;
			}
		} else {
			if (key.name === "ctrl-d") {
				this.questionEditor.clear();
				this.dispatch({ type: "overlay", value: "none" });
				this.render();
				return;
			}
			const options = pending?.request.options ?? [];
			if (key.name === "up" || key.name === "down") {
				const count = options.length + 1;
				const previous = key.name === "up";
				this.interactionChoice = (this.interactionChoice + (previous ? count - 1 : 1)) % count;
				this.render();
				return;
			}
			if (key.name === "enter" && this.interactionChoice < options.length) {
				await this.answerInteractionGuarded(options[this.interactionChoice]!);
				return;
			}
			if (key.name === "enter") {
				if (await this.answerInteractionGuarded(this.questionEditor.text)) this.questionEditor.clear();
				return;
			}
		}
		if (this.questionEditor.handle(key)) this.render();
	}
	private toggleLatestExpandableRecord(): void {
		const target = [...this.state.transcript]
			.reverse()
			.find((record) => record.kind === "tool" || record.kind === "tool-result" || record.kind === "thinking");
		if (!target) return;
		const expanded = this.collapsed.has(target.id);
		if (expanded) this.collapsed.delete(target.id);
		else this.collapsed.add(target.id);
		this.dispatch({ type: "replace", id: target.id, patch: { expanded: !expanded } });
		this.render();
	}
	/** Editor edits render immediately; the completion refresh follows off the echo path. */
	private refreshCompletionAfterEdit(): void {
		this.historyIndex = -1;
		this.historyDraft = undefined;
		this.cancelCompletionRequest();
		const requestId = this.completionRequestId;
		this.render();
		const beforeCursor = sliceGraphemes(this.editor.text, 0, this.editor.cursorIndex);
		const delay = /(^|\s)@[^\s]*$/u.test(beforeCursor) ? 20 : 0;
		const start = () => {
			this.completionDebounceTimer = undefined;
			const controller = new AbortController();
			this.completionAbort = controller;
			void this.refreshCompletion(requestId, controller.signal).then(
				() => this.render(),
				(error) => {
					if (!controller.signal.aborted) this.record("error", `Input failed: ${messageOf(error)}`);
					this.render();
				},
			);
		};
		if (delay) this.completionDebounceTimer = setTimeout(start, delay);
		else start();
	}
	private async refreshCompletion(requestId = this.completionRequestId, signal?: AbortSignal): Promise<void> {
		const snapshotText = this.editor.text;
		const snapshotCursor = this.editor.cursorIndex;
		const beforeCursor = sliceGraphemes(snapshotText, 0, snapshotCursor);
		if (signal?.aborted) return;
		if (!/(^|\s)@([^\s]*)$/.test(beforeCursor)) {
			if (
				requestId === this.completionRequestId &&
				this.editor.text === snapshotText &&
				this.editor.cursorIndex === snapshotCursor
			)
				this.completion = completionFor(snapshotText, snapshotCursor, []);
			return;
		}
		const entries = (await readdir(this.options.cwd, { withFileTypes: true }).catch(() => []))
			.filter((entry) => entry.isFile() || entry.isDirectory())
			.map((entry) => `@${entry.name}${entry.isDirectory() ? "/" : ""}`);
		if (
			signal?.aborted ||
			requestId !== this.completionRequestId ||
			this.editor.text !== snapshotText ||
			this.editor.cursorIndex !== snapshotCursor
		)
			return;
		this.completion = completionFor(snapshotText, snapshotCursor, entries);
	}
	private acceptCompletion(): void {
		const completion = this.completion;
		if (!completion) return;
		this.cancelCompletionRequest();
		const replacement = applyCompletion(this.editor.text, this.editor.cursorIndex, completion);
		this.editor.setWithCursor(replacement.text, replacement.cursorIndex);
		this.completion = undefined;
	}
	/** Collapses a multi-line bracketed paste into an inline marker; full text is restored at submit time. */
	private pasteIntoEditor(text: string): boolean {
		const id = ++this.pasteCounter;
		this.pastes.set(id, text);
		const marker = `[paste #${id} +${text.split("\n").length - 1} lines]`;
		this.editor.setWithCursor(
			`${sliceGraphemes(this.editor.text, 0, this.editor.cursorIndex)}${marker}${sliceGraphemes(this.editor.text, this.editor.cursorIndex)}`,
			this.editor.cursorIndex + graphemeCount(marker),
		);
		return true;
	}
	private expandPastes(text: string): string {
		return text.replace(/\[paste #(\d+) \+\d+ lines\]/g, (whole, id) => this.pastes.get(Number(id)) ?? whole);
	}
	/** Clears the draft and drops any paste markers it referenced. */
	private clearEditor(): void {
		this.cancelCompletionRequest();
		this.completion = undefined;
		this.editor.clear();
		this.pastes.clear();
	}
	private cancelCompletionRequest(): void {
		this.completionRequestId += 1;
		if (this.completionDebounceTimer) clearTimeout(this.completionDebounceTimer);
		this.completionDebounceTimer = undefined;
		this.completionAbort?.abort();
		this.completionAbort = undefined;
	}

	private async submit(text?: string): Promise<void> {
		// Callers that pass a snapshot (the Enter path) already cleared the draft at
		// key arrival; direct callers read, expand, and clear the live editor here.
		const rawPromptText = text ?? this.expandPastes(this.editor.text).trim();
		const promptText = rawPromptText;
		if (!promptText) return;
		if (promptText.startsWith("/")) {
			if (text === undefined) this.clearEditor();
			this.historyIndex = -1;
			this.rememberHistory(promptText);
			await this.runCommand(promptText);
			return;
		}
		if (!this.session) {
			this.record("warning", "Select a session with /sessions or create one with /new before sending a prompt.");
			this.render();
			return;
		}
		if (text === undefined) this.clearEditor();
		this.historyIndex = -1;
		this.rememberHistory(promptText);
		let mentionedAttachments: PromptPart[] = [];
		let promptTextWithMentions = promptText;
		try {
			const materialized = await this.materializeComposerMentions(promptText);
			promptTextWithMentions = materialized.text;
			mentionedAttachments = materialized.attachments;
		} catch (error) {
			this.record("error", messageOf(error));
			this.render();
			return;
		}
		const prompt = {
			id: `q-${Date.now()}`,
			text: promptTextWithMentions,
			attachments: mentionedAttachments,
		} satisfies Omit<QueuedPrompt, "state">;
		if (this.state.submitting || shouldQueuePrompt(this.state.turnLive)) {
			// kimi parity: a submission that arrives while another send or a turn is
			// still in flight queues instead of being silently dropped.
			this.dispatch({ type: "queue", value: [...this.state.queue, { ...prompt, state: "queued" }] });
			this.record("status", "Prompt queued until the current turn completes.");
			this.render();
			return;
		}
		await this.sendPrompt({ ...prompt, state: "sending" });
	}
	private async sendPrompt(prompt: QueuedPrompt): Promise<void> {
		if (!this.session) return;
		this.dispatch({ type: "submitting", value: true });
		let turnExpected = false;
		try {
			if (prompt.text.startsWith("!")) {
				const task = await this.session.runShell(prompt.text.slice(1), { background: true });
				this.record("process", `Shell task started · ${shortId(task.taskId)}`);
			} else {
				await this.session.prompt({ parts: [...prompt.attachments, { type: "text", text: prompt.text }] });
				turnExpected = true;
			}
		} catch (error) {
			this.record("error", messageOf(error));
			this.dispatch({
				type: "queue",
				value: [{ ...prompt, state: "failed", error: messageOf(error) }, ...this.state.queue],
			});
		} finally {
			this.dispatch({ type: "submitting", value: false });
			this.render();
			// Sends that produce no turn.end (background shell tasks, failures) must
			// release the next queued prompt themselves; turn-bound sends are released
			// by the turn.end event. Macrotask, so a send that itself came from
			// releaseQueuedPrompt does not trip its re-entry guard.
			if (!turnExpected)
				setTimeout(() => {
					if (!this.closed) void this.releaseQueuedPrompt();
				}, 0);
		}
	}
	private async releaseQueuedPrompt(): Promise<void> {
		if (this.releasingQueuedPrompt) return;
		const index = this.state.queue.findIndex((item) => item.state === "queued");
		if (index < 0) return;
		this.releasingQueuedPrompt = true;
		const next = this.state.queue[index]!;
		this.dispatch({ type: "queue", value: this.state.queue.filter((_, itemIndex) => itemIndex !== index) });
		try {
			await this.sendPrompt({ ...next, state: "sending" });
		} finally {
			this.releasingQueuedPrompt = false;
		}
	}

	private async runCommand(command: string): Promise<void> {
		let parsed: string[];
		try {
			parsed = splitCommandArguments(command.slice(1));
		} catch (error) {
			this.record("warning", messageOf(error));
			this.render();
			return;
		}
		const [rawName, ...args] = parsed;
		const slash = findSlashCommand(rawName ?? "");
		if (!slash) {
			this.record("warning", `Unknown command: /${rawName ?? ""}`);
			this.render();
			return;
		}
		if (slash.argumentHint === "(no arguments)" && args.length) {
			this.record("warning", `/${slash.name} takes no arguments. Open /help for its guided controls.`);
			this.render();
			return;
		}
		if (slash.needsSession && !this.session) {
			this.record("warning", `/${slash.name} requires an active session.`);
			this.render();
			return;
		}
		if (slash.availability !== "always" && this.state.turnLive) {
			this.record("warning", `/${slash.name} is unavailable while a turn is running.`);
			this.render();
			return;
		}
		try {
			await slash.run(args, this.commandContext());
			await this.refreshRuntimeModel();
		} catch (error) {
			this.record("error", messageOf(error));
		}
		this.render();
	}
	private commandContext(): CommandContext {
		return {
			client: this.options.client,
			session: this.session,
			cwd: this.options.cwd,
			notice: (kind, text) => this.record(kind, text),
			showLines: (lines) => {
				this.activityLines = [...lines];
				this.showModal("activities");
			},
			showDetails: (lines) => {
				this.activityLines = [...lines];
				this.showModal("details");
			},
			showOverlay: (overlay) => (overlay === "sessions" ? this.showSessions() : this.showModal(overlay)),
			showInteractions: () => {
				const pending = this.pendingInteractions[0];
				if (!pending) {
					this.record("warning", "No approval or question is waiting.");
					return;
				}
				this.showModal(pending.kind === "approval" ? "approval" : "question");
			},
			openShell: () => this.openShell(),
			openSetup: async () => {
				await this.runSetupWizard();
			},
			openOAuthSetup: async (provider) => {
				await this.runSetupWizard(provider, "oauth", true);
			},
			openPanel: (panel, args = []) => this.openCommandPanel(panel, args),
			refreshLearningPending: () => void this.refreshLearningPending(),
			confirm: (message) => this.askConfirm(message),
			switchSession: (session) => this.switchSession(session),
			quit: () => this.close(),
		};
	}
	private async openCommandPanel(panel: InteractivePanelName, args: readonly string[]): Promise<void> {
		this.panelCommandPrefills = [];
		this.requestedModelQuery = undefined;
		const [subcommand, ...rest] = args;
		if (panel === "fork") {
			if (!this.session) return;
			if (!(await this.askConfirm("Fork the current session and continue in the new copy?"))) return;
			await this.switchSession(await this.options.client.forkSession(this.session.id));
			this.record("status", "Session forked.");
			return;
		}
		if (panel === "archive" && subcommand === "off") {
			if (!this.session) return;
			if (!(await this.askConfirm("Unarchive this session and keep working in it?"))) return;
			await this.options.client.archiveSession(this.session.id, false);
			this.record("status", "Session unarchived.");
			return;
		}
		if (panel === "activity" && subcommand === "history") {
			await this.openActivityBrowser(false);
			return;
		}
		if (panel === "activity" && subcommand === "current") {
			await this.openActivityBrowser(true);
			return;
		}
		if (panel === "activity" && subcommand) {
			await this.openActivityBrowser(false);
			if (this.panel?.kind === "menu") {
				this.panel.query = subcommand;
				this.normalizeMenuSelection(this.panel);
				this.render();
			}
			return;
		}
		if (panel === "memory" && subcommand === "recall") {
			const query = rest.join(" ");
			this.openFormPanel("Recall profile memory", "Query", query, async (value) => {
				if (!this.session) return;
				const options = this.panelRequestOptions();
				const entries = (await this.options.client.recallProfile(this.session.id, value, options)) as readonly {
					scope?: string;
					fact?: string;
				}[];
				if (options.signal?.aborted) return;
				this.showPanelResult(
					entries.length
						? entries.map((entry) => `${entry.scope ?? "profile"} · ${entry.fact ?? "(empty fact)"}`)
						: ["No matching profile memories."],
					"Profile memory",
					"memory",
				);
			});
			return;
		}
		if (panel === "mcp" && subcommand === "add") {
			this.openMcpAddWizard(rest);
			return;
		}
		if (panel === "graph" && subcommand === "set") {
			await this.openGraphSetPanel(rest);
			return;
		}
		if (panel === "goal" && subcommand && !["status", "pause", "resume", "complete", "create"].includes(subcommand)) {
			this.openGoalCreateForm(args.join(" "));
			return;
		}
		if (panel === "plan" && subcommand && !["status", "approve", "revise", "cancel"].includes(subcommand)) {
			this.openFormPanel("Draft plan", "Objective", args.join(" "), (value) =>
				this.sendPlanInstruction(`Draft an execution plan for: ${value}`),
			);
			return;
		}
		if (panel === "auth" && subcommand === "set")
			this.record(
				"warning",
				"For safety, API keys must be entered in the masked credential form; command-line key text is not applied.",
			);
		if (panel === "config" && subcommand === "path") {
			const scope = rest[0] === "user" ? "user" : "project";
			const file = await this.options.client.configurationPath(scope);
			this.showPanelResult([`${scope} configuration`, file], "Configuration file location", "config");
			return;
		}
		if (panel === "config" && subcommand === "permission") {
			const section = SETTINGS_SECTIONS.find((candidate) => candidate.id === "permission");
			if (section) await this.openSettingsSection(section);
			return;
		}
		if (panel === "config" && subcommand === "set" && rest[0]) {
			this.record(
				"warning",
				"Typed values are not applied by /config set. Select the field and enter a validated value in Settings.",
			);
			await this.openConfigFieldByPath(rest[0]);
			return;
		}
		if (panel === "compact" && args.length) {
			this.openFormPanel(
				"Compact context",
				"Instructions (optional)",
				args.join(" "),
				async (value) => {
					if (!this.session) return;
					const options = this.panelRequestOptions();
					const result = (await this.session.compact(value || undefined, options)) as {
						outcome?: string;
						reason?: string;
					} | null;
					if (options.signal?.aborted) return;
					if (result?.outcome && result.outcome !== "compacted")
						this.record("warning", `Compaction ${result.outcome}${result.reason ? ` (${result.reason})` : ""}.`);
					else this.record("status", "Context compacted.");
					this.closePanel();
				},
				false,
				"compact",
				undefined,
				true,
			);
			return;
		}
		this.panelCommandPrefills = commandPanelPrefills(panel, args);
		await this.openInteractivePanel(panel, false, undefined, args);
		if (!args.length) return;
		if (panel === "sessions" && this.sessionPicker) {
			return;
		}
		if (this.panel?.kind === "menu") {
			const query = commandPanelQuery(panel, args);
			if (query) {
				this.panel.query = query;
				this.normalizeMenuSelection(this.panel);
				if (!visibleMenuItems(this.panel).some((item) => this.panelActions.has(item.id)))
					this.panelActionError = `No guided action matches “${query}”. Clear the search to browse all actions.`;
				this.render();
			}
		} else if (this.panel?.kind === "form" && !this.panel.value) {
			this.panel.value = args.join(" ");
			this.panel.cursorIndex = graphemeCount(this.panel.value);
			this.render();
		} else if (this.panel?.kind === "model") {
			if (args[0] === "show") return;
			if ((args[0] === "discover" || args[0] === "set") && args[1]) {
				const requestedProvider = args[1]!.toLocaleLowerCase();
				const requestedAuthMode =
					(args[0] === "discover" ? args[2] : args[4]) === "api" ||
					(args[0] === "discover" ? args[2] : args[4]) === "oauth"
						? ((args[0] === "discover" ? args[2] : args[4]) as "api" | "oauth")
						: undefined;
				const routeIndex = this.panel.routes.findIndex(
					(route) =>
						route.provider.toLocaleLowerCase() === requestedProvider &&
						route.provider !== "__setup__" &&
						(!requestedAuthMode || route.authMode === requestedAuthMode),
				);
				this.panel.step = "route";
				if (routeIndex >= 0) {
					this.panel.routeIndex = routeIndex;
					this.requestedModelQuery = args[0] === "set" ? args[2] : undefined;
					if (args[0] === "set" && args[3] !== undefined) {
						const contextLimit = Number(args[3]);
						if (!Number.isFinite(contextLimit) || contextLimit <= 0) {
							this.panel.error =
								"Context override must be a positive token count; choose a model to use provider metadata.";
							this.render();
							return;
						}
						this.panel.contextLimitOverride = contextLimit;
					}
					this.panel.error = `Requested provider ${this.panel.routes[routeIndex]!.label}; press Enter to discover models.`;
				} else {
					this.panel.step = "role";
					this.panel.error = `No configured route matches provider “${args[1]}”.`;
				}
			} else this.panel.error = `Requested: /${panel} ${args.join(" ")} · continue with the guided controls.`;
			this.ensureSelectedModalVisible();
			this.render();
		} else if (this.panel?.kind === "graph") {
			this.panel.error = `Requested: /${panel} ${args.join(" ")} · select the profile and field to edit.`;
			this.render();
		}
	}
	private openGoalCreateForm(value: string): void {
		const submit = async (objective: string): Promise<void> => {
			if (!this.session) return;
			const options = this.panelRequestOptions();
			const existing = await this.session.getGoal(options);
			if (options.signal?.aborted) return;
			if (existing) {
				const confirmed = await this.askConfirm("Replace the active goal with this objective?");
				if (options.signal?.aborted) return;
				if (!confirmed) {
					this.record("status", "Goal replacement cancelled.");
					this.openGoalCreateForm(objective);
					return;
				}
				await this.session.updateGoal({ status: "completed" }, options);
				if (options.signal?.aborted) return;
			}
			await this.session.createGoal({ objective }, options);
			if (options.signal?.aborted) return;
			this.record("status", "Goal created.");
			this.closePanel();
		};
		this.openFormPanel("Session goal", "Objective", value, submit);
	}
	private async openGraphSetPanel(args: readonly string[]): Promise<void> {
		const [targetName, fieldOrProvider, ...valueParts] = args;
		await this.openInteractivePanel("graph");
		const menu = this.panel;
		if (!menu || menu.kind !== "menu") return;
		const listField =
			fieldOrProvider === "tools" ||
			fieldOrProvider === "permissionProfile" ||
			fieldOrProvider === "interactionMode";
		if (!targetName || !fieldOrProvider || (valueParts.length === 0 && !listField)) {
			menu.query = "";
			this.panelActionError =
				"Use /graph set <profile> <field> [value] or /graph set <profile> <provider> <model> [api|oauth].";
			this.render();
			return;
		}
		const target = menu.items.find(
			(item) =>
				item.id.toLocaleLowerCase() === targetName.toLocaleLowerCase() ||
				item.id === `subagent:${targetName}` ||
				item.label.toLocaleLowerCase() === targetName.toLocaleLowerCase(),
		);
		if (!target) {
			menu.query = targetName;
			this.panelActionError = `No editable agent profile matches “${targetName}”.`;
			this.render();
			return;
		}
		const openTarget = this.panelActions.get(target.id);
		if (!openTarget) {
			this.panelActionError = `Profile “${targetName}” has no guided editor.`;
			this.render();
			return;
		}
		await openTarget();
		const graphPanel = this.panel;
		if (!graphPanel || graphPanel.kind !== "graph") return;
		const field = graphPanel.fields.find((candidate) => candidate === fieldOrProvider);
		if (field === "tools") {
			graphPanel.fieldIndex = graphPanel.fields.indexOf(field);
			await this.openGraphToolsPicker(
				graphPanel.target,
				graphPanel.config[graphPanel.target.id]?.["tools"],
				valueParts.join(" "),
			);
			return;
		}
		if (field === "permissionProfile" || field === "interactionMode") {
			graphPanel.fieldIndex = graphPanel.fields.indexOf(field);
			this.openGraphChoicePanel(graphPanel.target, field, valueParts.join(" "));
			return;
		}
		if (
			field &&
			field !== "route" &&
			field !== "reset" &&
			field !== "remove"
		) {
			const value = valueParts.join(" ");
			if (!value.trim()) {
				graphPanel.error = `Enter a value for ${graphFieldLabel(field)}.`;
				this.render();
				return;
			}
			graphPanel.fieldIndex = graphPanel.fields.indexOf(field);
			graphPanel.editing = { field, value, cursorIndex: graphemeCount(value) };
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		const knownField = [
			"description",
			"whenToUse",
			"route",
			"baseUrl",
			"contextLength",
			"maxContextSize",
			"maxOutputTokens",
			"maxSteps",
			"timeoutMs",
			"runTimeoutMs",
			"maxQueuedRuns",
			"systemPrompt",
			"permissionProfile",
			"interactionMode",
			"tools",
		].includes(fieldOrProvider);
		if (knownField && field !== "route") {
			graphPanel.error = `${fieldOrProvider} cannot be edited for ${graphPanel.target.label} in this panel.`;
			this.render();
			return;
		}
		const provider = field === "route" ? valueParts[0] : fieldOrProvider;
		const model = field === "route" ? valueParts[1] : valueParts[0];
		const authModeArgument = field === "route" ? valueParts[2] : valueParts[1];
		const authMode = authModeArgument === "api" || authModeArgument === "oauth" ? authModeArgument : undefined;
		if (!provider || !model) {
			graphPanel.error =
				field === "route"
					? "Enter a provider and model after route to open the guided route picker."
					: "Enter both a provider and model to open the guided route picker.";
			this.render();
			return;
		}
		const routeFieldIndex = graphPanel.fields.indexOf("route");
		if (routeFieldIndex < 0) {
			graphPanel.error = `Model routing is unavailable for ${graphPanel.target.label}.`;
			this.render();
			return;
		}
		graphPanel.fieldIndex = routeFieldIndex;
		await this.handleGraphPanelKey({ name: "enter", sequence: "\r" });
		const modelPanel = this.panel;
		if (!modelPanel || modelPanel.kind !== "model") return;
		const routeIndex = modelPanel.routes.findIndex(
			(route) =>
				route.provider.toLocaleLowerCase() === provider.toLocaleLowerCase() &&
				(!authMode || route.authMode === authMode),
		);
		if (routeIndex < 0) {
			modelPanel.error = `No configured ${authMode ? `${authMode} ` : ""}route matches “${provider}”.`;
			this.render();
			return;
		}
		modelPanel.routeIndex = routeIndex;
		modelPanel.error = `Requested ${provider} / ${model}; press Enter to discover and review the model.`;
		this.requestedModelQuery = model;
		this.ensureSelectedModalVisible();
		this.render();
	}
	private openMcpAddWizard(args: readonly string[]): void {
		const [initialName = "", initialCommand = "", ...initialArgs] = args;
		const initialArgumentText = initialArgs.map(quoteCommandArgument).join(" ");
		this.openFormPanel(
			"Add MCP server",
			"Server id",
			initialName,
			(serverId) => {
				if (!/^[A-Za-z0-9_-]{1,64}$/.test(serverId))
					throw new Error("Use 1–64 letters, numbers, underscores, or hyphens.");
				this.openFormPanel(
					"Add MCP server",
					"Command",
					initialCommand,
					(command) => {
						this.openFormPanel(
							"Add MCP server",
							"Arguments (space separated; quotes group values)",
							initialArgumentText,
							async (rawArgs) => {
								const parsedArgs = splitCommandArguments(rawArgs);
								const options = this.panelRequestOptions();
								await this.options.client.updateConfiguration(
									{ mcp: { servers: { [serverId]: { command, args: parsedArgs } } } },
									undefined,
									options,
								);
								if (options.signal?.aborted) return;
								if (this.session) await this.options.client.reloadCapabilities(this.session.id, options);
								if (options.signal?.aborted) return;
								this.record("status", `MCP server ${serverId} added.`);
								await this.openInteractivePanel("mcp");
							},
							false,
							"mcp",
							undefined,
							true,
						);
					},
					false,
					"mcp",
				);
			},
			false,
			"mcp",
		);
	}
	private async openConfigFieldByPath(path: string): Promise<void> {
		for (const section of SETTINGS_SECTIONS) {
			const index = section.fields.findIndex((field) => field.path === path);
			if (index < 0) continue;
			await this.openSettingsSection(section, index);
			if (this.panel?.kind === "menu") {
				this.panel.query = section.fields[index]!.label;
				this.normalizeMenuSelection(this.panel);
				this.render();
			}
			return;
		}
		await this.openSettingsPanel();
		this.panelActionError = `Unknown setting “${path}”. Choose a setting section to browse available fields.`;
		this.render();
	}
	private async openInteractivePanel(
		panel: InteractivePanelName,
		dataLoadStarted = false,
		guard?: PanelOperationGuard,
		commandArgs: readonly string[] = [],
	): Promise<void> {
		// A load cancelled by Escape (the busy-abort trips the signal and bumps
		// panelOperationId) must never open the panel anyway once its data arrives.
		if (this.panelGuardStale(guard)) return;
		// Any panel (re)open supersedes the learner auto-refresh; showLearnPanel
		// restarts it once the proposal list is actually on screen.
		this.stopLearnRefresh();
		const loadingLabel = dataLoadStarted ? undefined : panelLoadingLabel(panel);
		if (loadingLabel) {
			await this.runPanelLoad(panelLabel(panel), loadingLabel, (loadGuard) =>
				this.openInteractivePanel(panel, true, loadGuard, commandArgs),
			);
			return;
		}
		if (panel === "sessions") {
			await this.showSessions(commandArgs.join(" "));
			return;
		}
		if (panel === "help") {
			const commands = slashCommands.filter((command) => !command.hidden);
			const items: PanelMenuItem[] = [
				{ id: "keyboard", label: "Keyboard shortcuts", detail: "Composer, navigation and cancellation keys" },
				...commands.map((command) => ({
					id: command.name,
					label: `/${command.name}${command.argumentHint ? ` ${command.argumentHint}` : ""}`,
					detail: command.description,
				})),
			];
			const actions = new Map<string, () => void>();
			actions.set("keyboard", () =>
				this.showPanelResult(
					[
						"Enter: send · Alt+Enter: newline · Up/Down: history",
						"Ctrl+G: editor · Ctrl+O: expand output · Ctrl+T: activity",
						"Esc: interrupt/back · Ctrl+C: cancel/clear · Ctrl+D: exit",
					],
					"Keyboard shortcuts",
					"help",
				),
			);
			for (const command of commands)
				actions.set(command.name, () =>
					this.showPanelResult(
						[
							`Command: /${command.name}`,
							...(command.aliases?.length
								? [`Aliases: ${command.aliases.map((alias) => `/${alias}`).join(", ")}`]
								: []),
							`Category: ${command.category}`,
							`Arguments: ${command.argumentHint ?? "(none)"}`,
							command.description,
						],
						`Help · /${command.name}`,
						"help",
					),
				);
			this.openMenuPanel("Help", items, actions);
			return;
		}
		if (panel === "model") {
			await this.openModelPanel(undefined, false, guard);
			return;
		}
		if (panel === "graph") {
			await this.openGraphPanel(guard);
			return;
		}
		if (panel === "auth") {
			await this.openAuthPanel(guard);
			return;
		}
		if (panel === "config") {
			await this.openSettingsPanel(guard);
			return;
		}
		if (panel === "theme") {
			this.openMenuPanel(
				`Theme · ${this.themeName}`,
				[
					{ id: "system", label: "System", detail: "Follow terminal light/dark preference" },
					{ id: "dark", label: "Dark" },
					{ id: "light", label: "Light" },
				],
				new Map([
					["system", () => this.applyTheme("system")],
					["dark", () => this.applyTheme("dark")],
					["light", () => this.applyTheme("light")],
				]),
				undefined,
				Math.max(0, ["system", "dark", "light"].indexOf(this.themeName)),
			);
			return;
		}
		if (panel === "undo") {
			await this.openUndoPanel(guard);
			return;
		}
		if (panel === "new") {
			this.openFormPanel(
				"New session",
				"Title (optional)",
				"",
				async (value) => {
					const options = this.panelRequestOptions();
					const session = await this.options.client.createSession({ cwd: this.options.cwd }, options);
					if (options.signal?.aborted) return;
					if (value) await this.options.client.renameSession(session.id, value, options);
					if (options.signal?.aborted) return;
					await this.switchSession(session);
					this.record("status", value ? `Session “${value}” created.` : "New session created.");
					this.closePanel();
				},
				false,
				undefined,
				undefined,
				true,
			);
			return;
		}
		if (panel === "compact") {
			this.openMenuPanel(
				"Compact context",
				[
					{
						id: "compact",
						label: "Compact now",
						detail: "Summarize older turns while preserving current instructions and tool state",
					},
					{ id: "cancel", label: "Cancel" },
				],
				new Map([
					[
						"compact",
						async () => {
							if (this.session) {
								const options = this.panelRequestOptions();
								const result = (await this.session.compact(undefined, options)) as {
									outcome?: string;
									reason?: string;
								} | null;
								if (options.signal?.aborted) return;
								if (result?.outcome && result.outcome !== "compacted")
									this.record("warning", `Compaction ${result.outcome}${result.reason ? ` (${result.reason})` : ""}.`);
								else this.record("status", "Context compacted.");
							}
							this.closePanel();
						},
					],
					["cancel", () => this.closePanel()],
				]),
			);
			return;
		}
		if (panel === "activity") {
			this.openMenuPanel(
				"Activity",
				[
					{ id: "current", label: "Current work", detail: "Live tasks for this session" },
					{ id: "history", label: "Activity history", detail: "Recorded work across sessions" },
				],
				new Map([
					["current", () => this.openActivityBrowser(true)],
					["history", () => this.openActivityBrowser(false)],
				]),
			);
			return;
		}
		if (panel === "cron") {
			if (!this.session || typeof this.options.client.listCron !== "function") {
				this.showPanelResult(["Scheduled prompts are unavailable in this session."], "Scheduled prompts");
				return;
			}
			const jobs = await this.options.client.listCron(this.session.id, this.panelRequestOptions());
			if (this.panelGuardStale(guard)) return;
			const actions = new Map<string, () => Promise<void> | void>();
			// Reserved rows are prefixed so a real job id can never collide (learn/settings convention).
			const items: PanelMenuItem[] = [
				{
					id: "__create",
					label: "Create scheduled prompt",
					detail: "Choose the schedule and prompt in the next steps",
				},
			];
			for (const job of jobs) {
				items.push({
					id: job.id,
					label: job.cron,
					detail: `${job.id} · ${job.prompt ?? job.nextFireAt ?? "scheduled"}`,
				});
				actions.set(job.id, () =>
					this.openMenuPanel(
						`Scheduled prompt · ${job.cron}`,
						[
							{ id: "delete", label: "Delete this schedule" },
							{ id: "cancel", label: "Cancel" },
						],
						new Map([
							[
								"delete",
								async () => {
									const confirmed = await this.askConfirm(`Delete scheduled prompt ${job.id}?`);
									if (!confirmed) {
										this.record("status", "Scheduled prompt deletion cancelled.");
										return;
									}
									const options = this.panelRequestOptions();
									const deleted = await this.options.client.deleteCron(this.session!.id, job.id, options);
									if (options.signal?.aborted) return;
									if (!deleted) {
										this.record("warning", `Scheduled prompt ${job.id} was not found; it was already removed.`);
										this.closePanel();
										return;
									}
									this.record("status", "Scheduled prompt deleted.");
									this.closePanel();
								},
							],
							["cancel", () => this.openInteractivePanel("cron")],
						]),
					),
				);
			}
			actions.set("__create", () =>
				this.openFormPanel("Create scheduled prompt", "Schedule (cron expression)", "", (cron) =>
					this.openFormPanel("Create scheduled prompt", "Prompt", "", async (prompt) => {
						const options = this.panelRequestOptions();
						await this.options.client.createCron(this.session!.id, { cron, prompt, recurring: true }, options);
						if (options.signal?.aborted) return;
						this.record("status", "Scheduled prompt created.");
						await this.openInteractivePanel("cron");
					}),
				),
			);
			this.openMenuPanel("Scheduled prompts", items, actions);
			return;
		}
		if (panel === "tools") {
			if (!this.session) {
				this.showPanelResult(["An active session is required to list tools."], "Tools");
				return;
			}
			const items = await this.options.client.listTools(this.session.id, this.panelRequestOptions());
			if (this.panelGuardStale(guard)) return;
			const menuItems = items.length
				? items.map((item) => ({
						id: item.name,
						label: item.name,
						detail: `${item.provenance.kind} · ${item.provenance.ownerId}`,
					}))
				: [{ id: "__empty", label: "No tools available." }];
			const actions = new Map<string, () => void>();
			for (const item of items)
				actions.set(item.name, () =>
					this.showPanelResult(
						[`Name: ${item.name}`, `Source: ${item.provenance.kind}`, `Owner: ${item.provenance.ownerId}`],
						`Tool · ${item.name}`,
						"tools",
					),
				);
			this.openMenuPanel("Tools", menuItems, actions);
			return;
		}
		if (panel === "capabilities") {
			this.openMenuPanel(
				"Capabilities",
				[
					{ id: "all", label: "All capabilities" },
					{ id: "tools", label: "Tools" },
					{ id: "skills", label: "Skills" },
					{ id: "plugins", label: "Plugins" },
					{ id: "mcp", label: "MCP servers" },
				],
				new Map([
					[
						"all",
						async () => {
							if (!this.session) return;
							const options = this.panelRequestOptions();
							const items = await this.options.client.listCapabilities(this.session.id, undefined, options);
							if (options.signal?.aborted) return;
							this.showPanelResult(
								items.length
									? items.map((item) => `${item.kind}  ${item.id}${item.description ? ` — ${item.description}` : ""}`)
									: ["No active capabilities."],
								"All capabilities",
								"capabilities",
							);
						},
					],
					["tools", () => this.openInteractivePanel("tools")],
					["skills", () => this.openInteractivePanel("skills")],
					["plugins", () => this.openInteractivePanel("plugins")],
					["mcp", () => this.openInteractivePanel("mcp")],
				]),
			);
			return;
		}
		if (panel === "skills" || panel === "plugins" || panel === "mcp") {
			if (!this.session) {
				this.showPanelResult([`An active session is required to open ${panel}.`], panelLabel(panel));
				return;
			}
			const kind = panel === "skills" ? "skill" : panel === "plugins" ? "plugin" : "mcp";
			const items = await this.options.client.listCapabilities(this.session.id, kind, this.panelRequestOptions());
			if (this.panelGuardStale(guard)) return;
			const menuItems: PanelMenuItem[] = items.map((item) => ({
				id: item.id,
				label: item.id,
				detail: item.description ?? "",
			}));
			// Capability ids are user-controlled, so opaque internal ids prevent a
			// plugin named e.g. "__install" from shadowing a panel action.
			if (panel === "skills") menuItems.push({ id: PANEL_ACTION_RELOAD, label: "Reload skills" });
			if (panel === "plugins")
				menuItems.push({
					id: PANEL_ACTION_INSTALL,
					label: "Install plugin",
					detail: "Enter a source in the next field",
				});
			if (panel === "mcp")
				menuItems.push(
					{ id: PANEL_ACTION_INSTALL, label: "Add MCP server", detail: "Configure a command in three guided fields" },
					{ id: PANEL_ACTION_RELOAD, label: "Reconnect capabilities" },
				);
			const actions = new Map<string, () => Promise<void> | void>();
			for (const item of items) {
				actions.set(item.id, async () => {
					if (panel === "skills") {
						if (await this.askConfirm(`Remove skill ${item.id}?`)) {
							const options = this.panelRequestOptions();
							await this.options.client.removeSkill(item.id, options);
							if (options.signal?.aborted) return;
							this.record("status", `Skill ${item.id} removed.`);
							await this.openInteractivePanel("skills");
						} else {
							this.record("status", `Skill ${item.id} removal cancelled.`);
							await this.openInteractivePanel("skills");
						}
					} else if (panel === "plugins") {
						if (await this.askConfirm(`Uninstall plugin ${item.id}?`)) {
							const options = this.panelRequestOptions();
							await this.options.client.uninstallPlugin(item.id, options);
							if (options.signal?.aborted) return;
							this.record("status", `Plugin ${item.id} removed.`);
							await this.openInteractivePanel("plugins");
						} else {
							this.record("status", `Plugin ${item.id} removal cancelled.`);
							await this.openInteractivePanel("plugins");
						}
					} else {
						const actions = new Map<string, () => Promise<void> | void>([
							[
								"details",
								() =>
									this.showPanelResult(
										[
											`Server: ${item.id}`,
											`Authentication: ${item.authSupported ? "available" : "not required"}`,
											...(item.description ? [`Description: ${item.description}`] : []),
										],
										`MCP server · ${item.id}`,
										"mcp",
									),
							],
							[
								"remove",
								async () => {
									if (!(await this.askConfirm(`Remove MCP server ${item.id}?`))) return;
									const options = this.panelRequestOptions();
									const config = (await this.options.client.getConfiguration(options)) as {
										mcp?: { servers?: Record<string, unknown> };
									};
									if (!config.mcp?.servers?.[item.id]) {
										this.record("warning", `MCP server ${item.id} was already removed.`);
										await this.openInteractivePanel("mcp");
										return;
									}
									await this.options.client.updateConfiguration(
										{ mcp: { servers: { [item.id]: null } } },
										undefined,
										options,
									);
									if (options.signal?.aborted) return;
									await this.options.client.reloadCapabilities(this.session!.id, options);
									if (options.signal?.aborted) return;
									this.record("status", `MCP server ${item.id} removed.`);
									await this.openInteractivePanel("mcp");
								},
							],
						]);
						if (item.authSupported)
							actions.set("authenticate", async () => {
								if (!(await this.askConfirm(`Authenticate MCP server ${item.id}?`))) return;
								const options = this.panelRequestOptions();
								await this.options.client.authenticateMcpServer(item.id, options);
								if (options.signal?.aborted) return;
								this.record("status", `MCP server ${item.id} authenticated.`);
								await this.openInteractivePanel("mcp");
							});
						this.openMenuPanel(
							`MCP server · ${item.id}`,
							[
								{ id: "details", label: "View server details" },
								...(item.authSupported ? [{ id: "authenticate", label: "Authenticate" }] : []),
								{ id: "remove", label: "Remove server" },
								{ id: "cancel", label: "Back" },
							],
							new Map([...actions, ["cancel", () => this.openInteractivePanel("mcp")]]),
							"mcp",
						);
					}
				});
			}
			actions.set(PANEL_ACTION_RELOAD, async () => {
				const options = this.panelRequestOptions();
				await this.options.client.reloadCapabilities(this.session!.id, options);
				if (options.signal?.aborted) return;
				this.record("status", "Capabilities reloaded.");
				await this.openInteractivePanel(panel);
			});
			if (panel === "plugins")
				actions.set(PANEL_ACTION_INSTALL, () =>
					this.openFormPanel("Install plugin", "Source", "", async (source) => {
						const options = this.panelRequestOptions();
						const id = await this.options.client.installPlugin(source, options);
						if (options.signal?.aborted) return;
						await this.options.client.reloadCapabilities(this.session!.id, options);
						if (options.signal?.aborted) return;
						this.record("status", `Plugin ${id} installed.`);
						await this.openInteractivePanel("plugins");
					}),
				);
			if (panel === "mcp") actions.set(PANEL_ACTION_INSTALL, () => this.openMcpAddWizard([]));
			this.openMenuPanel(
				panelLabel(panel),
				menuItems.length ? menuItems : [{ id: "__empty", label: `No ${kind} capabilities.` }],
				actions,
			);
			return;
		}
		if (panel === "memory") {
			this.openMenuPanel(
				"Memory",
				[
					{ id: "status", label: "Memory status" },
					{ id: "query", label: "Search memory" },
					{ id: "recall", label: "Recall profile facts" },
					{ id: "remember", label: "Remember a fact" },
					{ id: "index", label: "Index workspace" },
				],
				new Map([
					[
						"status",
						async () => {
							if (this.session) {
								const options = this.panelRequestOptions();
								const status = await this.options.client.memoryStatus(this.session.id, options);
								if (options.signal?.aborted) return;
								this.showPanelResult(
									[
										`Knowledge entries: ${status.knowledgeEntries}`,
										`Repo files indexed: ${status.repoFilesIndexed}`,
										`Profile entries: ${status.profileEntries}`,
										`Pending learning: ${status.pendingLearning}`,
									],
									"Memory status",
									"memory",
								);
							}
						},
					],
					[
						"recall",
						() =>
							this.openFormPanel("Recall profile memory", "Query", "", async (value) => {
								if (!this.session) return;
								const options = this.panelRequestOptions();
								const entries = (await this.options.client.recallProfile(this.session.id, value, options)) as readonly {
									scope?: string;
									fact?: string;
								}[];
								if (options.signal?.aborted) return;
								this.showPanelResult(
									entries.length
										? entries.map((entry) => `${entry.scope ?? "profile"} · ${entry.fact ?? "(empty fact)"}`)
										: ["No matching profile memories."],
									"Profile memory",
									"memory",
								);
							}),
					],
					[
						"query",
						() =>
							this.openFormPanel("Search memory", "Query", "", async (value) => {
								if (this.session) {
									const options = this.panelRequestOptions();
									const answer = await this.options.client.queryMemory(this.session.id, value, options);
									if (options.signal?.aborted) return;
									const result = isObjectValue(answer) ? answer : undefined;
									const text =
										typeof answer === "string"
											? answer
											: typeof result?.["answer"] === "string"
												? result["answer"]
												: "";
									const sources = Array.isArray(result?.["sources"]) ? result["sources"] : [];
									this.showPanelResult(
										[
											text ? `Answer: ${text}` : "No relevant memory found.",
											...sources.map((source) => `Source: ${String(source)}`),
										],
										"Memory search",
										"memory",
									);
								}
							}),
					],
					[
						"remember",
						() =>
							this.openFormPanel("Remember fact", "Fact", "", async (value) => {
								if (this.session) {
									const options = this.panelRequestOptions();
									await this.options.client.rememberFact(this.session.id, value, undefined, options);
									if (options.signal?.aborted) return;
								}
								this.record("status", "Remembered.");
								this.closePanel();
							}),
					],
					[
						"index",
						async () => {
							if (this.session) {
								const options = this.panelRequestOptions();
								await this.options.client.indexRepository(this.session.id, options);
								if (options.signal?.aborted) return;
								this.record("status", "Workspace indexed.");
							}
							this.closePanel();
						},
					],
				]),
			);
			return;
		}
		if (panel === "learn") {
			await this.showLearnPanel(guard);
			return;
		}
		if (panel === "goal") {
			this.openMenuPanel(
				"Session goal",
				[
					{ id: "status", label: "View goal" },
					{ id: "create", label: "Create or replace goal" },
					{ id: "pause", label: "Pause goal" },
					{ id: "resume", label: "Resume goal" },
					{ id: "complete", label: "Complete goal" },
				],
				new Map([
					[
						"status",
						async () => {
							const options = this.panelRequestOptions();
							const goal = (await this.session?.getGoal(options)) as
								{ status?: string; objective?: string } | null | undefined;
							if (options.signal?.aborted) return;
							this.showPanelResult([
								goal ? `Goal (${goal.status ?? "unknown"}): ${goal.objective ?? "(no objective)"}` : "No active goal.",
							]);
						},
					],
					["create", () => this.openGoalCreateForm("")],
					[
						"pause",
						async () => {
							if (!this.session) return;
							const options = this.panelRequestOptions();
							const updated = await this.session.updateGoal({ status: "paused" }, options);
							if (options.signal?.aborted) return;
							if (updated === null) this.record("warning", "No active goal.");
							else this.record("status", "Goal paused.");
							this.closePanel();
						},
					],
					[
						"resume",
						async () => {
							if (!this.session) return;
							const options = this.panelRequestOptions();
							const updated = await this.session.updateGoal({ status: "active" }, options);
							if (options.signal?.aborted) return;
							if (updated === null) this.record("warning", "No goal to resume.");
							else this.record("status", "Goal resumed.");
							this.closePanel();
						},
					],
					[
						"complete",
						async () => {
							if (!this.session) return;
							const confirmed = await this.askConfirm("Complete the active goal?");
							if (!confirmed) {
								this.record("status", "Goal completion cancelled.");
								this.closePanel();
								return;
							}
							const completedOptions = this.panelRequestOptions();
							const completed = await this.session.updateGoal({ status: "completed" }, completedOptions);
							if (completedOptions.signal?.aborted) return;
							if (completed === null) this.record("warning", "No active goal.");
							else this.record("status", "Goal completed.");
							this.closePanel();
						},
					],
				]),
			);
			return;
		}
		if (panel === "plan") {
			this.openMenuPanel(
				"Coordinator plan",
				[
					{ id: "status", label: "Plan status" },
					{ id: "start", label: "Draft a plan" },
					{ id: "approve", label: "Approve current plan" },
					{ id: "revise", label: "Request revision" },
					{ id: "cancel", label: "Cancel plan turn" },
				],
				new Map([
					[
						"status",
						() =>
							this.showPanelResult(
								[
									`Coordinator turn: ${this.state.turnLive ? "running" : "idle"}`,
									`Pending interaction: ${this.pendingInteractions[0]?.kind ?? "none"}`,
									"Plan approval and revision are available as separate guided actions.",
								],
								"Coordinator plan status",
								"plan",
							),
					],
					[
						"start",
						() =>
							this.openFormPanel("Draft plan", "Objective", "", (value) =>
								this.sendPlanInstruction(`Draft an execution plan for: ${value}`),
							),
					],
					[
						"approve",
						() =>
							this.sendPlanInstruction(
								"The human approved the current coordinator plan. Dispatch approved steps to executor agents.",
							),
					],
					[
						"revise",
						() =>
							this.openFormPanel("Revise plan", "Feedback", "", (value) =>
								this.sendPlanInstruction(
									`Revise the current execution plan using this feedback: ${value}. Keep execution gated until approval.`,
								),
							),
					],
					[
						"cancel",
						async () => {
							if (!this.session || !this.state.turnLive) {
								this.record("warning", "No plan turn is running.");
								this.closePanel();
								return;
							}
							const options = this.panelRequestOptions();
							await this.session.cancel(undefined, options);
							if (options.signal?.aborted) return;
							// A successful cancellation is an authoritative local boundary even
							// when a provider/event transport does not emit turn.interrupted.
							this.dispatch({ type: "turn", value: false });
							this.record("status", "Plan turn cancelled.");
							this.closePanel();
						},
					],
				]),
			);
			return;
		}
		if (panel === "delete") {
			const options = this.panelRequestOptions();
			const sessions = await this.options.client.listSessions({}, options);
			if (options.signal?.aborted || this.panelGuardStale(guard)) return;
			const actions = new Map<string, () => Promise<void> | void>();
			const items = sessions.map((item) => ({
				id: item.sessionId,
				label: shortId(item.sessionId),
				detail: `${item.sessionId} · ${item.title ?? item.cwd}`,
			}));
			for (const item of sessions)
				actions.set(item.sessionId, async () => {
					if (await this.askConfirm(`Delete session ${shortId(item.sessionId)}?`)) {
						const deletingCurrent = item.sessionId === this.session?.id;
						const options = this.panelRequestOptions();
						await this.options.client.deleteSession(item.sessionId, options);
						if (options.signal?.aborted && !deletingCurrent) return;
						this.closePanel();
						if (!deletingCurrent) {
							this.record("status", `Session ${shortId(item.sessionId)} deleted.`);
							return;
						}
						// A deleted current session must never remain as a live SDK handle: every
						// session-owned panel would otherwise fail later with "Unknown session".
						// This recovery finishes even when the panel action was cancelled —
						// the delete already committed and half-done state is worse.
						this.eventGeneration += 1;
						await this.eventStream.stop();
						await this.eventTask?.catch(() => {});
						this.eventTask = undefined;
						this.session = undefined;
						this.clearLiveReconciliation();
						this.dispatch({ type: "reset-session" });
						const replacement = await this.options.client.createSession({ cwd: this.options.cwd });
						await this.switchSession(replacement);
						this.record("status", `Session ${shortId(item.sessionId)} deleted; started a new session.`);
					}
				});
			this.openMenuPanel("Delete session", items.length ? items : [{ id: "__empty", label: "No sessions" }], actions);
			return;
		}
		if (panel === "rename") {
			this.openFormPanel("Rename session", "New title", "", async (value) => {
				if (!this.session) return;
				const options = this.panelRequestOptions();
				await this.options.client.renameSession(this.session.id, value, options);
				if (options.signal?.aborted) return;
				this.record("status", `Session renamed to “${value}”.`);
				this.closePanel();
			});
			return;
		}
		if (panel === "archive") {
			this.openMenuPanel(
				"Session archive",
				[
					{ id: "archive", label: "Archive and start a new session", detail: "Keep this session in history" },
					{ id: "restore", label: "Unarchive this session", detail: "Keep working in the current session" },
				],
				new Map([
					[
						"archive",
						async () => {
							if (!this.session) return;
							const archivedId = this.session.id;
							const options = this.panelRequestOptions();
							await this.options.client.archiveSession(archivedId, true, options);
							if (options.signal?.aborted) return;
							this.closePanel();
							const replacement = await this.options.client.createSession({ cwd: this.options.cwd });
							await this.switchSession(replacement);
							this.record("status", `Session ${shortId(archivedId)} archived; started a new session.`);
						},
					],
					[
						"restore",
						async () => {
							if (!this.session) return;
							const options = this.panelRequestOptions();
							await this.options.client.archiveSession(this.session.id, false, options);
							if (options.signal?.aborted) return;
							this.record("status", "Session unarchived.");
							this.closePanel();
						},
					],
				]),
			);
			return;
		}
		if (panel === "trust") {
			await this.openTrustPanel(guard);
			return;
		}
		this.openMenuPanel(
			panelLabel(panel),
			[{ id: "open", label: "Open panel" }],
			new Map([["open", () => this.record("status", `${panelLabel(panel)} is ready for interactive actions.`)]]),
		);
	}
	private async openSettingsPanel(guard?: PanelOperationGuard): Promise<void> {
		const config = (await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<
			string,
			unknown
		>;
		if (this.panelGuardStale(guard)) return;
		const items: PanelMenuItem[] = SETTINGS_SECTIONS.map((section) => ({
			id: section.id,
			label: section.title,
			detail: settingsSectionSummary(section, config),
		}));
		const actions = new Map<string, () => Promise<void> | void>();
		for (const section of SETTINGS_SECTIONS)
			actions.set(section.id, () => this.openSettingsSection(section, SETTINGS_SECTIONS.indexOf(section)));
		items.push(
			{ id: "paths", label: "Configuration file locations", detail: "Show user and workspace settings files" },
			{ id: "model", label: "Model routes", detail: "Assign a provider/model to a graph role" },
			{ id: "graph", label: "Agent profiles", detail: "Edit worker policy and limits" },
			{ id: "auth", label: "Provider credentials", detail: "Add, inspect or remove API/OAuth access" },
			{ id: "trust", label: "Workspace trust", detail: "Review security-sensitive project changes" },
		);
		actions.set("paths", async () => {
			const [userPath, projectPath] = await Promise.all([
				this.options.client.configurationPath("user"),
				this.options.client.configurationPath("project"),
			]);
			this.showPanelResult(
				[`User settings · ${userPath}`, `Workspace settings · ${projectPath}`],
				"Configuration files",
				"config",
			);
		});
		actions.set("model", () => this.openInteractivePanel("model"));
		actions.set("graph", () => this.openInteractivePanel("graph"));
		actions.set("auth", () => this.openInteractivePanel("auth"));
		actions.set("trust", () => this.openInteractivePanel("trust"));
		this.openMenuPanel("Settings", items, actions);
	}
	private async openSettingsSection(section: SettingsSection, selected = 0): Promise<void> {
		const config = (await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<
			string,
			unknown
		>;
		const items: PanelMenuItem[] = section.fields.map((field) => ({
			id: field.path,
			label: `${field.label}: ${formatSettingValue(field, readSettingValue(config, field.path))}`,
			detail: field.hint,
		}));
		const actions = new Map<string, () => Promise<void> | void>();
		for (const field of section.fields)
			actions.set(field.path, () => this.editSettingField(section, field, readSettingValue(config, field.path)));
		items.push({ id: "__note", label: section.note ?? SETTINGS_NEW_SESSION_NOTE });
		this.openMenuPanel(`Settings · ${section.title}`, items, actions, "config", selected);
	}
	private async editSettingField(section: SettingsSection, field: SettingField, current: unknown): Promise<void> {
		if (field.type === "boolean") {
			const next = current !== true;
			await this.writeSettingValue(field, next);
			await this.openSettingsSection(section, section.fields.indexOf(field));
			return;
		}
		if (field.type === "enum") {
			const values = field.enumValues ?? [];
			this.openMenuPanel(
				`Settings · ${field.label}`,
				values.map((value) => ({
					id: value,
					label: value,
					detail: value === current ? "current" : undefined,
				})),
				new Map(
					values.map((value) => [
						value,
						async () => {
							await this.writeSettingValue(field, value);
							await this.openSettingsSection(section, section.fields.indexOf(field));
						},
					]),
				),
				undefined,
				Math.max(0, values.indexOf(String(current))),
				() => this.openSettingsSection(section, section.fields.indexOf(field)),
			);
			return;
		}
		if (field.type === "stringList") {
			await this.openSettingsListEditor(section, field);
			return;
		}
		this.openFormPanel(
			`Settings · ${field.label}`,
			field.hint ? `Value (${field.hint})` : "Value",
			current === undefined || current === null ? "" : String(current),
			async (raw) => {
				const parsed = parseSettingInput(field, raw);
				if (!parsed.ok) throw new Error(parsed.message);
				await this.writeSettingValue(field, parsed.value);
				await this.openSettingsSection(section, section.fields.indexOf(field));
			},
			false,
			undefined,
			() => this.openSettingsSection(section, section.fields.indexOf(field)),
		);
	}
	private async openSettingsListEditor(section: SettingsSection, field: SettingField): Promise<void> {
		const config = (await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<
			string,
			unknown
		>;
		const value = readSettingValue(config, field.path);
		const entries = Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
		const items: PanelMenuItem[] = entries.map((entry, index) => ({
			id: `entry-${index}`,
			label: entry,
			detail: "Enter to remove",
		}));
		if (!entries.length) items.push({ id: "__empty", label: "No entries" });
		items.push({ id: "add", label: "Add entry…", detail: field.hint });
		const actions = new Map<string, () => Promise<void> | void>();
		entries.forEach((entry, index) =>
			actions.set(`entry-${index}`, async () => {
				const confirmed = await this.askConfirm(`Remove “${entry}” from ${field.label}?`);
				if (confirmed)
					await this.writeSettingValue(
						field,
						entries.filter((_, other) => other !== index),
						`Removed ${entry} from ${field.path}.`,
					);
				await this.openSettingsListEditor(section, field);
			}),
		);
		actions.set("add", () =>
			this.openFormPanel(
				`Settings · ${field.label}`,
				"New entry",
				"",
				async (raw) => {
					const parsed = parseSettingInput(field, raw);
					if (!parsed.ok) throw new Error(parsed.message);
					await this.writeSettingValue(field, [...entries, parsed.value], `Added ${parsed.value} to ${field.path}.`);
					await this.openSettingsListEditor(section, field);
				},
				false,
				undefined,
				() => this.openSettingsListEditor(section, field),
			),
		);
		this.openMenuPanel(`Settings · ${field.label}`, items, actions, undefined, 0, () =>
			this.openSettingsSection(section, section.fields.indexOf(field)),
		);
	}
	/** Persist one field through the same validated write path as `/config set`. */
	private async writeSettingValue(field: SettingField, value: unknown, message?: string): Promise<void> {
		await this.panelRequest(this.options.client.updateConfiguration, [buildConfigPatch(field.path, value), "user"]);
		await this.refreshRuntimeModel();
		this.record(
			"status",
			message ?? `Set ${field.path} to ${typeof value === "string" ? value : JSON.stringify(value)}.`,
		);
	}
	private async openUndoPanel(guard?: PanelOperationGuard): Promise<void> {
		if (!this.session) {
			this.record("warning", "/undo requires an active session.");
			return;
		}
		const options = this.panelRequestOptions();
		const entries = await this.session.timeline(options);
		if (options.signal?.aborted) return;
		if (this.panelGuardStale(guard)) return;
		const restorable = entries.filter((entry) => entry.kind !== "session");
		const items: PanelMenuItem[] = restorable.length
			? restorable.map((entry) => ({
					id: String(entry.sequence),
					label: `#${entry.sequence} · ${entry.kind} · ${entry.label}`,
					detail: `${entry.actorId ? `actor ${shortId(entry.actorId)} · ` : ""}${entry.hasExternalEffects ? "external effect recorded" : "Kageko state"}`,
				}))
			: [
					{
						id: "empty",
						label: "No restorable session history",
						detail: "This session has no durable timeline entries",
					},
				];
		const actions = new Map<string, () => Promise<void> | void>();
		for (const entry of restorable)
			actions.set(String(entry.sequence), async () => {
				const warning = entry.hasExternalEffects
					? "This state includes external tool or process effects. Restoring changes Kageko state only; external effects remain. Continue?"
					: "Restore Kageko to this exact timeline state? Running session work will be stopped first.";
				if (!(await this.askConfirm(warning))) return;
				const sessionId = this.session!.id;
				const options = this.panelRequestOptions();
				const restored = await this.session!.restore(entry.sequence, entry.timelineId, options);
				if (options.signal?.aborted) return;
				await this.switchSession(this.options.client.session(sessionId));
				this.record(
					"status",
					`Restored to timeline state #${restored.restoredToSequence}.${restored.externalEffectsRetained ? ` ${restored.externalEffectsRetained} later external effect${restored.externalEffectsRetained === 1 ? "" : "s"} remain recorded.` : ""}`,
				);
				// The restored session rewrote the timeline this menu still displays;
				// close it so a stale entry can never be applied twice.
				this.closePanel();
			});
		this.openMenuPanel("Session timeline", items, actions);
	}
	private openMenuPanel(
		title: string,
		items: readonly PanelMenuItem[],
		actions: Map<string, () => Promise<void> | void>,
		parent?: InteractivePanelName,
		selected = 0,
		returnAction?: () => Promise<void> | void,
	): void {
		this.panelAbort?.abort(new Error("Panel replaced."));
		this.panelAbort = undefined;
		// An action may asynchronously replace its originating menu (for example,
		// Activity → history).  The replacement is already interactive, so it must
		// not inherit the originating menu's busy lock and swallow the first key.
		this.panelActionBusy = false;
		this.panelActionError = undefined;
		this.panelActions = actions;
		this.panelSubmit = undefined;
		this.panelReturn = parent;
		this.panelReturnAction = returnAction;
		this.panel = {
			kind: "menu",
			title,
			items,
			query: "",
			selected: Math.max(0, Math.min(selected, Math.max(0, items.length - 1))),
			parent,
		};
		this.normalizeMenuSelection(this.panel);
		this.showModal("panel");
		this.render();
	}
	private openFormPanel(
		title: string,
		label: string,
		value: string,
		submit: (value: string) => Promise<void> | void,
		masked = false,
		parent?: InteractivePanelName,
		returnAction?: () => Promise<void> | void,
		allowEmpty = false,
		options: FormPanelOptions = {},
	): void {
		this.panelAbort?.abort(new Error("Panel replaced."));
		this.panelAbort = undefined;
		this.panelActionBusy = false;
		this.panelActionError = undefined;
		this.panelActions.clear();
		if (!value && this.panelCommandPrefills.length) value = this.panelCommandPrefills.shift()!;
		this.panelSubmit = async (next) => {
			if (!next.trim() && !allowEmpty) return;
			await submit(next.trim());
		};
		this.panelReturn = parent;
		this.panelReturnAction = returnAction;
		this.panel = {
			kind: "form",
			title,
			label,
			value,
			cursorIndex: graphemeCount(value),
			masked,
			placeholder: options.placeholder,
			hint: options.hint,
			parent,
		};
		this.showModal("panel");
		this.render();
	}
	private async runPanelLoad(
		title: string,
		label: string,
		operation: (guard: { readonly operationId: number; readonly signal: AbortSignal }) => Promise<void>,
	): Promise<void> {
		this.panelAbort?.abort(new Error("Panel operation replaced."));
		const abort = new AbortController();
		const operationId = ++this.panelOperationId;
		const loadingPanel: MenuPanelState = {
			kind: "menu",
			title,
			items: [{ id: "loading", label }],
			query: "",
			selected: 0,
		};
		this.panelAbort = abort;
		this.panelActionBusy = true;
		this.panelActionError = undefined;
		this.panelActions.clear();
		this.panelSubmit = undefined;
		this.panelReturn = undefined;
		this.panelReturnAction = undefined;
		this.panel = loadingPanel;
		this.showModal("panel");
		this.render();
		try {
			await operation({ operationId, signal: abort.signal });
			if (this.panel === loadingPanel && this.panelOperationId === operationId) {
				this.panelActionError = "The requested panel did not return any data.";
			}
		} catch (error) {
			if (abort.signal.aborted) return;
			if (this.panel !== loadingPanel || this.panelOperationId !== operationId) return;
			this.panelActionError = messageOf(error);
		} finally {
			if (this.panel === loadingPanel && this.panelOperationId === operationId) {
				if (this.panelAbort === abort) this.panelAbort = undefined;
				this.panelActionBusy = false;
				this.render();
			} else if (this.panelActionBusy) {
				this.panelActionBusy = false;
			}
		}
	}
	private async collectModelRoutes(
		config: Record<string, unknown>,
		signal?: AbortSignal,
	): Promise<readonly ModelPanelState["routes"][number][]> {
		const candidates: Array<Omit<ModelPanelState["routes"][number], "ready">> = [];
		const add = (provider: unknown, authMode: unknown, label?: string, baseUrl?: unknown): void => {
			if (typeof provider !== "string" || (authMode !== "api" && authMode !== "oauth")) return;
			const existing = candidates.find((route) => route.provider === provider && route.authMode === authMode);
			if (existing) {
				if (typeof baseUrl === "string" && baseUrl.trim()) existing.baseUrl = baseUrl;
				return;
			}
			candidates.push({
				provider,
				authMode,
				label: label ?? provider,
				...(typeof baseUrl === "string" && baseUrl.trim() ? { baseUrl } : {}),
			});
		};
		for (const entry of SETUP_PROVIDERS) add(entry.id, entry.authMode, entry.label);
		const model = isObjectValue(config["model"]) ? config["model"] : {};
		// A custom route can be fully usable through KAGEKO_API_KEY/baseUrl while
		// authMode remains implicit.  Enrich every matching catalog route before
		// the stricter provider+authMode insertion below.
		if (typeof model["provider"] === "string" && typeof model["baseUrl"] === "string")
			for (const route of candidates) if (route.provider === model["provider"]) route.baseUrl = model["baseUrl"];
		add(model["provider"], model["authMode"], `${String(model["provider"] ?? "current")} (current)`, model["baseUrl"]);
		for (const target of agentTargets(config)) {
			const value = agentTargetConfig(config, target);
			if (typeof value["provider"] === "string" && typeof value["baseUrl"] === "string")
				for (const route of candidates) if (route.provider === value["provider"]) route.baseUrl = value["baseUrl"];
			add(
				value["provider"],
				value["authMode"],
				`${String(value["provider"] ?? target.label)} (${target.label})`,
				value["baseUrl"],
			);
		}
		const routes = await Promise.all(
			candidates.map(async (route) => {
				if (typeof this.options.client.hasCredential !== "function") return { ...route, ready: true };
				try {
					const ready = await this.options.client.hasCredential(route.provider, route.authMode, { signal });
					return { ...route, ready };
				} catch (error) {
					if (signal?.aborted) throw signal.reason ?? error;
					return { ...route, ready: false };
				}
			}),
		);
		routes.push({ provider: "__setup__", authMode: "api", ready: true, label: "Add provider…" });
		return routes;
	}
	private async openModelPanel(
		target?: AgentTarget,
		returnToGraph = false,
		guard?: PanelOperationGuard,
	): Promise<void> {
		if (this.panelGuardStale(guard)) return;
		const signal = guard?.signal ?? this.panelAbort?.signal;
		const config = (await this.options.client.getConfiguration({ signal })) as unknown as Record<string, unknown>;
		if (this.panelGuardStale(guard)) return;
		const targets = agentTargets(config);
		const targetIndex = target
			? Math.max(
					0,
					targets.findIndex((candidate) => candidate.id === target.id),
				)
			: 0;
		const routes = await this.collectModelRoutes(config, signal);
		if (this.panelGuardStale(guard)) return;
		this.panelReturn = returnToGraph ? "graph" : undefined;
		this.panelReturnAction = undefined;
		this.panelAbort?.abort(new Error("Panel replaced."));
		this.panelAbort = undefined;
		this.panelActionError = undefined;
		this.panelActions.clear();
		this.panelSubmit = undefined;
		this.panel = {
			kind: "model",
			step: target ? "route" : "role",
			targets,
			targetIndex,
			routes,
			routeIndex: Math.max(
				0,
				routes.findIndex((route) => route.ready),
			),
			models: [],
			modelQuery: "",
			modelIndex: 0,
			reasoningIndex: 0,
			confirmIndex: 0,
			busy: false,
		};
		this.showModal("panel");
		this.ensureSelectedModalVisible();
		this.render();
	}
	private async openGraphPanel(guard?: PanelOperationGuard): Promise<void> {
		if (this.panelGuardStale(guard)) return;
		const signal = guard?.signal ?? this.panelAbort?.signal;
		const config = (await this.options.client.getConfiguration({ signal })) as unknown as Record<string, unknown>;
		if (this.panelGuardStale(guard)) return;
		const targets = agentTargets(config);
		const items: PanelMenuItem[] = targets.map((target) => ({
			id: target.id,
			label: target.label,
			detail: target.detail,
		}));
		items.push({ id: "add", label: "Add subagent profile", detail: "Create a named reusable worker" });
		const actions = new Map<string, () => Promise<void> | void>();
		for (const target of targets) actions.set(target.id, () => this.openAgentProfilePanel(target, config));
		actions.set("add", () => this.openNewSubagentProfileForm());
		this.openMenuPanel("Agent graph and worker profiles", items, actions);
	}
	private openAgentProfilePanel(target: AgentTarget, config: Record<string, unknown>): void {
		const fields: GraphField[] = [
			...(target.kind === "subagent" ? (["description", "whenToUse"] as const) : []),
			"route",
			"baseUrl",
			"contextLength",
			"maxContextSize",
			"maxOutputTokens",
			"maxSteps",
			...(target.kind === "learner" ? (["runTimeoutMs", "maxQueuedRuns"] as const) : []),
			...(target.kind === "subagent" ? (["timeoutMs"] as const) : []),
			"systemPrompt",
			"permissionProfile",
			"interactionMode",
			"tools",
			...(target.builtin
				? (["reset"] as const)
				: target.kind === "subagent" && !target.legacyExecutor
					? (["remove"] as const)
					: []),
		];
		this.panelActions.clear();
		this.panelSubmit = undefined;
		this.panelReturn = "graph";
		this.panelReturnAction = undefined;
		this.panel = {
			kind: "graph",
			target,
			fieldIndex: 0,
			fields,
			config: { [target.id]: agentTargetConfig(config, target) },
			busy: false,
		};
		this.showModal("panel");
		this.render();
	}
	private async reopenAgentProfilePanel(target: AgentTarget): Promise<void> {
		const config = (await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<
			string,
			unknown
		>;
		this.openAgentProfilePanel(target, config);
	}
	private openGraphChoicePanel(
		target: AgentTarget,
		field: "permissionProfile" | "interactionMode",
		query = "",
	): void {
		const options =
			field === "permissionProfile"
				? [
						{ value: "manual", detail: "Ask before protected actions" },
						{ value: "workspace", detail: "Keep actions within workspace policy" },
						{ value: "unrestricted", detail: "Broad access, still capped by the parent policy" },
					]
				: [
						{ value: "interactive", detail: "Can pause for approvals and user input" },
						{ value: "unattended", detail: "Runs without waiting for user input" },
					];
		const current = this.panel?.kind === "graph" ? this.panel.config[target.id]?.[field] : undefined;
		const actions = new Map<string, () => Promise<void>>();
		const items = options.map(({ value, detail }) => ({
			id: value,
			label: value,
			detail: value === current ? "Current · " + detail : detail,
		}));
		for (const { value } of options)
			actions.set(value, async () => {
				await this.panelRequest(this.options.client.updateConfiguration, [
					agentTargetPatch(target, { [field]: value }),
					"user",
				]);
				await this.refreshRuntimeModel();
				this.record("status", target.label + " " + graphFieldLabel(field) + " set to " + value + ".");
				await this.reopenAgentProfilePanel(target);
			});
		const returnAction = () => this.reopenAgentProfilePanel(target);
		this.openMenuPanel(
			"Worker · " + graphFieldLabel(field),
			items,
			actions,
			undefined,
			Math.max(
				0,
				options.findIndex((option) => option.value === current),
			),
			returnAction,
		);
		if (query && this.panel?.kind === "menu") {
			this.panel.query = query;
			this.normalizeMenuSelection(this.panel);
			this.render();
		}
	}
	private async openGraphToolsPicker(target: AgentTarget, configuredValue: unknown, query = ""): Promise<void> {
		const graphPanel = this.panel;
		if (!graphPanel || graphPanel.kind !== "graph") return;
		const returnAction = () => this.reopenAgentProfilePanel(target);
		if (!this.session) {
			this.openMenuPanel(
				"Worker tools · " + target.label,
				[
					{
						id: "no-session",
						label: "Open or resume a session to load tools",
						detail: "The picker uses the active session's registered tools, including MCP and plugin tools.",
					},
					{ id: "back", label: "Back to worker profile" },
				],
				new Map([["back", returnAction]]),
				undefined,
				1,
				returnAction,
			);
			return;
		}
		await this.runGraphPanelOperation(graphPanel, "Loading session tools…", async (operationId, signal) => {
			const tools = await this.panelRequest(this.options.client.listTools, [this.session!.id], signal);
			if (this.panel !== graphPanel || this.panelOperationId !== operationId) return;
			this.openGraphToolsChecklist(target, configuredValue, tools, query);
		});
	}
	private openGraphToolsChecklist(
		target: AgentTarget,
		configuredValue: unknown,
		availableTools: readonly {
			readonly name: string;
			readonly provenance: { readonly kind: string; readonly ownerId: string };
		}[],
		initialQuery = "",
	): void {
		const availableNames = availableTools.map((tool) => tool.name);
		const configuredNames = Array.isArray(configuredValue)
			? configuredValue.filter((name): name is string => typeof name === "string")
			: undefined;
		const selectedNames = new Set(configuredNames ?? availableNames);
		const toolByName = new Map(availableTools.map((tool) => [tool.name, tool]));
		const names = [...new Set([...availableNames, ...(configuredNames ?? [])])];
		const returnAction = () => this.reopenAgentProfilePanel(target);
		const renderChecklist = (query = "", selectedIndex = 0): void => {
			const items: PanelMenuItem[] = [
				{
					id: "worker-tools:summary",
					label: selectedNames.size + " tools selected",
					detail:
						configuredNames === undefined
							? "This profile currently inherits every session tool."
							: "Selection is saved to this worker profile.",
				},
				...names.map((name) => {
					const tool = toolByName.get(name);
					return {
						id: "worker-tools:tool:" + name,
						label: (selectedNames.has(name) ? "☑" : "☐") + "  " + name,
						detail: tool
							? tool.provenance.kind + " · " + tool.provenance.ownerId
							: "Not available in this session · uncheck to remove",
					};
				}),
				{ id: "worker-tools:all", label: "Select all available tools" },
				{ id: "worker-tools:clear", label: "Clear selection" },
				{ id: "worker-tools:save", label: "Save selection · " + selectedNames.size },
				{ id: "worker-tools:cancel", label: "Cancel" },
			];
			const actions = new Map<string, () => Promise<void> | void>();
			for (const name of names)
				actions.set("worker-tools:tool:" + name, () => {
					const currentMenu = this.panel;
					const nextQuery = currentMenu?.kind === "menu" ? currentMenu.query : query;
					const nextIndex = currentMenu?.kind === "menu" ? currentMenu.selected : selectedIndex;
					if (selectedNames.has(name)) selectedNames.delete(name);
					else selectedNames.add(name);
					renderChecklist(nextQuery, nextIndex);
				});
			actions.set("worker-tools:all", () => {
				const currentMenu = this.panel;
				const nextQuery = currentMenu?.kind === "menu" ? currentMenu.query : query;
				const nextIndex = currentMenu?.kind === "menu" ? currentMenu.selected : selectedIndex;
				selectedNames.clear();
				for (const name of availableNames) selectedNames.add(name);
				renderChecklist(nextQuery, nextIndex);
			});
			actions.set("worker-tools:clear", () => {
				const currentMenu = this.panel;
				const nextQuery = currentMenu?.kind === "menu" ? currentMenu.query : query;
				const nextIndex = currentMenu?.kind === "menu" ? currentMenu.selected : selectedIndex;
				selectedNames.clear();
				renderChecklist(nextQuery, nextIndex);
			});
			actions.set("worker-tools:save", async () => {
				await this.panelRequest(this.options.client.updateConfiguration, [
					agentTargetPatch(target, { tools: [...selectedNames].sort((left, right) => left.localeCompare(right)) }),
					"user",
				]);
				await this.refreshRuntimeModel();
				this.record("status", target.label + " tool access updated (" + selectedNames.size + " selected).");
				await this.reopenAgentProfilePanel(target);
			});
			actions.set("worker-tools:cancel", returnAction);
			this.openMenuPanel("Worker tools · " + target.label, items, actions, undefined, selectedIndex, returnAction);
			if (this.panel?.kind === "menu") {
				this.panel.query = query;
				this.normalizeMenuSelection(this.panel);
				this.render();
			}
		};
		renderChecklist(initialQuery);
	}
	private openNewSubagentProfileForm(): void {
		this.openFormPanel(
			"Add subagent profile",
			"Profile id",
			"",
			async (profileId) => {
				if (!isSubagentProfileId(profileId)) {
					this.record(
						"warning",
						"Profile id must start with a letter, use only letters, numbers, _ or -, and cannot use a reserved system name.",
					);
					return;
				}
				const config = (await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<
					string,
					unknown
				>;
				if (customSubagentTargets(config).some((target) => target.profileId === profileId)) {
					this.record("warning", `Subagent profile ${profileId} already exists.`);
					return;
				}
				await this.panelRequest(this.options.client.updateConfiguration, [
					{
						agentGraph: {
							subagents: {
								[profileId]: {
									description: "Custom worker profile.",
									whenToUse: "Configure this custom worker before delegating work to it.",
								},
							},
						},
					},
					"user",
				]);
				this.record("status", `Subagent profile ${profileId} created.`);
				this.openAgentProfilePanel(
					subagentTarget(profileId),
					(await this.panelRequest(this.options.client.getConfiguration, [])) as unknown as Record<string, unknown>,
				);
			},
			false,
			"graph",
			undefined,
			false,
			{
				placeholder: "e.g. security-review",
				hint: "Starts with a letter; use letters, numbers, underscores, or hyphens.",
			},
		);
	}
	private async openAuthPanel(guard?: PanelOperationGuard): Promise<void> {
		if (this.panelGuardStale(guard)) return;
		const items: PanelMenuItem[] = [];
		const actions = new Map<string, () => Promise<void> | void>();
		const signal = guard?.signal ?? this.panelAbort?.signal;
		const states = await Promise.all(
			SETUP_PROVIDERS.map(async (entry) => {
				const [apiResult, oauthResult] = await Promise.allSettled([
					this.options.client.hasCredential(entry.id, "api", { signal }),
					this.options.client.hasCredential(entry.id, "oauth", { signal }),
				]);
				const cached = this.credentialReadiness.get(entry.id);
				return {
					entry,
					api: apiResult.status === "fulfilled" ? apiResult.value : cached?.api,
					oauth: oauthResult.status === "fulfilled" ? oauthResult.value : cached?.oauth,
				};
			}),
		);
		if (this.panelGuardStale(guard)) return;
		for (const { entry, api, oauth } of states) {
			const routeId = `${entry.id}:${entry.authMode}`;
			const readinessLabel = (value: boolean | undefined, label: string) =>
				value === true ? `${label} ready` : value === false ? `${label} —` : `${label} status unavailable`;
			items.push({
				id: routeId,
				label: entry.label,
				detail: `${readinessLabel(api, "API")}${entry.authMode === "oauth" || oauth ? ` · ${readinessLabel(oauth, "OAuth")}` : ""}`,
			});
			actions.set(routeId, () =>
				this.openAuthRoutePanel(entry.id, entry.label, api === true, oauth === true, entry.authMode),
			);
		}
		items.push({ id: "setup", label: "Add another provider…", detail: "Open the guided provider setup" });
		if (this.panelGuardStale(guard)) return;
		actions.set("setup", async () => {
			this.closePanel();
			await this.runSetupWizard();
		});
		this.openMenuPanel("Provider credentials", items, actions);
	}
	private openAuthRoutePanel(
		provider: string,
		label: string,
		api: boolean,
		oauth: boolean,
		preferred: "api" | "oauth",
	): void {
		const oauthRouteExists = SETUP_PROVIDERS.some((entry) => entry.id === provider && entry.authMode === "oauth");
		const items: PanelMenuItem[] = [
			{
				id: "api",
				label: api ? "API key configured" : "Add API key",
				detail: "Enter a key without exposing it in the command line",
			},
			...(oauthRouteExists
				? [
						{
							id: "oauth",
							label: oauth ? "OAuth connected" : "Connect OAuth",
							detail: "Open the provider verification flow",
						},
					]
				: []),
			{ id: "remove", label: "Remove credential", detail: "Choose API or OAuth next" },
		];
		const actions = new Map<string, () => Promise<void> | void>([
			[
				"api",
				() =>
					this.openFormPanel(
						`API key · ${label}`,
						"API key",
						"",
						async (value) => {
							await this.panelRequest(this.options.client.setApiKey, [provider, value]);
							const readiness = this.credentialReadiness.get(provider) ?? { api: false, oauth: false };
							this.credentialReadiness.set(provider, { ...readiness, api: true });
							this.record("status", `API credential saved for ${label}.`);
							await this.openAuthPanel();
						},
						true,
						"auth",
					),
			],
		]);
		if (oauthRouteExists)
			actions.set("oauth", async () => {
				if (typeof this.options.client.loginOAuth !== "function") {
					this.record("warning", "OAuth is unavailable in this host.");
					return;
				}
				// The wizard records its own outcome (connected vs cancelled); a
				// cancelled login must never be reported here as "OAuth connected".
				const connected = await this.runSetupWizard(provider, "oauth", true);
				if (connected) {
					const readiness = this.credentialReadiness.get(provider) ?? { api: false, oauth: false };
					this.credentialReadiness.set(provider, { ...readiness, oauth: true });
				}
				await this.openAuthPanel();
			});
		actions.set("remove", () =>
			this.openMenuPanel(
				`Remove credential · ${label}`,
				[
					{ id: "api", label: "Remove API key" },
					...(oauthRouteExists ? [{ id: "oauth", label: "Disconnect OAuth" }] : []),
					{ id: "cancel", label: "Cancel" },
				],
				new Map([
					[
						"api",
						async () => {
							const confirmed = await this.askConfirm(`Remove the API credential for ${label}?`);
							if (confirmed) {
								await this.panelRequest(this.options.client.removeCredential, [provider]);
								const readiness = this.credentialReadiness.get(provider) ?? { api: false, oauth: false };
								this.credentialReadiness.set(provider, { ...readiness, api: false });
								this.record("status", `API credential removed for ${label}.`);
								await this.openAuthPanel();
							} else this.record("status", `API credential removal cancelled for ${label}.`);
						},
					],
					[
						"oauth",
						async () => {
							if (
								typeof this.options.client.logoutOAuth === "function" &&
								(await this.askConfirm(`Disconnect OAuth for ${label}?`))
							) {
								await this.panelRequest(this.options.client.logoutOAuth, [provider]);
								const readiness = this.credentialReadiness.get(provider) ?? { api: false, oauth: false };
								this.credentialReadiness.set(provider, { ...readiness, oauth: false });
								this.record("status", `OAuth disconnected for ${label}.`);
								await this.openAuthPanel();
							}
						},
					],
					["cancel", () => this.openAuthRoutePanel(provider, label, api, oauth, preferred)],
				]),
			),
		);
		this.openMenuPanel(`Credentials · ${label}`, items, actions, "auth");
	}
	private async openTrustPanel(guard?: PanelOperationGuard): Promise<void> {
		const status = await this.options.client.inspectWorkspaceTrust(this.panelRequestOptions()).catch((error) => {
			if (this.panelAbort?.signal.aborted) throw this.panelAbort.signal.reason ?? error;
			return undefined;
		});
		if (this.panelGuardStale(guard)) return;
		this.openMenuPanel(
			"Workspace trust",
			[
				{
					id: "status",
					label: `Trust status · ${status?.trusted ? "Trusted" : "Not trusted"}`,
					detail: status?.workspace ?? "Unavailable",
				},
				{ id: "grant", label: "Trust this workspace" },
				{ id: "revoke", label: "Revoke trust" },
			],
			new Map([
				[
					"status",
					() =>
						this.showPanelResult(
							[
								`State: ${status?.trusted ? "trusted" : "not trusted"}`,
								`Workspace: ${status?.workspace ?? "Unavailable"}`,
								...(status?.reason ? [`Reason: ${status.reason}`] : []),
							],
							"Workspace trust status",
							"trust",
						),
				],
				[
					"grant",
					async () => {
						await this.panelRequest(this.options.client.grantWorkspaceTrust, []);
						this.record("status", "Workspace trusted.");
						await this.openTrustPanel();
					},
				],
				[
					"revoke",
					async () => {
						const confirmed = await this.askConfirm("Revoke trust for this workspace?");
						if (confirmed) {
							await this.panelRequest(this.options.client.revokeWorkspaceTrust, []);
							this.record("status", "Workspace trust revoked.");
							await this.openTrustPanel();
						} else this.record("status", "Workspace trust revocation cancelled.");
					},
				],
			]),
		);
	}
	private async handlePanelKey(key: KeyInput): Promise<void> {
		if (!this.panel) {
			this.closePanel();
			return;
		}
		if (key.name === "pageup" || key.name === "pagedown") {
			this.scrollModal(key.name === "pageup" ? -8 : 8);
			this.render();
			return;
		}
		if (this.panel.kind === "model") {
			await this.handleModelPanelKey(key);
			return;
		}
		if (this.panel.kind === "graph") {
			await this.handleGraphPanelKey(key);
			return;
		}
		if (this.panelActionBusy && key.name === "escape") {
			this.panelAbort?.abort(new Error("Panel operation cancelled by user."));
			this.panelAbort = undefined;
			this.panelOperationId += 1;
			this.panelActionBusy = false;
			this.panelActionError = "Cancelled.";
			this.render();
			return;
		}
		if (this.panel.kind === "form") {
			if (key.name === "escape") {
				this.returnFromPanel();
				return;
			}
			if (key.name === "left") this.panel.cursorIndex = Math.max(0, this.panel.cursorIndex - 1);
			else if (key.name === "right")
				this.panel.cursorIndex = Math.min(graphemeCount(this.panel.value), this.panel.cursorIndex + 1);
			else if (key.name === "home" || key.name === "ctrl-a") this.panel.cursorIndex = 0;
			else if (key.name === "end") this.panel.cursorIndex = graphemeCount(this.panel.value);
			else if (key.name === "backspace" && this.panel.cursorIndex > 0) {
				this.panel.value =
					sliceGraphemes(this.panel.value, 0, this.panel.cursorIndex - 1) +
					sliceGraphemes(this.panel.value, this.panel.cursorIndex);
				this.panel.cursorIndex -= 1;
			} else if (key.name === "delete" && this.panel.cursorIndex < graphemeCount(this.panel.value)) {
				this.panel.value =
					sliceGraphemes(this.panel.value, 0, this.panel.cursorIndex) +
					sliceGraphemes(this.panel.value, this.panel.cursorIndex + 1);
			} else if (key.name === "enter") {
				// Commit guard: a submit already in flight swallows further Enter presses.
				const submit = this.panelSubmit;
				if (submit && !this.panelActionBusy) {
					this.panelActionBusy = true;
					const abort = new AbortController();
					this.panelAbort?.abort(new Error("Panel operation replaced."));
					this.panelAbort = abort;
					this.render();
					const origin = this.panel;
					this.panelActionError = undefined;
					try {
						await submit(this.panel.value);
					} catch (error) {
						if (!abort.signal.aborted && this.panel === origin) this.panelActionError = messageOf(error);
					} finally {
						if (this.panelAbort === abort) this.panelAbort = undefined;
						this.panelActionBusy = false;
						this.render();
					}
				}
				return;
			} else if (key.text && !key.text.includes("\n")) {
				this.panel.value =
					sliceGraphemes(this.panel.value, 0, this.panel.cursorIndex) +
					key.text +
					sliceGraphemes(this.panel.value, this.panel.cursorIndex);
				this.panel.cursorIndex += graphemeCount(key.text);
			}
			this.render();
			return;
		}
		if (this.panel.kind === "menu") {
			const items = visibleMenuItems(this.panel);
			if (key.name === "escape") {
				if (this.panel.query) {
					this.panel.query = "";
					this.normalizeMenuSelection(this.panel);
					this.render();
				} else this.returnFromPanel();
				return;
			}
			if (key.name === "up") this.moveMenuSelection(this.panel, -1);
			else if (key.name === "down") this.moveMenuSelection(this.panel, 1);
			else if (key.name === "backspace") {
				this.panel.query = sliceGraphemes(this.panel.query, 0, Math.max(0, graphemeCount(this.panel.query) - 1));
				this.normalizeMenuSelection(this.panel);
			} else if (key.text && !key.text.includes("\n")) {
				this.panel.query += key.text;
				this.normalizeMenuSelection(this.panel);
			} else if (key.name === "enter") {
				const item = items[this.panel.selected];
				const action = item ? this.panelActions.get(item.id) : undefined;
				if (action && !this.panelActionBusy) {
					this.panelActionBusy = true;
					const abort = new AbortController();
					this.panelAbort?.abort(new Error("Panel operation replaced."));
					this.panelAbort = abort;
					this.render();
					const origin = this.panel;
					this.panelActionError = undefined;
					try {
						await action();
					} catch (error) {
						if (!abort.signal.aborted && this.panel === origin) this.panelActionError = messageOf(error);
					} finally {
						if (this.panelAbort === abort) this.panelAbort = undefined;
						this.panelActionBusy = false;
						this.render();
					}
				}
				return;
			}
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (key.name === "escape") {
			this.returnFromPanel();
			return;
		}
		this.render();
	}
	private normalizeMenuSelection(panel: MenuPanelState): void {
		const items = visibleMenuItems(panel);
		const normalizedQuery = panel.query.trim().toLocaleLowerCase();
		if (normalizedQuery) {
			const exact = items.findIndex(
				(item) => item.label.trim().toLocaleLowerCase() === normalizedQuery && this.panelActions.has(item.id),
			);
			if (exact >= 0) {
				panel.selected = exact;
				return;
			}
		}
		const actionable = items.flatMap((item, index) => (this.panelActions.has(item.id) ? [index] : []));
		if (!actionable.length) {
			panel.selected = 0;
			return;
		}
		panel.selected = actionable.find((index) => index >= panel.selected) ?? actionable[0]!;
	}
	private moveMenuSelection(panel: MenuPanelState, delta: number): void {
		const items = visibleMenuItems(panel);
		const actionable = items.flatMap((item, index) => (this.panelActions.has(item.id) ? [index] : []));
		if (!actionable.length) {
			panel.selected = 0;
			return;
		}
		const current = actionable.indexOf(panel.selected);
		const start = current >= 0 ? current : 0;
		panel.selected = actionable[(start + delta + actionable.length) % actionable.length]!;
	}
	private async handleModelPanelKey(key: KeyInput): Promise<void> {
		const panel = this.panel;
		if (!panel || panel.kind !== "model") return;
		if (panel.busy && key.name === "escape") {
			this.panelAbort?.abort(new Error("Model operation cancelled by user."));
			this.panelAbort = undefined;
			this.panelOperationId += 1;
			panel.busy = false;
			panel.busyLabel = undefined;
			panel.error = "Cancelled.";
			this.render();
			return;
		}
		if (panel.busy) return;
		const models = visibleModelChoices(panel);
		const move = (length: number, delta: number): void => {
			if (length <= 0) return;
			if (panel.step === "role") panel.targetIndex = (panel.targetIndex + length + delta) % length;
			else if (panel.step === "route") panel.routeIndex = (panel.routeIndex + length + delta) % length;
			else if (panel.step === "model") {
				panel.modelIndex = (panel.modelIndex + length + delta) % length;
				panel.reasoningIndex = 0;
			} else if (panel.step === "confirm") panel.confirmIndex = (panel.confirmIndex + length + delta) % length;
		};
		const length =
			panel.step === "role"
				? panel.targets.length
				: panel.step === "route"
					? panel.routes.length
					: panel.step === "model"
						? models.length
						: modelConfirmActions(panel).length;
		if (key.name === "up") {
			move(length, -1);
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (key.name === "down") {
			move(length, 1);
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (key.name === "escape") {
			if (panel.step === "model" && panel.modelQuery) {
				panel.modelQuery = "";
				panel.modelIndex = 0;
				this.render();
				return;
			}
			if (panel.step === "model") panel.step = "route";
			else if (panel.step === "route" && this.panelReturn === "graph") this.returnFromPanel();
			else if (panel.step === "route") panel.step = "role";
			else if (panel.step === "confirm") panel.step = "model";
			else this.closePanel();
			panel.error = undefined;
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (panel.step === "model") {
			const selected = models[panel.modelIndex];
			const levels = selected?.reasoningLevels ?? [];
			if (key.name === "left" || key.name === "right") {
				if (levels.length > 1) {
					panel.reasoningIndex =
						(panel.reasoningIndex + levels.length + (key.name === "left" ? -1 : 1)) % levels.length;
				}
				this.render();
				return;
			}
			if (key.name === "backspace") {
				panel.modelQuery = sliceGraphemes(panel.modelQuery, 0, Math.max(0, graphemeCount(panel.modelQuery) - 1));
				panel.modelIndex = 0;
				this.render();
				return;
			}
			if (key.text && !key.text.includes("\n") && key.name !== "enter") {
				panel.modelQuery += key.text;
				panel.modelIndex = 0;
				this.render();
				return;
			}
		}
		if (key.name !== "enter") return;
		if (panel.step === "role") {
			panel.step = "route";
			panel.error = undefined;
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (panel.step === "route") {
			const route = panel.routes[panel.routeIndex];
			if (route?.provider === "__setup__") {
				this.closePanel();
				await this.runSetupWizard();
				return;
			}
			if (!route || !route.ready) {
				panel.error = "This provider has no configured credential. Use /setup to add it.";
				this.render();
				return;
			}
			panel.busy = true;
			panel.busyLabel = `Discovering models from ${route.label}…`;
			const operationId = ++this.panelOperationId;
			const abort = new AbortController();
			this.panelAbort?.abort(new Error("Model operation replaced."));
			this.panelAbort = abort;
			this.render();
			try {
				const models =
					typeof this.options.client.discoverModels === "function"
						? await this.options.client.discoverModels(route.provider, {
								baseUrl: route.baseUrl,
								authMode: route.authMode,
								includeProvenance: true,
								signal: abort.signal,
							})
						: [];
				if (this.panel !== panel || this.panelOperationId !== operationId) return;
				panel.models = models;
				if (!panel.models.length) panel.error = "No models were returned for this configured route.";
				else {
					panel.modelQuery = this.requestedModelQuery ?? "";
					this.requestedModelQuery = undefined;
					const requestedIndex = visibleModelChoices(panel).findIndex(
						(model) => model.id.toLocaleLowerCase() === panel.modelQuery.trim().toLocaleLowerCase(),
					);
					panel.modelIndex = requestedIndex >= 0 ? requestedIndex : 0;
					panel.reasoningIndex = 0;
					panel.step = "model";
					panel.error = undefined;
					this.ensureSelectedModalVisible();
				}
			} catch (error) {
				if (this.panel !== panel || this.panelOperationId !== operationId) return;
				panel.error = messageOf(error);
				this.modalViewport.reset();
			} finally {
				if (this.panel !== panel || this.panelOperationId !== operationId) return;
				if (this.panelAbort === abort) this.panelAbort = undefined;
				panel.busy = false;
				panel.busyLabel = undefined;
				this.render();
			}
			return;
		}
		if (panel.step === "model") {
			if (models[panel.modelIndex]) {
				panel.confirmIndex = 0;
				panel.step = "confirm";
				panel.error = undefined;
				this.ensureSelectedModalVisible();
			}
			this.render();
			return;
		}
		if (panel.step === "confirm") {
			const action = modelConfirmActions(panel)[panel.confirmIndex];
			if (action === "back") {
				panel.step = "model";
				this.render();
				return;
			}
			if (action === "retry") {
				const route = panel.routes[panel.routeIndex];
				if (!route || route.provider === "__setup__") {
					panel.error = "The provider route is unavailable. Choose another route.";
					this.render();
					return;
				}
				panel.busy = true;
				panel.busyLabel = `Refreshing models from ${route.label}…`;
				panel.error = undefined;
				const operationId = ++this.panelOperationId;
				const abort = new AbortController();
				this.panelAbort?.abort(new Error("Model operation replaced."));
				this.panelAbort = abort;
				this.render();
				try {
					const models =
						typeof this.options.client.discoverModels === "function"
							? await this.options.client.discoverModels(route.provider, {
									baseUrl: route.baseUrl,
									authMode: route.authMode,
									includeProvenance: true,
									signal: abort.signal,
								})
							: [];
					if (this.panel !== panel || this.panelOperationId !== operationId) return;
					panel.models = models;
					panel.modelIndex = 0;
					panel.modelQuery = "";
					panel.reasoningIndex = 0;
					panel.step = models.length ? "model" : "route";
					if (!models.length) panel.error = "No models were returned. Choose another route or open setup.";
					this.ensureSelectedModalVisible();
				} catch (error) {
					if (this.panel !== panel || this.panelOperationId !== operationId) return;
					panel.error = `Provider discovery failed: ${messageOf(error)} Choose another route or retry.`;
					this.modalViewport.reset();
				} finally {
					if (this.panel !== panel || this.panelOperationId !== operationId) return;
					if (this.panelAbort === abort) this.panelAbort = undefined;
					panel.busy = false;
					panel.busyLabel = undefined;
					this.render();
				}
				return;
			}
			if (action === "session") {
				if (
					!this.session ||
					panel.targets[panel.targetIndex]?.kind !== "coordinator" ||
					typeof this.options.client.switchModel !== "function"
				) {
					panel.error = "Session-only model routing is available for the active coordinator session.";
					this.render();
					return;
				}
				const sessionRoute = panel.routes[panel.routeIndex];
				const sessionModel = visibleModelChoices(panel)[panel.modelIndex];
				if (!sessionRoute || !sessionModel) return;
				const contextLimit = panel.contextLimitOverride ?? sessionModel.contextLimit;
				panel.busy = true;
				panel.busyLabel = `Applying ${sessionModel.id} to this session…`;
				const operationId = ++this.panelOperationId;
				const abort = new AbortController();
				this.panelAbort?.abort(new Error("Model operation replaced."));
				this.panelAbort = abort;
				this.render();
				try {
					await this.panelRequest(
						this.options.client.switchModel,
						[
							{
								provider: sessionRoute.provider,
								modelName: sessionModel.id,
								baseUrl: sessionRoute.baseUrl,
								discoveredModel: sessionModel,
								authMode: sessionRoute.authMode,
								...(typeof contextLimit === "number" ? { maxContextSize: contextLimit } : {}),
								...(typeof sessionModel.maxOutputTokens === "number"
									? { maxOutputTokens: sessionModel.maxOutputTokens }
									: {}),
								...(reasoningConfigForModel(sessionModel, panel.reasoningIndex)
									? { reasoningConfig: reasoningConfigForModel(sessionModel, panel.reasoningIndex) }
									: {}),
								scope: "session",
								sessionId: this.session.id,
							},
						],
						abort.signal,
					);
					if (this.panel !== panel || this.panelOperationId !== operationId) return;
					await this.refreshRuntimeModel();
					this.record(
						"status",
						`${panel.targets[panel.targetIndex]!.label} now uses ${sessionRoute.label} · ${sessionModel.id} for this session.`,
					);
					this.closePanel();
				} catch (error) {
					if (this.panel !== panel || this.panelOperationId !== operationId) return;
					panel.busy = false;
					panel.busyLabel = undefined;
					panel.error = messageOf(error);
					this.render();
				} finally {
					if (this.panelAbort === abort) this.panelAbort = undefined;
				}
				return;
			}
			if (action === "policy") {
				await this.openGraphPanel();
				return;
			}
		}
		const route = panel.routes[panel.routeIndex];
		const model = visibleModelChoices(panel)[panel.modelIndex];
		if (!route || !model) return;
		const contextLimit = panel.contextLimitOverride ?? model.contextLimit;
		panel.busy = true;
		panel.busyLabel = `Applying ${model.id} to ${panel.targets[panel.targetIndex]?.label ?? "agent"}…`;
		const operationId = ++this.panelOperationId;
		const abort = new AbortController();
		this.panelAbort?.abort(new Error("Model operation replaced."));
		this.panelAbort = abort;
		this.render();
		try {
			const target = panel.targets[panel.targetIndex]!;
			const routePatch = {
				provider: route.provider,
				modelName: model.id,
				...(route.baseUrl ? { baseUrl: route.baseUrl } : {}),
				authMode: route.authMode,
				...(typeof model.contextLength === "number" ? { contextLength: model.contextLength } : {}),
				...(typeof contextLimit === "number" ? { maxContextSize: contextLimit } : {}),
				...(model.capabilities?.length ? { capabilities: [...model.capabilities] } : {}),
				...(typeof model.maxOutputTokens === "number" ? { maxOutputTokens: model.maxOutputTokens } : {}),
				...(reasoningConfigForModel(model, panel.reasoningIndex)
					? { reasoningConfig: reasoningConfigForModel(model, panel.reasoningIndex) }
					: {}),
			};
			let graphRoute: Record<string, unknown> = routePatch;
			if (target.kind === "coordinator" && typeof this.options.client.switchModel === "function") {
				// Keep the interactive picker on the same authoritative boundary as
				// /model set and setup: discover provider metadata, persist the
				// canonical model id, and rebuild the active runtime before returning.
				const applied = await this.panelRequest(
					this.options.client.switchModel,
					[
						{
							provider: route.provider,
							modelName: model.id,
							baseUrl: route.baseUrl,
							discoveredModel: model,
							authMode: route.authMode,
							...(typeof contextLimit === "number" ? { maxContextSize: contextLimit } : {}),
							...(typeof model.maxOutputTokens === "number" ? { maxOutputTokens: model.maxOutputTokens } : {}),
							...(reasoningConfigForModel(model, panel.reasoningIndex)
								? { reasoningConfig: reasoningConfigForModel(model, panel.reasoningIndex) }
								: {}),
							scope: "user",
						},
					],
					abort.signal,
				);
				const appliedFields = Object.fromEntries(
					Object.entries(applied).filter(
						([key, value]) =>
							value !== undefined &&
							((key !== "provider" && key !== "modelName") || (typeof value === "string" && value.trim().length > 0)),
					),
				);
				graphRoute = {
					...routePatch,
					...appliedFields,
					...(applied.capabilities ? { capabilities: [...applied.capabilities] } : {}),
				};
				if (typeof graphRoute["provider"] !== "string" || !graphRoute["provider"].trim())
					throw new Error("Model switch returned no provider; the selected route was not applied.");
				await this.panelRequest(
					this.options.client.updateConfiguration,
					[{ agentGraph: { coordinator: graphRoute } }, "user"],
					abort.signal,
				);
			} else {
				await this.panelRequest(
					this.options.client.updateConfiguration,
					[
						{
							...agentTargetPatch(target, routePatch),
						},
						"user",
					],
					abort.signal,
				);
			}
			if (this.panel !== panel || this.panelOperationId !== operationId) return;
			await this.refreshRuntimeModel();
			this.record("status", `${target.label} now uses ${route.label} · ${model.id}.`);
			if (this.panelReturn === "graph") {
				await this.openGraphPanel({ panel, operationId, signal: abort.signal });
				return;
			}
			this.closePanel();
		} catch (error) {
			if (this.panel !== panel || this.panelOperationId !== operationId) return;
			panel.error = messageOf(error);
			panel.busy = false;
			panel.busyLabel = undefined;
			this.render();
		} finally {
			if (this.panelAbort === abort) this.panelAbort = undefined;
		}
	}
	private async openActivityBrowser(activeOnly: boolean): Promise<void> {
		const options = this.panelRequestOptions();
		const items = await this.options.client.listActivities(
			{
				...(activeOnly && this.session?.id ? { sessionId: this.session.id } : {}),
				activeOnly,
			},
			options,
		);
		if (options.signal?.aborted) return;
		const menuItems: PanelMenuItem[] = items.length
			? items.map((item) => ({
					id: item.activityId,
					label: `${item.status}  ${item.kind}  ${item.title}`,
					detail: item.taskId ?? item.subagentId ?? item.activityId,
				}))
			: [{ id: "empty", label: activeOnly ? "No agent activity is running." : "No recorded activity history." }];
		const actions = new Map<string, () => Promise<void> | void>();
		for (const item of items) {
			actions.set(item.activityId, () => {
				const taskId = item.taskId;
				if (!taskId) {
					this.showPanelResult([
						`Status: ${item.status}`,
						`Kind: ${item.kind}`,
						`Title: ${item.title}`,
						`Activity: ${item.activityId}`,
					]);
					return;
				}
				const activitySession = this.options.client.session(item.sessionId);
				const taskActions: PanelMenuItem[] = [
					{ id: "output", label: "Open output", detail: "Read the captured task output" },
					...(activeOnly ? [{ id: "stop", label: "Stop task", detail: "Request cancellation" }] : []),
					{ id: "back", label: "Back" },
				];
				const taskHandlers = new Map<string, () => Promise<void> | void>([
					[
						"output",
						async () => {
							const options = this.panelRequestOptions();
							const output = await activitySession.readActivityOutput(taskId, 0, undefined, options);
							if (options.signal?.aborted) return;
							this.showPanelResult(output.content ? output.content.split("\n") : ["No output captured."]);
						},
					],
					...(activeOnly
						? ([
								[
									"stop",
									async () => {
										if (!(await this.askConfirm(`Stop task ${taskId}?`))) return;
										const options = this.panelRequestOptions();
										await activitySession.stopActivity(taskId, options);
										if (options.signal?.aborted) return;
										this.record("status", `Stop requested for ${taskId}.`);
										await this.openActivityBrowser(true);
									},
								],
							] as const)
						: []),
					["back", () => this.openActivityBrowser(activeOnly)],
				]);
				this.openMenuPanel(`Task · ${taskId}`, taskActions, taskHandlers);
			});
		}
		if (activeOnly) {
			menuItems.push({ id: "refresh", label: "Refresh", detail: "Reload current work" });
			actions.set("refresh", () => this.openActivityBrowser(true));
		}
		this.openMenuPanel(activeOnly ? "Current work" : "Activity history", menuItems, actions);
	}
	private async handleGraphPanelKey(key: KeyInput): Promise<void> {
		const panel = this.panel;
		if (!panel || panel.kind !== "graph") return;
		if (panel.busy && key.name === "escape") {
			this.panelAbort?.abort(new Error("Graph operation cancelled by user."));
			this.panelAbort = undefined;
			this.panelOperationId += 1;
			panel.busy = false;
			panel.busyLabel = undefined;
			panel.error = "Cancelled.";
			this.render();
			return;
		}
		if (panel.busy) return;
		if (panel.editing) {
			if (key.name === "escape") {
				panel.editing = undefined;
				this.render();
				return;
			}
			if (key.name === "left") panel.editing.cursorIndex = Math.max(0, panel.editing.cursorIndex - 1);
			else if (key.name === "right")
				panel.editing.cursorIndex = Math.min(graphemeCount(panel.editing.value), panel.editing.cursorIndex + 1);
			else if (key.name === "home" || key.name === "ctrl-a") panel.editing.cursorIndex = 0;
			else if (key.name === "end") panel.editing.cursorIndex = graphemeCount(panel.editing.value);
			else if (key.name === "backspace" && panel.editing.cursorIndex > 0) {
				panel.editing.value =
					sliceGraphemes(panel.editing.value, 0, panel.editing.cursorIndex - 1) +
					sliceGraphemes(panel.editing.value, panel.editing.cursorIndex);
				panel.editing.cursorIndex -= 1;
			} else if (key.name === "delete" && panel.editing.cursorIndex < graphemeCount(panel.editing.value)) {
				panel.editing.value =
					sliceGraphemes(panel.editing.value, 0, panel.editing.cursorIndex) +
					sliceGraphemes(panel.editing.value, panel.editing.cursorIndex + 1);
			} else if (key.name === "enter") {
				const edit = panel.editing;
				panel.editing = undefined;
				await this.runGraphPanelOperation(
					panel,
					`Saving ${graphFieldLabel(edit.field)}…`,
					async (operationId, signal) => {
						if (await this.commitGraphField(edit.field, edit.value, signal))
							await this.openGraphPanel({ panel, operationId, signal });
					},
				);
				return;
			} else if (key.text && !key.text.includes("\n")) {
				panel.editing.value =
					sliceGraphemes(panel.editing.value, 0, panel.editing.cursorIndex) +
					key.text +
					sliceGraphemes(panel.editing.value, panel.editing.cursorIndex);
				panel.editing.cursorIndex += graphemeCount(key.text);
			}
			this.render();
			return;
		}
		if (key.name === "up") {
			panel.fieldIndex = (panel.fieldIndex + panel.fields.length - 1) % panel.fields.length;
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (key.name === "down") {
			panel.fieldIndex = (panel.fieldIndex + 1) % panel.fields.length;
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (key.name === "escape") {
			this.returnFromPanel();
			return;
		}
		if (key.name !== "enter") return;
		const field = panel.fields[panel.fieldIndex]!;
		if (field === "permissionProfile" || field === "interactionMode") {
			this.openGraphChoicePanel(panel.target, field);
			return;
		}
		if (field === "tools") {
			await this.openGraphToolsPicker(panel.target, panel.config[panel.target.id]?.["tools"]);
			return;
		}
		if (field === "reset") {
			const profileId = panel.target.profileId;
			if (!profileId || !(await this.askConfirm(`Restore built-in worker ${profileId} to its defaults?`))) return;
			this.showModal("panel");
			await this.runGraphPanelOperation(panel, `Restoring ${profileId}…`, async (operationId, signal) => {
				await this.options.client.updateConfiguration({ agentGraph: { subagents: { [profileId]: null } } }, "user", {
					signal,
				});
				if (this.panel !== panel || this.panelOperationId !== operationId) return;
				this.record("status", `Built-in worker ${profileId} restored to defaults.`);
				await this.openGraphPanel({ panel, operationId, signal });
			});
			return;
		}
		if (field === "remove") {
			const profileId = panel.target.profileId;
			if (!profileId || !(await this.askConfirm(`Delete subagent profile ${profileId}?`))) return;
			this.showModal("panel");
			await this.runGraphPanelOperation(panel, `Deleting ${profileId}…`, async (operationId, signal) => {
				await this.options.client.updateConfiguration({ agentGraph: { subagents: { [profileId]: null } } }, "user", {
					signal,
				});
				if (this.panel !== panel || this.panelOperationId !== operationId) return;
				this.record("status", `Subagent profile ${profileId} deleted.`);
				await this.openGraphPanel({ panel, operationId, signal });
			});
			return;
		}
		if (field === "route") {
			await this.runGraphPanelOperation(panel, "Opening model routes…", (operationId, signal) =>
				this.openModelPanel(panel.target, true, { panel, operationId, signal }),
			);
			return;
		}
		const value = panel.config[panel.target.id]?.[field];
		const editValue = Array.isArray(value) ? value.join(",") : value === undefined ? "" : String(value);
		panel.editing = { field, value: editValue, cursorIndex: graphemeCount(editValue) };
		this.ensureSelectedModalVisible();
		this.render();
	}
	private async runGraphPanelOperation(
		panel: GraphPanelState,
		label: string,
		operation: (operationId: number, signal: AbortSignal) => Promise<void>,
	): Promise<void> {
		panel.busy = true;
		panel.busyLabel = label;
		panel.error = undefined;
		const operationId = ++this.panelOperationId;
		const abort = new AbortController();
		this.panelAbort?.abort(new Error("Graph operation replaced."));
		this.panelAbort = abort;
		this.render();
		try {
			await operation(operationId, abort.signal);
		} catch (error) {
			if (this.panel !== panel || this.panelOperationId !== operationId) return;
			panel.error = messageOf(error);
		} finally {
			if (this.panel !== panel || this.panelOperationId !== operationId) return;
			if (this.panelAbort === abort) this.panelAbort = undefined;
			panel.busy = false;
			panel.busyLabel = undefined;
			this.render();
		}
	}
	private async commitGraphField(field: GraphEditableField, raw: string, signal?: AbortSignal): Promise<boolean> {
		const value = raw.trim();
		if (!value) return false;
		const parsed: string | number | Record<string, unknown> = [
			"contextLength",
			"maxContextSize",
			"maxOutputTokens",
			"maxSteps",
			"runTimeoutMs",
			"maxQueuedRuns",
			"timeoutMs",
		].includes(field)
			? Number(value)
			: value;
		if (typeof parsed === "number" && (!Number.isFinite(parsed) || parsed <= 0)) {
			this.record("warning", `${field} must be a positive number.`);
			return false;
		}
		const target = (this.panel as GraphPanelState).target;
		await this.panelRequest(
			this.options.client.updateConfiguration,
			[agentTargetPatch(target, { [field]: parsed }), "user"],
			signal,
		);
		if (signal?.aborted) return false;
		await this.refreshRuntimeModel();
		this.record("status", `${target.label} ${field} updated.`);
		return true;
	}
	private returnFromPanel(): void {
		const returnAction = this.panelReturnAction;
		const parent = this.panelReturn;
		this.panelReturn = undefined;
		this.panelReturnAction = undefined;
		if (returnAction) {
			void returnAction();
			return;
		}
		if (parent) {
			void this.openInteractivePanel(parent);
			return;
		}
		this.closePanel();
	}
	private closePanel(): void {
		this.panelCommandPrefills = [];
		this.stopLearnRefresh();
		this.panelAbort?.abort(new Error("Panel closed."));
		this.panelAbort = undefined;
		this.panelOperationId += 1;
		this.panel = undefined;
		this.panelActions.clear();
		this.panelSubmit = undefined;
		this.panelActionError = undefined;
		this.panelReturn = undefined;
		this.panelReturnAction = undefined;
		this.dispatch({ type: "overlay", value: "none" });
		this.render();
	}
	private panelRequestOptions(): { readonly signal?: AbortSignal } {
		return this.panelAbort ? { signal: this.panelAbort.signal } : {};
	}
	/** A guard is stale once its operation was cancelled, superseded, or its pinned panel was replaced. */
	private panelGuardStale(guard: PanelOperationGuard | undefined): boolean {
		if (!guard) return false;
		if (guard.signal?.aborted) return true;
		if (this.panelOperationId !== guard.operationId) return true;
		return guard.panel !== undefined && this.panel !== guard.panel;
	}
	private panelRequest<T, A extends readonly unknown[]>(
		method: (...args: A) => Promise<T>,
		args: A,
		signal = this.panelAbort?.signal,
	): Promise<T> {
		// Every SDK method used through this helper takes its optional
		// request-options slot directly after the arguments listed here, so the
		// abort signal is always forwarded; lightweight host doubles simply
		// ignore the extra argument.
		throwIfAborted(signal);
		const callArgs = signal ? [...args, { signal }] : args;
		return (Reflect.apply(method, this.options.client, callArgs as unknown as unknown[]) as Promise<T>).then(
			(value) => {
				// Some embedded/test clients accept request options but do not honour the
				// signal themselves. Do not let their late result revive a panel that
				// Escape already cancelled.
				throwIfAborted(signal);
				return value;
			},
		);
	}
	private applyTheme(theme: "dark" | "light" | "system"): void {
		this.themeName = theme;
		const env = { ...process.env };
		if (theme === "system") delete env["KAGEKO_THEME"];
		else env["KAGEKO_THEME"] = theme;
		this.renderer.setTheme(resolveTheme(env));
		this.record("status", `Theme set to ${theme}.`);
		this.closePanel();
	}
	private async sendPlanInstruction(text: string): Promise<void> {
		if (!this.session || typeof this.session.prompt !== "function") {
			this.record("warning", "No active session can receive a plan instruction.");
			this.closePanel();
			return;
		}
		await this.sendPrompt({ id: `plan-${Date.now()}`, text, attachments: [], state: "sending" });
		this.record("status", "Instruction sent to the coordinator.");
		this.closePanel();
	}
	private showPanelResult(lines: readonly string[], title = "Result", parent?: InteractivePanelName): void {
		const items: PanelMenuItem[] = lines.map((line, index) => ({ id: `result-${index}`, label: line }));
		items.push({ id: "back", label: parent ? `Back to ${panelLabel(parent)}` : "Close" });
		this.openMenuPanel(
			title,
			items,
			new Map([["back", () => (parent ? this.openInteractivePanel(parent) : this.closePanel())]]),
			parent,
		);
	}
	private async showLearnPanel(guard?: PanelOperationGuard): Promise<void> {
		if (!this.session) return;
		const model = await this.buildLearnPanelModel(this.session.id);
		if (this.panelGuardStale(guard)) return;
		this.learningPendingCount = model.pendingCount;
		this.openMenuPanel("Resident learner", model.items, model.actions);
		this.startLearnRefresh();
	}
	private async buildLearnPanelModel(sessionId: string): Promise<{
		items: PanelMenuItem[];
		actions: Map<string, () => Promise<void> | void>;
		pendingCount: number;
	}> {
		const rawPending = (await this.options.client.listLearningPending(
			sessionId,
			this.panelRequestOptions(),
		)) as readonly LearningPendingEntry[];
		const pending = rawPending.flatMap((entry) => {
			const id = entry.id ?? entry.event?.id;
			if (!id) return [];
			return [
				{
					id,
					kind: entry.output?.kind ?? entry.kind ?? "learning proposal",
					name: entry.output?.name ?? id,
					description: entry.output?.description,
					raw: entry,
				},
			];
		});
		const items: PanelMenuItem[] = pending.map((entry) => ({
			id: entry.id,
			label: entry.name,
			detail: `${entry.kind}${entry.description ? ` · ${entry.description}` : ""}`,
		}));
		// Reserved rows are prefixed so a real (uuid) event id can never collide.
		if (!pending.length) items.push({ id: "__empty", label: "No pending proposals" });
		const actions = new Map<string, () => Promise<void> | void>();
		for (const entry of pending)
			actions.set(entry.id, () =>
				this.openMenuPanel(
					`Learning proposal · ${entry.name}`,
					[
						{ id: "approve", label: "Approve" },
						{ id: "details", label: "View details" },
						{ id: "reject", label: "Reject" },
						{ id: "cancel", label: "Cancel" },
					],
					new Map([
						[
							"approve",
							async () => {
								const options = this.panelRequestOptions();
								const result = (await this.options.client.resolveLearning(
									this.session!.id,
									entry.id,
									"approve",
									options,
								)) as { resolved?: boolean; reason?: string } | undefined;
								if (options.signal?.aborted) return;
								await this.openInteractivePanel("learn");
								// A resolved:false result is a failure, not a success: surface the reason.
								if (result?.resolved === false) {
									this.panelActionError = `Could not approve: ${result.reason ?? "unknown reason"}.`;
									this.render();
									return;
								}
								this.record("status", "Learning proposal approved.");
							},
						],
						[
							"details",
							() =>
								this.showPanelResult(
									learningProposalDetailLines(entry.raw),
									`Learning proposal · ${entry.name}`,
									"learn",
								),
						],
						[
							"reject",
							async () => {
								if (!(await this.askConfirm("Reject this learning proposal?"))) {
									this.record("status", "Learning proposal rejection cancelled.");
									await this.openInteractivePanel("learn");
									return;
								}
								const options = this.panelRequestOptions();
								const result = (await this.options.client.resolveLearning(
									this.session!.id,
									entry.id,
									"reject",
									options,
								)) as { resolved?: boolean; reason?: string } | undefined;
								if (options.signal?.aborted) return;
								await this.openInteractivePanel("learn");
								if (result?.resolved === false) {
									this.panelActionError = `Could not reject: ${result.reason ?? "unknown reason"}.`;
									this.render();
									return;
								}
								this.record("status", "Learning proposal rejected.");
							},
						],
						["cancel", () => this.openInteractivePanel("learn")],
					]),
				),
			);
		items.push({
			id: "__status",
			label: "Learner status",
			detail: `${pending.length} pending proposal${pending.length === 1 ? "" : "s"}`,
		});
		actions.set("__status", async () => {
			const options = this.panelRequestOptions();
			const status = await this.options.client.memoryStatus(this.session!.id, options);
			if (options.signal?.aborted) return;
			this.showPanelResult(
				[
					status.learningEnabled === false ? "Resident learner: disabled" : "Resident learner: active",
					`Pending proposals: ${status.pendingLearning}`,
				],
				"Learner status",
				"learn",
			);
		});
		return { items, actions, pendingCount: pending.length };
	}
	/** The auto-refresh only owns the top-level proposal list, never a submenu. */
	private isLearnListPanel(): boolean {
		return (
			this.state.overlay === "panel" &&
			this.panel?.kind === "menu" &&
			this.panel.title === "Resident learner" &&
			this.panel.parent === undefined
		);
	}
	private startLearnRefresh(): void {
		this.stopLearnRefresh();
		this.learnRefreshTimer = setInterval(() => void this.refreshLearnPanel(), LEARN_PANEL_REFRESH_MS);
		this.learnRefreshTimer.unref?.();
	}
	private stopLearnRefresh(): void {
		if (this.learnRefreshTimer) clearInterval(this.learnRefreshTimer);
		this.learnRefreshTimer = undefined;
	}
	/** Reload the open proposal list in place, preserving selection and filter. */
	private async refreshLearnPanel(): Promise<void> {
		if (this.closed || this.learnRefreshBusy || !this.session || !this.isLearnListPanel()) return;
		this.learnRefreshBusy = true;
		try {
			const panel = this.panel as MenuPanelState;
			const selectedId = visibleMenuItems(panel)[panel.selected]?.id;
			const model = await this.buildLearnPanelModel(this.session.id);
			// The user may have navigated into a submenu or closed the panel mid-load.
			if (!this.isLearnListPanel()) return;
			const current = this.panel as MenuPanelState;
			this.learningPendingCount = model.pendingCount;
			const unchanged =
				current.items.length === model.items.length &&
				current.items.every(
					(item, index) =>
						item.id === model.items[index]?.id &&
						item.label === model.items[index]?.label &&
						item.detail === model.items[index]?.detail,
				);
			if (unchanged) {
				this.render();
				return;
			}
			this.panelActions = model.actions;
			const next: MenuPanelState = { ...current, items: model.items };
			const visible = visibleMenuItems(next);
			const kept = selectedId === undefined ? -1 : visible.findIndex((item) => item.id === selectedId);
			next.selected = kept >= 0 ? kept : current.selected;
			this.panel = next;
			this.normalizeMenuSelection(next);
			this.render();
		} catch {
			// A failed refresh must not tear down the open panel; the next tick retries.
		} finally {
			this.learnRefreshBusy = false;
		}
	}
	private async refreshLearningPending(): Promise<void> {
		if (!this.session || this.learningPendingBusy || this.closed) return;
		this.learningPendingBusy = true;
		try {
			const pending = await this.options.client.listLearningPending(this.session.id);
			if (pending.length !== this.learningPendingCount) {
				this.learningPendingCount = pending.length;
				this.render();
			}
		} catch {
			// Learning may be disabled or mid-drain; keep the last known count.
		} finally {
			this.learningPendingBusy = false;
		}
	}
	private askConfirm(message: string): Promise<boolean> {
		return new Promise((resolve) => {
			this.pendingConfirm?.resolve(false);
			this.confirmChoice = 0;
			// Confirmation is a modal replacement for an action panel, not a child
			// form. Remove the panel capture before showing it so Esc leaves the TUI
			// at the composer, matching the existing command contract while the
			// confirmation itself still gets a focused stack owner.
			if (this.normalOverlayStack.contains("panel")) this.normalOverlayStack.hide("panel");
			this.pendingConfirm = { message, resolve };
			this.showModal("confirm");
			this.render();
		});
	}
	private handleConfirmKey(key: KeyInput): void {
		const pending = this.pendingConfirm;
		if (!pending) {
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return;
		}
		if (
			key.name === "up" ||
			key.name === "down" ||
			key.name === "left" ||
			key.name === "right"
		) {
			this.confirmChoice = this.confirmChoice === 0 ? 1 : 0;
		} else if (key.name === "enter" || key.name === "escape" || key.name === "ctrl-c") {
			this.pendingConfirm = undefined;
			this.dispatch({ type: "overlay", value: "none" });
			pending.resolve(key.name === "enter" && this.confirmChoice === 0);
		}
		this.render();
	}
	private async handleTrustKey(key: KeyInput): Promise<void> {
		const pending = this.startupTrust;
		if (!pending) {
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return;
		}
		if (this.trustBusy && key.name === "escape") {
			this.trustAbort?.abort(new Error("Workspace trust request cancelled by user."));
			this.trustAbort = undefined;
			this.trustBusy = false;
			pending.error = "Cancelled.";
			this.render();
			return;
		}
		if (this.trustBusy) return;
		if (key.name === "up" || key.name === "down") {
			pending.choice = pending.choice === 0 ? 1 : 0;
			this.render();
			return;
		}
		if (key.name === "enter") {
			if (pending.choice === 0) {
				this.trustBusy = true;
				const abort = new AbortController();
				this.trustAbort = abort;
				pending.error = undefined;
				this.render();
				try {
					await this.options.client.grantWorkspaceTrust({ signal: abort.signal });
					if (abort.signal.aborted || this.trustAbort !== abort || this.startupTrust !== pending) return;
					this.dispatch({ type: "overlay", value: "none" });
					this.record("status", "Workspace trusted.");
					pending.resolve(true);
				} catch (error) {
					if (!abort.signal.aborted && this.startupTrust === pending) pending.error = messageOf(error);
				} finally {
					if (this.trustAbort === abort) this.trustAbort = undefined;
					this.trustBusy = false;
					this.render();
				}
			} else {
				this.dispatch({ type: "overlay", value: "none" });
				pending.resolve(false);
			}
			return;
		}
		if (key.name === "escape") {
			this.dispatch({ type: "overlay", value: "none" });
			pending.resolve(false);
			return;
		}
		this.render();
	}
	private async handleSetupKey(key: KeyInput): Promise<void> {
		const wizard = this.setupWizard;
		if (!wizard) {
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
			return;
		}
		// Setup is a real modal owner, so cancellation must be handled here rather
		// than by the global Ctrl+C path (the input loop intentionally bypasses the
		// serialized command queue while the wizard is awaited).
		if (key.name === "ctrl-c") {
			await this.finishSetup(undefined);
			return;
		}
		if (wizard.busy) {
			if (wizard.oauthPrompt) {
				const options = wizard.oauthPrompt.options;
				if (key.name === "escape") {
					wizard.oauthPrompt.resolve(undefined);
					wizard.oauthPrompt = undefined;
					wizard.oauthAbort?.abort(new Error("OAuth login cancelled by user."));
					wizard.oauthAbort = undefined;
					this.setupOperationId += 1;
					wizard.busy = false;
					wizard.controller.error = "Cancelled.";
					wizard.controller.status = undefined;
					this.render();
					return;
				}
				if (options?.length) {
					if (key.name === "up")
						wizard.oauthPrompt.selectedIndex = (wizard.oauthPrompt.selectedIndex - 1 + options.length) % options.length;
					else if (key.name === "down")
						wizard.oauthPrompt.selectedIndex = (wizard.oauthPrompt.selectedIndex + 1) % options.length;
					else if (key.name === "enter") {
						const prompt = wizard.oauthPrompt;
						wizard.oauthPrompt = undefined;
						prompt.resolve(options[prompt.selectedIndex]?.id);
					}
				} else if (key.name === "backspace")
					wizard.oauthPrompt.value = [...wizard.oauthPrompt.value].slice(0, -1).join("");
				else if (key.name === "enter") {
					const prompt = wizard.oauthPrompt;
					wizard.oauthPrompt = undefined;
					prompt.resolve(prompt.value.trim() || undefined);
				} else if (key.text) wizard.oauthPrompt.value += key.text;
				this.render();
				return;
			}
			if (key.name === "escape") {
				wizard.oauthAbort?.abort(new Error("Setup operation cancelled by user."));
				wizard.oauthAbort = undefined;
				this.setupOperationId += 1;
				wizard.busy = false;
				wizard.controller.error = "Cancelled.";
				wizard.controller.status = undefined;
				this.render();
			}
			return;
		}
		const { controller } = wizard;
		if (key.name === "pageup" || key.name === "pagedown") {
			this.scrollModal((key.name === "pageup" ? -1 : 1) * 8);
			this.render();
			return;
		}
		if (key.name === "escape") {
			if (controller.step !== "provider") {
				controller.step = "provider";
				controller.buffer = "";
				controller.error = undefined;
				controller.modelOptions = [];
				this.render();
			} else await this.finishSetup(undefined);
			return;
		}
		if (controller.step === "provider") {
			if (setupKeyIs(key, "up")) controller.move(-1);
			else if (setupKeyIs(key, "down")) controller.move(1);
			else if (key.name === "enter") {
				controller.acceptProvider();
				if (wizard.credentialOnly && controller.provider.credentialMode === "none") void this.prepareSetupRoute();
			}
			this.ensureSelectedModalVisible();
			this.render();
			return;
		}
		if (controller.step === "oauth" && key.name === "enter") {
			// OAuth may wait for a browser callback or a human prompt. Launch that
			// lifecycle after this focused key is consumed; it must not retain input
			// ownership or delay the prompt that will answer it.
			void this.prepareSetupRoute();
			return;
		}
		if (controller.step === "model") {
			if (setupKeyIs(key, "up") || setupKeyIs(key, "down")) {
				controller.moveModel(setupKeyIs(key, "up") ? -1 : 1);
				this.ensureSelectedModalVisible();
				this.render();
				return;
			}
			if (key.name === "enter") {
				if (!controller.modelOptions.length) {
					if (!controller.buffer.trim()) {
						void this.prepareSetupRoute();
						return;
					}
					const outcome = controller.submitStep();
					if (typeof outcome === "object") await this.finishSetup(outcome);
					else this.render();
					return;
				}
				const outcome = controller.submitStep();
				if (typeof outcome === "object") await this.finishSetup(outcome);
				else this.render();
			} else if (key.name === "backspace") {
				controller.backspace();
				this.render();
			} else if (key.text && !controller.modelOptions.length) {
				controller.type(key.text);
				this.render();
			} else this.render();
			return;
		}
		if (key.name === "backspace") {
			controller.backspace();
			this.render();
			return;
		}
		if (key.name === "enter") {
			const outcome = controller.submitStep();
			if (outcome === "error") {
				this.render();
				return;
			}
			if (typeof outcome === "object") {
				await this.finishSetup(outcome);
				return;
			}
			if (
				outcome === "model" &&
				controller.provider.authMode === "api" &&
				controller.provider.credentialMode !== "none"
			) {
				await this.prepareSetupRoute();
				return;
			}
			this.render();
			return;
		}
		if (key.text) {
			controller.type(key.text);
			this.render();
			return;
		}
		this.render();
	}
	private async prepareSetupRoute(): Promise<void> {
		const wizard = this.setupWizard;
		if (!wizard) return;
		const controller = wizard.controller;
		const operationId = ++this.setupOperationId;
		const operationAbort = new AbortController();
		wizard.oauthAbort?.abort(new Error("Setup operation replaced."));
		wizard.oauthAbort = operationAbort;
		wizard.busy = true;
		controller.error = undefined;
		controller.status = undefined;
		this.render();
		try {
			if (controller.provider.authMode === "oauth") {
				if (typeof this.options.client.loginOAuth !== "function")
					throw new Error("OAuth login is unavailable in this host.");
				// A matching Kageko credential is never evidence that the user has
				// approved this setup run. Hermes asks before reuse/import; until that
				// explicit flow exists here we always start a new provider session.
				if (
					await this.options.client
						.hasCredential(controller.provider.id, "oauth", { signal: operationAbort.signal })
						.catch(() => false)
				)
					controller.status =
						"An existing Kageko credential was found and will not be reused automatically. Starting a fresh login…";
				await this.options.client.loginOAuth(controller.provider.id, undefined, {
					signal: operationAbort.signal,
					notify: (event) => {
						if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
						if (event.type === "device_code") {
							wizard.oauthUrl = event.verificationUri;
							wizard.oauthCode = event.userCode;
							wizard.oauthInstructions = `Open the verification page and enter code ${event.userCode}.`;
							controller.status = "Waiting for provider approval…";
							if (event.openBrowser) this.openOAuthUrl(event.verificationUri);
						} else if (event.type === "auth_url") {
							wizard.oauthUrl = event.url;
							wizard.oauthInstructions = event.instructions;
							controller.status = event.instructions ?? "Complete authorization in the browser, then return here.";
							if (event.openBrowser) this.openOAuthUrl(event.url);
						} else controller.status = event.message;
						this.render();
					},
					prompt: (definition) =>
						new Promise<string | undefined>((resolve) => {
							if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return resolve(undefined);
							wizard.oauthPrompt = {
								message: definition.message,
								placeholder: definition.placeholder,
								value: "",
								options: definition.options,
								selectedIndex: 0,
								resolve,
							};
							this.render();
						}),
				});
			} else if (controller.provider.credentialMode !== "none") {
				const apiKey = controller.apiKeyValue();
				if (!apiKey) throw new Error("API key must not be empty");
				if (!wizard.credentialReady)
					await this.options.client.setApiKey(controller.provider.id, apiKey, { signal: operationAbort.signal });
			}
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			wizard.credentialReady = true;
			if (wizard.credentialOnly) {
				this.setupWizard = undefined;
				this.dispatch({ type: "overlay", value: "none" });
				wizard.resolve(true);
				this.record(
					"status",
					`${controller.provider.authMode === "oauth" ? "OAuth" : "API credential"} connected for ${controller.provider.label}.`,
				);
				this.render();
				return;
			}
			if (typeof this.options.client.discoverModels !== "function")
				throw new Error("Live model discovery is unavailable in this client.");
			const models = await this.options.client.discoverModels(controller.provider.id, {
				authMode: controller.provider.authMode,
				includeProvenance: true,
				signal: operationAbort.signal,
			});
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			const options: SetupModelOption[] = models.map((model) => ({
				id: model.id,
				...(model.name ? { name: model.name } : {}),
				...(typeof model.contextLength === "number" ? { contextLength: model.contextLength } : {}),
				...(typeof model.contextLimit === "number" ? { contextLimit: model.contextLimit } : {}),
				...(typeof model.maxOutputTokens === "number" ? { maxOutputTokens: model.maxOutputTokens } : {}),
				...(model.reasoningLevels?.length ? { reasoningLevels: [...model.reasoningLevels] } : {}),
				...(model.capabilities?.length ? { capabilities: [...model.capabilities] } : {}),
				...(model.provenance ? { provenance: model.provenance } : {}),
				...(model.metadataSource ? { metadataSource: model.metadataSource } : {}),
				...(model.provenance?.contextLength ? { contextSource: model.provenance.contextLength } : {}),
			}));
			controller.setModels(options);
			controller.step = "model";
			if (!options.length)
				controller.error = "No models returned. Press Enter to retry or Esc to choose another provider.";
		} catch (error) {
			if (wizard.oauthAbort === operationAbort) wizard.oauthAbort = undefined;
			wizard.oauthPrompt = undefined;
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			controller.error = messageOf(error);
			// Keep OAuth failures at the auth gate. A model must never be selectable
			// before its credential route has been established.
			if (controller.provider.authMode === "oauth") {
				controller.step = "oauth";
				controller.modelOptions = [];
			} else {
				controller.step = "model";
				controller.modelOptions = [];
			}
		} finally {
			if (wizard.oauthAbort === operationAbort) wizard.oauthAbort = undefined;
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			wizard.busy = false;
			this.render();
		}
	}
	private async handleShellKey(key: KeyInput): Promise<void> {
		if (key.name === "f2") {
			await this.closeEmbeddedShell();
			return;
		}
		const input = this.shellProcess?.stdin;
		if (!input || input.destroyed) return;
		if (key.name === "enter") input.write(this.shellCodec.encode("\r\n"));
		else if (key.name === "backspace") input.write(this.shellCodec.encode("\b \b"));
		else if (key.name === "ctrl-c") input.write(this.shellCodec.encode("\x03"));
		else if (key.name === "escape") input.write(this.shellCodec.encode("\x1b"));
		else if (key.text) input.write(this.shellCodec.encode(key.text));
	}
	private async finishSetup(result: SetupResult | undefined): Promise<void> {
		const wizard = this.setupWizard;
		if (!wizard) return;
		const operationId = ++this.setupOperationId;
		const operationAbort = new AbortController();
		wizard.oauthAbort?.abort(new Error("Setup operation replaced."));
		wizard.oauthAbort = operationAbort;
		if (!result) {
			operationAbort.abort(new Error("Setup cancelled by user."));
			wizard.oauthAbort = undefined;
			this.setupWizard = undefined;
			this.dispatch({ type: "overlay", value: "none" });
			const anyRouteReady = await this.hasAnyConfiguredCredential();
			this.record(
				anyRouteReady ? "status" : "warning",
				anyRouteReady
					? "Setup cancelled. Existing provider routes remain available; use /model or /graph to choose where they are used."
					: "Setup cancelled. Configure at least one provider with /setup or /auth set before sending prompts.",
			);
			wizard.resolve(false);
			this.render();
			return;
		}
		wizard.busy = true;
		this.render();
		try {
			if (result.authMode === "oauth" && !wizard.credentialReady) {
				throw new Error("OAuth setup must complete before selecting a model.");
			} else if (result.authMode === "api" && !wizard.credentialReady) {
				if (!result.apiKey) throw new Error("API key must not be empty");
				await this.options.client.setApiKey(result.providerId, result.apiKey, { signal: operationAbort.signal });
			}
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			if (typeof this.options.client.switchModel === "function") {
				// switchModel is the single application boundary for discovery,
				// provenance persistence, runtime rebuild, and user-scope writes.
				// Setup must use it too; writing a half-populated model directly is
				// how the old flow produced ?/? and a stale 128K runtime.
				await this.options.client.switchModel(
					{
						provider: result.providerId,
						modelName: result.modelName,
						discoveredModel: result.discoveredModel,
						baseUrl: result.baseUrl,
						authMode: result.authMode,
						scope: "user",
					},
					{ signal: operationAbort.signal },
				);
			} else {
				await this.options.client.updateConfiguration(
					{
						model: {
							provider: result.providerId,
							modelName: result.modelName,
							authMode: result.authMode,
							provenance: {
								contextLength: "unknown",
								capabilities: "unknown",
								maxContextSize: "unknown",
								maxOutputTokens: "unknown",
							},
							...(result.baseUrl ? { baseUrl: result.baseUrl } : {}),
						},
					},
					"user",
					{ signal: operationAbort.signal },
				);
			}
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
		} catch (error) {
			if (wizard.oauthAbort === operationAbort) wizard.oauthAbort = undefined;
			if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
			// Keep the wizard and its resolver alive on failure. The previous
			// implementation cleared both before awaiting I/O, leaving the
			// startup gate permanently suspended when discovery/config failed.
			wizard.controller.error = messageOf(error);
			wizard.busy = false;
			this.dispatch({ type: "overlay", value: "setup" });
			this.record("error", `Setup failed: ${messageOf(error)}. Press Enter to retry.`);
			this.render();
			return;
		}
		if (wizard.oauthAbort === operationAbort) wizard.oauthAbort = undefined;
		if (this.setupWizard !== wizard || this.setupOperationId !== operationId) return;
		this.setupWizard = undefined;
		this.dispatch({ type: "overlay", value: "none" });
		this.record("status", `Setup complete: ${result.providerId} / ${result.modelName}.`);
		wizard.resolve(true);
		// Setup can be launched from an already-running TUI. Refresh the footer
		// after the central route switch so it cannot retain the old ?/? metadata.
		await this.refreshRuntimeModel();
		this.render();
	}
	/** Commit guard: keys dispatch without a queue, so an answer already in flight
	 * swallows further answer keys instead of answering the same request twice. */
	private async answerInteractionGuarded(rawAnswer: string): Promise<boolean> {
		if (this.interactionBusy) return false;
		this.interactionBusy = true;
		this.render();
		try {
			return await this.answerInteraction(rawAnswer);
		} finally {
			this.interactionBusy = false;
			this.render();
		}
	}
	private async answerInteraction(rawAnswer: string): Promise<boolean> {
		const pending = this.pendingInteractions[0];
		if (!pending) {
			this.dispatch({ type: "overlay", value: "none" });
			return false;
		}
		let responded: boolean;
		try {
			if (pending.kind === "approval") {
				responded = await this.options.client.respondToInteraction({
					sessionId: pending.sessionId,
					requestId: pending.request.id,
					kind: "approval",
					decision: approvalDecision(rawAnswer),
					...(this.approvalFeedback.trim() ? { feedback: this.approvalFeedback.trim() } : {}),
				});
			} else {
				if (!isQuestionAnswer(rawAnswer)) {
					this.record("warning", "A question requires an answer.");
					this.render();
					return false;
				}
				responded = await this.options.client.respondToInteraction({
					sessionId: pending.sessionId,
					requestId: pending.request.id,
					kind: "question",
					answer: rawAnswer,
				});
			}
		} catch (error) {
			this.record("error", `Interaction failed: ${messageOf(error)}`);
			this.render();
			return false;
		}
		// A false response means the request was already resolved elsewhere; say so
		// instead of silently claiming the answer landed.
		if (!responded) this.record("warning", "That request was already resolved or has expired.");
		await this.refreshPendingInteractions();
		const next = this.pendingInteractions[0];
		if (next) this.showModal(next.kind === "approval" ? "approval" : "question");
		else this.dispatch({ type: "overlay", value: "none" });
		this.render();
		return responded;
	}
	private async switchSession(session: SessionClient): Promise<void> {
		const previousTask = this.eventTask;
		const droppedQueue = this.state.queue.length;
		const dismissedInteractions = this.pendingInteractions.length;
		this.eventGeneration++;
		await this.eventStream.stop();
		await previousTask?.catch(() => {});
		this.session = session;
		this.sessionPicker = undefined;
		// Pending approvals/questions belong to the previous session's runtime;
		// leaving them answerable after the switch would target a dead request.
		this.pendingInteractions = [];
		if (this.state.overlay === "approval" || this.state.overlay === "question")
			this.dispatch({ type: "overlay", value: "none" });
		// The pending-learning badge belongs to the previous session; it refills
		// from the next learning diagnostic or /learn panel activity.
		this.learningPendingCount = undefined;
		this.viewport.reset();
		this.clearLiveReconciliation();
		this.dispatch({ type: "reset-session", value: session.id });
		this.record("system", `Switched to session ${shortId(session.id)}.`);
		if (dismissedInteractions > 0)
			this.record("status", "Pending approvals or questions from the previous session were dismissed.");
		if (droppedQueue > 0)
			this.record(
				"warning",
				`${droppedQueue} queued prompt${droppedQueue === 1 ? "" : "s"} from the previous session ${droppedQueue === 1 ? "was" : "were"} dropped.`,
			);
		this.eventTask = this.consumeEvents(session, this.eventGeneration);
		await this.refreshRuntimeModel();
		this.render();
	}
	/** Reset must discard references before reducer state is replaced for a new session. */
	private clearLiveReconciliation(): void {
		this.liveTranscript.clear();
	}
	private async showSessions(initialSearch = ""): Promise<void> {
		this.sessionScope = "cwd";
		let sessions = await this.options.client.listSessions({ cwd: this.options.cwd });
		let picker = new SelectableList(sessions, sessionSearchLabel);
		if (initialSearch) {
			picker.append(initialSearch);
			if (!picker.visible().length) {
				sessions = await this.options.client.listSessions({});
				picker = new SelectableList(sessions, sessionSearchLabel);
				picker.append(initialSearch);
				if (picker.visible().length) this.sessionScope = "all";
			}
		}
		this.sessionPicker = picker;
		this.sessionPicker.onCancel = () => {
			this.sessionPicker = undefined;
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
		};
		this.modalViewport.reset();
		this.showModal("sessions");
		this.ensureSelectedSessionVisible();
	}
	private async reloadSessionPicker(picker: SelectableList<SessionSummary>): Promise<void> {
		if (this.sessionReloadBusy || this.sessionPicker !== picker || this.closed) return;
		this.sessionReloadBusy = true;
		try {
			const sessions = await this.options.client.listSessions({
				cwd: this.sessionScope === "cwd" ? this.options.cwd : undefined,
			});
			if (this.sessionPicker !== picker || this.closed) return;
			picker.setItems(sessions);
			this.ensureSelectedSessionVisible();
			this.render();
		} catch (error) {
			this.record("error", `Session list failed: ${messageOf(error)}`);
			this.render();
		} finally {
			this.sessionReloadBusy = false;
		}
	}
	/** Convert completed @file mentions into the same trusted prompt parts used by headless clients. */
	private async materializeComposerMentions(value: string): Promise<{ text: string; attachments: PromptPart[] }> {
		const attachments: PromptPart[] = [];
		const consumed = new Set<string>();
		const mention = /(^|\s)@([^\s]+)/gu;
		let text = value;
		for (const match of value.matchAll(mention)) {
			const token = match[2];
			if (!token || consumed.has(token)) continue;
			const part = await this.resolveAttachmentPart(token);
			if (!part) continue;
			consumed.add(token);
			attachments.push(part);
			text = text.replace(`${match[1] ?? ""}@${token}`, match[1] ?? "");
		}
		return { text: text.replace(/\s{2,}/g, " ").trim(), attachments };
	}
	private async resolveAttachmentPart(value: string): Promise<PromptPart | undefined> {
		const root = await realpath(this.options.cwd).catch(() => path.resolve(this.options.cwd));
		const candidate = path.resolve(root, value);
		const filePath = await realpath(candidate).catch(() => undefined);
		if (!filePath) return undefined;
		const relative = path.relative(root, filePath);
		if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative))
			throw new Error("Attachment must remain inside the trusted workspace.");
		const info = await stat(filePath);
		if (!info.isFile()) return undefined;
		if (info.size > 20 * 1024 * 1024) throw new Error("Attachment exceeds 20 MiB.");
		const ext = path.extname(filePath).toLowerCase();
		const mimeType =
			ext === ".png"
				? "image/png"
				: ext === ".jpg" || ext === ".jpeg"
					? "image/jpeg"
					: ext === ".gif"
						? "image/gif"
						: ext === ".webp"
							? "image/webp"
							: undefined;
		return { type: mimeType ? "image_url" : "file", path: filePath, mimeType };
	}
	private async openEditor(): Promise<void> {
		const editor = resolveEditorCommand();
		if (!editor) {
			this.record("warning", "No editor configured. Set $VISUAL or $EDITOR.");
			this.render();
			return;
		}
		this.renderer.stopAnimation();
		this.leased = true;
		try {
			await this.terminal.withTerminal(async () => {
				const value = await editDraft(this.editor.text, editor);
				if (value !== undefined) this.editor.set(value.replaceAll("\r\n", "\n").replace(/\n$/, ""));
			});
		} finally {
			this.leased = false;
		}
		this.render();
	}
	private async openShell(): Promise<void> {
		if (this.shellProcess) return;
		this.renderer.stopAnimation();
		const executable =
			process.platform === "win32" ? (process.env["ComSpec"] ?? "cmd.exe") : (process.env["SHELL"] ?? "/bin/sh");
		const shellHeader = [
			`Embedded shell · ${executable}`,
			`cwd: ${this.options.cwd}`,
			"Type commands; Enter runs · F2 returns to Kageko · Ctrl-C interrupts the current shell command",
		];
		this.shellLines = [...shellHeader];
		this.showModal("shell");
		const child = spawn(executable, { cwd: this.options.cwd, stdio: "pipe", windowsHide: true });
		this.shellProcess = child;
		const encoding = resolveShellEncoding(process.platform, executable);
		const stdoutCodec = new ShellCodec(encoding);
		const stderrCodec = new ShellCodec(encoding);
		this.shellCodec = new ShellCodec(encoding);
		let output = "";
		const appendText = (value: string) => {
			output += value;
			// Bound retained output without cutting encoded bytes: decoding has
			// already completed, so slicing here can only remove whole JS text.
			if (output.length > 200_000) output = output.slice(-100_000);
			const lines = output.replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n");
			this.shellLines = [...shellHeader, ...lines.slice(-197)];
			this.render();
		};
		child.stdout?.on("data", (value: Buffer | string) => appendText(stdoutCodec.decode(value)));
		child.stderr?.on("data", (value: Buffer | string) => appendText(stderrCodec.decode(value)));
		child.stdout?.once("end", () => appendText(stdoutCodec.end()));
		child.stderr?.once("end", () => appendText(stderrCodec.end()));
		child.once("error", (error) => {
			appendText(`\nshell error: ${messageOf(error)}\n`);
			void this.closeEmbeddedShell();
		});
		child.once("exit", (code) => {
			appendText(`\nshell exited (${code ?? "signal"})\n`);
			this.shellProcess = undefined;
			this.dispatch({ type: "overlay", value: "none" });
			this.render();
		});
		this.render();
	}
	private async closeEmbeddedShell(): Promise<void> {
		const child = this.shellProcess;
		if (!child) return;
		const exited = new Promise<void>((resolve) => {
			if (child.exitCode !== null || child.signalCode !== null) resolve();
			else {
				child.once("exit", () => resolve());
				child.once("error", () => resolve());
			}
		});
		if (!child.killed) child.kill();
		await exited;
		if (this.shellProcess === child) this.shellProcess = undefined;
		this.dispatch({ type: "overlay", value: "none" });
		this.record("status", "Returned to Kageko TUI.");
		this.render();
	}
	private async suspend(): Promise<void> {
		this.record("warning", "Use /shell for an embedded shell; the TUI stays active there.");
		this.render();
	}

	private render(): void {
		if (this.inputDispatchDepth > 0) {
			this.inputRenderPending = true;
			return;
		}
		if (!this.renderRateLimitActive) {
			this.renderFrame();
			return;
		}
		const now = Date.now();
		const elapsed = now - this.lastRenderAt;
		if (this.lastRenderAt === 0 || elapsed >= 16) {
			if (this.renderTimer) clearTimeout(this.renderTimer);
			this.renderTimer = undefined;
			this.renderPending = false;
			this.lastRenderAt = now;
			this.renderFrame();
			return;
		}
		this.renderPending = true;
		if (this.renderTimer) return;
		this.renderTimer = setTimeout(
			() => {
				this.renderTimer = undefined;
				if (!this.renderPending || this.closed) return;
				this.renderPending = false;
				this.lastRenderAt = Date.now();
				this.renderFrame();
			},
			Math.max(1, 16 - elapsed),
		);
		this.renderTimer.unref?.();
	}

	private renderFrame(): void {
		if (this.closed || this.leased) return;
		if (this.immediateInputDepth > 0) {
			this.immediateRenderPending = true;
			return;
		}
		const running =
			this.state.turnLive ||
			this.state.submitting ||
			[...this.state.activities.values()].some((entry) => entry.state === "running");
		if (running)
			this.renderer.startAnimation(() => {
				this.tickCount += 1;
				this.render();
			});
		else this.renderer.stopAnimation();
		const spinnerFrame = SPINNER_FRAMES[this.tickCount % SPINNER_FRAMES.length]!;
		const tipIndex = Math.floor(this.tickCount / 80) % ACTIVITY_TIPS.length;
		const { columns, rows } = this.terminal.size();
		this.editor.setVisualWidth(Math.max(4, columns - 4));
		this.questionEditor.setVisualWidth(Math.max(4, columns - 4));
		let header = wrapRenderRows(
			welcomeLines({ cwd: this.options.cwd, sessionId: this.session?.id, model: this.runtimeModelLabel() }, columns),
			columns,
		);
		let footer = wrapRenderRows(
			footerLines(
				this.state.overlay,
				{
					atTail: this.viewport.scrollOffset === 0,
					queued: this.state.queue.length,
					cwd: this.options.cwd,
					model: this.runtimeModelLabel(),
					contextUsed: this.runtimeModel.contextUsed,
					contextLength: this.runtimeModel.contextLimit ?? this.runtimeModel.contextLength,
					contextUsedSource: this.runtimeModel.contextUsedSource,
					contextLimitSource: this.runtimeModel.contextLimit
						? this.runtimeModel.contextLimitSource
						: this.runtimeModel.contextLengthSource,
					permissionProfile: this.runtimePolicies.permissionProfile,
					interactionMode: this.runtimePolicies.interactionMode,
					learningPending: this.learningPendingCount,
				},
				columns,
			),
			columns,
		);
		const composer =
			this.state.overlay === "none" || this.state.overlay === "question"
				? composerLines({
						columns,
						maxRows: Math.max(3, Math.min(6, rows - 3)),
						text: this.state.overlay === "question" ? this.questionEditor.text : this.editor.text,
						cursorIndex: this.state.overlay === "question" ? this.questionEditor.cursorIndex : this.editor.cursorIndex,
						placeholder: this.state.overlay === "question" ? "Type your answer…" : "Ask Kageko…",
						focused: this.terminal.isFocused(),
					})
				: { lines: [] as readonly RenderRow[], cursorRow: 0, cursorColumn: 0, hiddenAbove: 0 };
		let completion = wrapRenderRows(this.completionLines(columns), columns);
		let panel = this.state.overlay === "none" ? [] : wrapRenderRows(this.modalPanelLines(columns), columns);
		const activities = activityLines([...this.state.activities.values()], { spinnerFrame, tipIndex });
		const lowerLogical =
			this.state.overlay === "none"
				? columns >= 60
					? [
							...activities,
							row({ text: "─".repeat(Math.max(1, columns - 4)), tone: "surface", dim: true }),
							...queueLines(this.state.queue),
						]
					: [...activities.slice(0, 1), ...queueLines(this.state.queue).slice(0, 2)]
				: [];
		let lower = wrapRenderRows(lowerLogical, columns);
		// Enforce a strict region budget: preserve an active composer row first.
		const over = () =>
			header.length + footer.length + panel.length + lower.length + completion.length >= Math.max(0, rows - 1);
		if (over())
			header = wrapRenderRows(
				welcomeLines(
					{ cwd: this.options.cwd, sessionId: this.session?.id, model: this.runtimeModelLabel() },
					Math.min(columns, 39),
				),
				columns,
			);
		if (over()) footer = footer.slice(0, 1);
		if (over() && completion.length) completion = wrapRenderRows(this.compactCompletionLines(columns), columns);
		if (over()) lower = lower.slice(0, 1);
		if (over()) panel = panel.slice(0, Math.max(0, rows - 2));
		if (over() && completion.length > 1) completion = completion.slice(0, 1);
		const fullComposer = wrapRenderRows(composer.lines, columns);
		const composerBudget = Math.max(
			1,
			rows - header.length - footer.length - panel.length - lower.length - completion.length,
		);
		// Window the box around the cursor row so the active line stays visible.
		const composerStart = Math.max(
			0,
			Math.min(
				fullComposer.length - composerBudget,
				wrapRenderRows(composer.lines.slice(0, composer.cursorRow), columns).length - composerBudget + 1,
			),
		);
		const physicalComposer = fullComposer.slice(composerStart);
		const reserved =
			header.length + footer.length + physicalComposer.length + completion.length + lower.length + panel.length;
		const bodyRows = Math.max(this.state.overlay !== "none" && rows >= 12 ? 2 : 0, rows - reserved);
		const body = transcriptPhysicalSlice(
			this.state.transcript,
			columns,
			this.viewport.scrollOffset,
			bodyRows,
			spinnerFrame,
		);
		const composerBefore = wrapRenderRows(composer.lines.slice(0, composer.cursorRow), columns).length;
		const composerCursorRow = composerBefore - composerStart;
		const cursor =
			composerCursorRow >= 0 && composerCursorRow < physicalComposer.length
				? {
						row:
							header.length + body.lines.length + panel.length + lower.length + completion.length + composerCursorRow,
						column: Math.min(columns - 1, composer.cursorColumn + 2),
					}
				: undefined;
		this.renderer.render({
			lines: [...header, ...body.lines, ...panel, ...lower, ...completion, ...physicalComposer, ...footer],
			cursor,
		});
	}
	private modalLines(): readonly RenderRow[] {
		if (this.state.overlay === "panel") return this.interactivePanelLines();
		if (this.state.overlay === "help")
			return helpDialogLines().map((line) => row({ text: line.text, tone: line.tone, bold: line.bold, dim: line.dim }));
		if (this.state.overlay === "sessions") {
			const picker = this.sessionPicker;
			const items = picker?.visible() ?? [];
			return [
				...(this.sessionActionBusy ? [row({ text: "Resuming selected session…", tone: "primary", bold: true })] : []),
				row(
					{ text: "Search: ", tone: "faint" },
					{ text: picker?.filter || "", tone: "default" },
					{ text: "_", tone: "faint" },
				),
				row({
					text: `${items.length} sessions · ${this.sessionScope === "cwd" ? "current cwd" : "all workspaces"} · Ctrl+A switch scope`,
					tone: "faint",
					dim: true,
				}),
				...(items.length
					? items.map((item, index) => {
							const selected = index === picker!.selectedIndex;
							const label = `${shortId(item.sessionId)}  ${item.archived ? "archived" : "active"}  ${item.title ?? item.cwd}`;
							const current =
								item.sessionId === this.session?.id ? [{ text: " ← current", tone: "success" as const }] : [];
							return selected
								? row(
										{ text: "  ", tone: "strong", background: "primary", bold: true },
										{ text: label, tone: "strong", background: "primary", bold: true },
										...current.map((span) => ({ ...span, tone: "strong" as const, background: "primary" as const })),
									)
								: row({ text: "  ", tone: "default" }, { text: label, tone: "default" }, ...current);
						})
					: [row({ text: "No matching sessions.", tone: "faint" })]),
			];
		}
		if (["activities", "details"].includes(this.state.overlay))
			return this.activityLines.map((text) => row({ text, tone: "default" }));
		if (this.state.overlay === "shell") return this.shellLines.map((text) => row({ text, tone: "default" }));
		if (this.state.overlay === "setup") {
			const wizard = this.setupWizard;
			if (!wizard) return [row({ text: "Setup unavailable.", tone: "faint" })];
			const { controller } = wizard;
			if (wizard.busy)
				return [
					row({ text: `Connecting ${controller.provider.label}…`, tone: "primary", bold: true }),
					row({
						text: controller.status ?? "Finish the provider verification, then Kageko will load its models.",
						tone: "faint",
					}),
					...(wizard.oauthUrl ? [row({ text: `URL: ${wizard.oauthUrl}`, tone: "strong" })] : []),
					...(wizard.oauthCode ? [row({ text: `Code: ${wizard.oauthCode}`, tone: "strong", bold: true })] : []),
					...(wizard.oauthPrompt ? this.oauthPromptLines(wizard.oauthPrompt) : []),
				];
			if (controller.step === "provider") {
				return [
					row({ text: "Provider · step 1 of 2", tone: "primary", bold: true }),
					row({ text: "Choose a provider and authentication route:", tone: "faint" }),
					...SETUP_PROVIDERS.map((entry, index) =>
						index === controller.providerIndex
							? row(
									{ text: "  ", tone: "strong", background: "primary", bold: true },
									{ text: entry.label, tone: "strong", background: "primary", bold: true },
									{ text: `  ${entry.authMode === "oauth" ? "OAuth" : "API key"}`, tone: "faint" },
								)
							: row(
									{ text: "  ", tone: "default" },
									{ text: entry.label, tone: "default" },
									{ text: `  ${entry.authMode === "oauth" ? "OAuth" : "API key"}`, tone: "faint" },
								),
					),
				];
			}
			if (controller.step === "oauth")
				return [
					row({ text: "Authentication · step 2 of 2", tone: "primary", bold: true }),
					row({ text: `${controller.provider.label} uses OAuth login.`, tone: "default" }),
					row({ text: controller.status ?? "Press Enter to request a verification link/code.", tone: "faint" }),
					...(wizard.oauthUrl ? [row({ text: `URL: ${wizard.oauthUrl}`, tone: "strong" })] : []),
					...(wizard.oauthCode ? [row({ text: `Code: ${wizard.oauthCode}`, tone: "strong", bold: true })] : []),
					...(wizard.oauthPrompt ? this.oauthPromptLines(wizard.oauthPrompt) : []),
					...(controller.error ? [row({ text: controller.error, tone: "danger" })] : []),
				];
			if (controller.step === "baseUrl" || controller.step === "apiKey") {
				const label = controller.step === "baseUrl" ? "Base URL" : `API key for ${controller.provider.label}`;
				const value = controller.step === "apiKey" ? controller.maskedBuffer() : controller.buffer;
				return [
					row({ text: `Authentication · step 2 of 2`, tone: "primary", bold: true }),
					row({ text: `${label}:`, tone: "default" }),
					row({ text: `  ${value}█`, tone: "strong" }),
					...(controller.error ? [row({ text: controller.error, tone: "danger" })] : []),
				];
			}
			return [
				row({ text: "Model · step 3 of 3", tone: "primary", bold: true }),
				row({
					text: `${controller.provider.label} · authenticated  ·  Up/Down navigate · Enter select · Esc back`,
					tone: "faint",
				}),
				...(controller.modelOptions.length
					? controller.modelOptions.flatMap((model, index) => {
							const selected = index === controller.modelIndex;
							const detail = modelPickerDetail(model);
							const label = model.name ? `${model.name}  (${model.id})` : model.id;
							const choice = selected
								? row(
										{ text: "  ", tone: "strong", background: "primary", bold: true },
										{ text: label, tone: "strong", background: "primary", bold: true },
									)
								: row({ text: "  ", tone: "default" }, { text: label, tone: "default" });
							return detail ? [choice, panelRow(selected, `    ${detail}`)] : [choice];
						})
					: [
							row({ text: "No verified model list was returned for this route.", tone: "warning" }),
							row({
								text: "Type a model ID and press Enter, or press Enter with an empty field to retry.",
								tone: "faint",
							}),
							row({ text: `  ${controller.buffer}█`, tone: "strong" }),
						]),
				...(controller.error ? [row({ text: controller.error, tone: "danger" })] : []),
			];
		}
		if (this.state.overlay === "trust") {
			const pending = this.startupTrust;
			if (!pending) return [row({ text: "Workspace trust status unavailable.", tone: "faint" })];
			const { status, choice } = pending;
			return [
				...(this.trustBusy ? [row({ text: "Granting workspace trust…", tone: "primary", bold: true })] : []),
				row({ text: `Workspace: ${status.workspace}`, tone: "default" }),
				row({
					text:
						status.reason === "configuration_changed"
							? "Security configuration changed since this workspace was trusted."
							: "This workspace contains security-sensitive configuration.",
					tone: "warning",
				}),
				...(status.findings ?? []).map((finding) => row({ text: `  ${finding}`, tone: "faint" })),
				row({ text: "", tone: "default" }),
				panelRow(choice === 0, "Trust this workspace"),
				panelRow(choice === 1, "Exit"),
				...(pending.error ? [row({ text: pending.error, tone: "danger" })] : []),
			];
		}
		if (this.state.overlay === "confirm")
			return [
				row({ text: this.pendingConfirm?.message ?? "", tone: "warning" }),
				row({ text: "Choose whether to continue:", tone: "faint" }),
				panelRow(this.confirmChoice === 0, "Confirm"),
				panelRow(this.confirmChoice === 1, "Cancel"),
			];
		const pending = this.pendingInteractions[0];
		if (!pending) return [row({ text: "No pending interactions.", tone: "faint" })];
		if (pending.kind === "approval") {
			const selected = ["once", "session", "deny"][this.interactionChoice]!;
			return [
				...(this.interactionBusy ? [row({ text: "Submitting decision…", tone: "primary", bold: true })] : []),
				row({ text: pending.request.action, tone: "default" }),
				...(pending.request.risk
					? [
							row({
								text: `Risk: ${pending.request.risk}`,
								tone: pending.request.risk === "high" ? "danger" : "warning",
							}),
						]
					: []),
				...((this.approvalPreview || this.approvalOutputExpanded) && pending.request.preview
					? [
							row({ text: this.approvalOutputExpanded ? "Tool output" : "Preview", tone: "primary", bold: true }),
							...(this.approvalOutputExpanded
								? pending.request.preview.split("\n").map((line) => row({ text: `  ${line}`, tone: "code" }))
								: wrapDisplay(pending.request.preview, 76).map((line) => row({ text: `  ${line}`, tone: "code" }))),
						]
					: []),
				row({
					text: `Feedback${this.approvalEditing ? " (typing)" : ""}: ${this.approvalFeedback || "Tab to add a note"}`,
					tone: this.approvalEditing ? "strong" : "faint",
				}),
				row({ text: "1-3 choose · Enter confirm · Tab feedback · Ctrl+G preview · Ctrl+O output", tone: "faint" }),
				...["once", "session", "deny"].map((choice, index) =>
					panelRow(choice === selected, `${index + 1}. ${choice}${choice === "deny" ? " (Esc)" : ""}`),
				),
			];
		}
		const options = pending.request.options ?? [];
		return [
			...(this.interactionBusy ? [row({ text: "Submitting answer…", tone: "primary", bold: true })] : []),
			row({ text: pending.request.prompt, tone: "strong", bold: true }),
			...options.map((option, index) => panelRow(this.interactionChoice === index, `${index + 1}. ${option}`)),
			panelRow(
				this.interactionChoice === options.length,
				`${options.length + 1}. Other  ${this.questionEditor.text || "type an answer"}`,
			),
		];
	}
	private oauthPromptLines(prompt: OAuthPromptState): readonly RenderRow[] {
		if (prompt.options?.length)
			return [
				row({ text: prompt.message, tone: "default" }),
				row({ text: "Up/Down choose · Enter continue · Esc cancel", tone: "faint" }),
				...prompt.options.map((option, index) =>
					panelRow(index === prompt.selectedIndex, option.label, option.description),
				),
			];
		return [
			row({ text: prompt.message, tone: "default" }),
			row({ text: `  ${prompt.value || prompt.placeholder || ""}█`, tone: "strong" }),
		];
	}
	private interactivePanelLines(): readonly RenderRow[] {
		const panel = this.panel;
		if (!panel) return [row({ text: "Panel unavailable.", tone: "faint" })];
		if (panel.kind === "menu") {
			const items = visibleMenuItems(panel);
			return [
				...(this.panelActionBusy ? [row({ text: "Working…", tone: "primary", bold: true })] : []),
				...(this.panelActionError ? [row({ text: this.panelActionError, tone: "danger" })] : []),
				row({ text: `Search: ${panel.query || "type to filter"}`, tone: "faint" }),
				...(items.length
					? items.map((item, index) =>
							panelRow(index === panel.selected && this.panelActions.has(item.id), item.label, item.detail),
						)
					: [row({ text: "No matching actions.", tone: "warning" })]),
			];
		}
		if (panel.kind === "form") {
			return [
				...(this.panelActionBusy ? [row({ text: "Saving…", tone: "primary", bold: true })] : []),
				...(this.panelActionError ? [row({ text: this.panelActionError, tone: "danger" })] : []),
				...textInputRows(panel.label, panel.value, panel.cursorIndex, this.terminal.size().columns, {
					masked: panel.masked,
					placeholder: panel.placeholder,
					hint: panel.hint,
				}),
			];
		}
		if (panel.kind === "model") {
			const busy = panel.busyLabel ? [row({ text: panel.busyLabel, tone: "primary", bold: true })] : [];
			if (panel.step === "role")
				return [
					...busy,
					...(panel.error ? [row({ text: panel.error, tone: "danger" })] : []),
					row({ text: "Choose which agent receives the model route and reasoning:", tone: "default" }),
					...panel.targets.map((target, index) => panelRow(index === panel.targetIndex, target.label, target.detail)),
				];
			if (panel.step === "route")
				return [
					...busy,
					...(panel.error ? [row({ text: panel.error, tone: "danger" })] : []),
					row({
						text: `Choose a configured route for ${panel.targets[panel.targetIndex]?.label ?? "agent"}`,
						tone: "default",
					}),
					...(panel.routes.length
						? panel.routes.map((route, index) =>
								panelRow(
									index === panel.routeIndex,
									route.provider === "__setup__" ? route.label : `${route.label} · ${route.authMode}`,
									route.provider === "__setup__" ? "guided setup" : route.ready ? "credential ready" : "not configured",
								),
							)
						: [row({ text: "  No provider routes found. Open /setup first.", tone: "warning" })]),
				];
			if (panel.step === "model")
				return [
					...busy,
					...(panel.error ? [row({ text: panel.error, tone: "danger" })] : []),
					row({ text: `Choose a model · ${panel.routes[panel.routeIndex]?.label ?? "route"}`, tone: "default" }),
					row({
						text: `Search: ${panel.modelQuery || "type to filter"} · Left/Right reasoning · Esc clear/back`,
						tone: "faint",
					}),
					...(visibleModelChoices(panel).length
						? visibleModelChoices(panel).map((model, index) =>
								panelRow(
									index === panel.modelIndex,
									model.name ? `${model.name} (${model.id})` : model.id,
									modelPickerDetail(model),
								),
							)
						: [row({ text: "No models match this search.", tone: "warning" })]),
					...(visibleModelChoices(panel)[panel.modelIndex]?.reasoningLevels?.length
						? [
								row({
									text: `Reasoning: ${visibleModelChoices(panel)
										[panel.modelIndex]!.reasoningLevels!.map((level, index) =>
											index === panel.reasoningIndex ? `[ ${level} ]` : `  ${level}  `,
										)
										.join(" ")}`,
									tone: "primary",
								}),
							]
						: []),
				];
			const selected = visibleModelChoices(panel)[panel.modelIndex];
			return selected
				? [
						...busy,
						...modelConfirmActions(panel).map((action, index) =>
							panelRow(
								index === panel.confirmIndex,
								action === "permanent"
									? "Apply permanently"
									: action === "session"
										? "Apply for this session"
										: action === "policy"
											? "Edit agent policy"
											: action === "retry"
												? "Retry provider discovery"
												: "Choose another model",
							),
						),
						row({
							text: `${panel.targets[panel.targetIndex]?.label ?? "Agent"} · ${panel.routes[panel.routeIndex]?.label ?? "route unavailable"} · ${selected.name ? `${selected.name} (${selected.id})` : selected.id}`,
							tone: "default",
						}),
						...(typeof panel.contextLimitOverride === "number"
							? [
									row({
										text: `Local context limit override: ${formatTokenCount(panel.contextLimitOverride)}`,
										tone: "warning",
									}),
								]
							: []),
						...(modelMetadataStatus(selected).complete
							? []
							: [
									row({
										text: `Metadata incomplete: ${modelMetadataStatus(selected).missing.join(", ")} · choose Retry provider discovery`,
										tone: "warning",
									}),
								]),
						row({ text: `Metadata: ${metadataOriginLabel(selected)}`, tone: "faint" }),
						...(panel.error ? [row({ text: panel.error, tone: "danger" })] : []),
					]
				: [row({ text: panel.error ?? "No model selected.", tone: "warning" })];
		}
		const value = panel.config[panel.target.id] ?? {};
		return [
			...(panel.busyLabel ? [row({ text: panel.busyLabel, tone: "primary", bold: true })] : []),
			...(panel.error ? [row({ text: panel.error, tone: "danger" })] : []),
			row({ text: `Policy · ${panel.target.label}`, tone: "default" }),
			...panel.fields.map((field, index) => {
				const selected = index === panel.fieldIndex;
				const display =
					field === "route"
						? `${String(value["provider"] ?? "inherit")} / ${String(value["modelName"] ?? "inherit")} · ${String(value["authMode"] ?? "inherit")}`
						: field === "remove"
							? "Permanently delete this profile"
							: field === "tools"
								? formatWorkerToolSelection(value["tools"])
							: Array.isArray(value[field])
								? value[field].join(",")
								: String(value[field] ?? "inherit");
				return panelRow(selected, graphFieldLabel(field), display);
			}),
			...(panel.editing
				? textInputRows(
						graphFieldLabel(panel.editing.field),
						panel.editing.value,
						panel.editing.cursorIndex,
						this.terminal.size().columns,
						{ hint: graphFieldHint(panel.editing.field) },
					)
				: []),
		];
	}
	private modalPanelLines(columns: number): readonly RenderRow[] {
		const overlay = this.state.overlay;
		const title =
			overlay === "sessions"
				? "Sessions"
				: overlay === "approval"
					? "Run this command?"
					: overlay === "question"
						? "Question"
						: overlay === "help"
							? "Help"
							: overlay === "details"
								? "Activity details"
								: overlay === "confirm"
									? "Confirm"
									: overlay === "trust"
										? "Workspace trust"
										: overlay === "setup"
											? "Setup"
											: overlay === "shell"
												? "Embedded shell"
												: overlay === "panel"
													? this.panel?.kind === "model"
														? this.panel.step === "confirm"
															? "Apply model"
															: "Choose model"
														: this.panel?.kind === "graph"
															? "Agent graph"
															: this.panel?.kind === "form"
																? this.panel.title
																: (this.panel?.title ?? "Choose")
													: "Activities";
		const hint =
			(
			overlay === "sessions"
				? this.sessionActionBusy
					? "Resuming… · Esc cancel"
					: "Up/Down navigate · Enter resume · Esc cancel"
				: overlay === "approval"
					? this.interactionBusy
						? "Submitting…"
						: "Up/Down navigate · Enter confirm · Esc deny"
					: overlay === "question"
						? this.interactionBusy
							? "Submitting…"
							: "Up/Down navigate · Enter select · Esc close"
						: overlay === "help"
							? "PgUp/PgDn scroll · Esc close"
							: overlay === "confirm"
								? "Up/Down choose · Enter select · Esc cancel"
								: overlay === "trust"
									? this.trustBusy
										? "Granting trust…"
										: "Up/Down navigate · Enter select · Esc exit"
									: overlay === "setup"
										? this.setupWizard?.busy
											? "Connecting… Esc cancel"
											: this.setupWizard?.controller.step === "provider"
												? "Up/Down choose · Enter connect · Esc cancel"
												: this.setupWizard?.controller.step === "model"
													? "Up/Down choose model · Enter save · Esc back"
													: "Enter continue · Esc back"
										: overlay === "shell"
											? "Enter run · F2 return to TUI · Ctrl-C interrupt"
											: overlay === "panel"
												? this.panelActionBusy
													? "Working… · Esc back"
													: (this.panel?.kind === "model" || this.panel?.kind === "graph") && this.panel.busy
														? `${this.panel.busyLabel ?? "Working…"} · Esc cancel`
														: this.panel?.kind === "form"
															? "Type · Enter save · Esc back"
															: this.panel?.kind === "model" && this.panel.step === "confirm"
											? "Up/Down choose action · Enter apply · Esc models"
																: this.panel?.kind === "menu" && this.panel.title.startsWith("Worker tools")
																	? "Type to filter · Enter toggle · Save selection · Esc back"
											: "Up/Down navigate · Enter select · Esc back"
								: "PgUp/PgDn scroll · Esc close");
		const barTone = overlay === "approval" || overlay === "trust" ? ("warning" as const) : ("surface" as const);
		const bar = "─".repeat(Math.max(1, columns));
		const all = this.modalLines();
		const limit = this.modalLimit(columns);
		const selected = all.findIndex((entry) => entry.spans.some((span) => span.background !== undefined));
		const compact = columns < 60 && selected >= 0;
		const body = compact
			? [all[0]!, all[selected]!].filter((line, index, values) => values.indexOf(line) === index).slice(0, limit)
			: this.modalViewport.sliceFromStart(all, limit);
		const more = columns < 60 ? 0 : Math.max(0, all.length - this.modalViewport.scrollOffset - body.length);
		if (overlay === "setup") return this.setupModalFrame(columns, title, hint, body);
		return [
			row({ text: bar, tone: barTone }),
			row(
				{
					text: truncateDisplay(` ${title}`, columns),
					tone: overlay === "approval" ? "strong" : "primary",
					bold: true,
				},
				...(overlay === "sessions" && columns >= 60 ? [{ text: " (type to search)", tone: "faint" as const }] : []),
			),
			row({ text: truncateDisplay(` ${hint}`, columns), tone: "faint" }),
			...body.map((entry) => row({ text: " ", tone: "default" }, ...entry.spans)),
			...(more > 0 ? [row({ text: ` ▼ ${more} more`, tone: "faint" })] : []),
			row({ text: bar, tone: barTone }),
		];
	}
	private setupModalFrame(
		columns: number,
		title: string,
		hint: string,
		body: readonly RenderRow[],
	): readonly RenderRow[] {
		const width = Math.max(1, Math.min(92, columns - 2));
		const left = Math.max(0, Math.floor((columns - width) / 2));
		const inner = Math.max(1, width - 4);
		const prefix = " ".repeat(left);
		const border = (start: string, end: string): RenderRow =>
			row({ text: `${prefix}${start}${"─".repeat(Math.max(1, width - 2))}${end}`, tone: "surface" });
		const line = (
			text: string,
			tone: "primary" | "faint" | "default" | "warning" | "danger" = "default",
			background?: "primary",
		): RenderRow => {
			const clipped = truncateDisplay(text, inner);
			const padding = Math.max(0, inner - displayWidth(clipped));
			return row(
				{ text: `${prefix}│ `, tone: "surface", ...(background ? { background } : {}) },
				{ text: clipped, tone, ...(background ? { background } : {}) },
				{ text: `${" ".repeat(padding)} │`, tone: "surface", ...(background ? { background } : {}) },
			);
		};
		return [
			border("╭", "╮"),
			line(title, "primary"),
			line(hint, "faint"),
			...body.map((entry) => {
				const selected = entry.spans.some((span) => span.background !== undefined);
				return line(renderRowText(entry), selected ? "primary" : "default", selected ? "primary" : undefined);
			}),
			border("╰", "╯"),
		];
	}
	private completionLines(columns: number): readonly RenderRow[] {
		const menu = this.completion;
		if (!menu) return [];
		const window = columns < 60 ? 3 : 6;
		const start = Math.max(
			0,
			Math.min(Math.max(0, menu.values.length - window), menu.selected - Math.floor(window / 2)),
		);
		const values = menu.values.slice(start, start + window);
		return [
			row({
				text: ` ${menu.kind === "/" ? "Commands" : "Files"}${start ? "  ↑" : ""}${start + values.length < menu.values.length ? `  … +${menu.values.length - start - values.length}` : ""}`,
				tone: "primary",
				bold: true,
			}),
			...values.map((value) => {
				const selected = value === menu.values[menu.selected];
				const command = menu.kind === "/" ? findSlashCommand(value.slice(1)) : undefined;
				const description = command?.description;
				const hint = command?.argumentHint ? ` · ${command.argumentHint}` : "";
				if (selected) {
					return panelRow(
						true,
						value,
						description ? truncateDisplay(`${description}${hint}`, Math.max(8, columns - value.length - 6)) : undefined,
					);
				}
				return row(
					{ text: "  ", tone: "default" },
					{ text: value, tone: "faint" },
					...(description
						? [
								{
									text: ` — ${truncateDisplay(`${description}${hint}`, Math.max(8, columns - value.length - 6))}`,
									tone: "faint" as const,
								},
							]
						: []),
				);
			}),
			row({ text: " Up/Down select · Tab/Enter insert · F2 embedded shell · Esc dismiss", tone: "faint", dim: true }),
		];
	}
	private compactCompletionLines(columns: number): readonly RenderRow[] {
		const menu = this.completion;
		const selected = menu?.values[menu.selected];
		if (!menu || !selected) return [];
		return [
			row({ text: ` ${menu.kind === "/" ? "Commands" : "Files"}  …`, tone: "primary", bold: true }),
			panelRow(true, truncateDisplay(selected, Math.max(1, columns - 4))),
		];
	}
	private scrollTranscript(delta: number): void {
		const columns = this.terminal.size().columns;
		this.viewport.move(delta, transcriptPhysicalRowCount(this.state.transcript, columns), this.bodyRows());
	}
	private scrollModal(delta: number): void {
		this.modalViewport.moveFromStart(delta, this.modalLines().length, this.modalVisibleRows());
	}
	private modalLimit(columns: number): number {
		const availableBodyRows = Math.max(2, this.bodyRows() - 4);
		return columns < 60 ? Math.min(4, availableBodyRows) : availableBodyRows;
	}
	private modalVisibleRows(): number {
		return Math.min(this.modalLimit(this.terminal.size().columns), Math.max(1, this.bodyRows()));
	}
	private bodyRows(): number {
		const size = this.terminal.size();
		const composerRows =
			this.state.overlay === "none" || this.state.overlay === "question"
				? composerLines({
						columns: size.columns,
						maxRows: Math.max(3, Math.min(6, size.rows - 3)),
						text: this.editor.text,
						cursorIndex: this.editor.cursorIndex,
						placeholder: "Ask Kageko…",
					}).lines.length
				: 0;
		return allocateLayout(
			size.columns,
			size.rows,
			composerRows,
			this.state.activities.size > 0 || this.state.queue.length > 0,
		).bodyRows;
	}
	private showModal(overlay: Exclude<Overlay, "none">): void {
		this.modalViewport.reset();
		if (overlay === "approval") this.interactionChoice = 2;
		if (overlay === "approval") {
			this.approvalFeedback = "";
			this.approvalEditing = false;
			this.approvalPreview = false;
			this.approvalOutputExpanded = false;
		}
		if (overlay === "question") {
			this.interactionChoice = 0;
			this.questionEditor.clear();
		}
		// Setup/auth uses its own staged Hermes flow. All other surfaces are
		// regular Kimi-style capturing overlays with focus restoration.
		if (overlay !== "setup") {
			if (!this.normalOverlayStack.contains(overlay)) {
				this.normalOverlayHandles.set(
					overlay,
					this.normalOverlayStack.show(overlay, this.normalOverlayComponent(overlay)),
				);
			} else this.normalOverlayHandles.get(overlay)?.focus();
		}
		this.dispatch({ type: "overlay", value: overlay });
	}
	private ensureSelectedSessionVisible(): void {
		if (this.state.overlay !== "sessions" || !this.sessionPicker) return;
		const lines = this.modalLines();
		const selectedLine = this.sessionPicker.selectedIndex + 2;
		this.modalViewport.ensureVisibleFromStart(selectedLine, selectedLine, lines.length, this.modalVisibleRows());
	}
	private ensureSelectedModalVisible(): void {
		if (this.state.overlay === "sessions") {
			this.ensureSelectedSessionVisible();
			return;
		}
		if (this.state.overlay === "panel" && this.panel) {
			const lines = this.modalLines();
			const highlighted = lines.findIndex((line) => line.spans.some((span) => span.background !== undefined));
			const selectedLine =
				this.panel.kind === "graph" && this.panel.editing
					? Number(Boolean(this.panel.busyLabel)) +
						Number(Boolean(this.panel.error)) +
						this.panel.fields.length +
						3
					: highlighted >= 0
						? highlighted
						: 0;
			this.modalViewport.ensureVisibleFromStart(selectedLine, selectedLine, lines.length, this.modalVisibleRows());
			return;
		}
		if (this.state.overlay !== "setup") return;
		const lines = this.modalLines();
		const controller = this.setupWizard?.controller;
		if (!controller) return;
		const selectedLine =
			controller.step === "provider"
				? controller.providerIndex + 2
				: controller.step === "model"
					? 2 +
						controller.modelOptions
							.slice(0, controller.modelIndex)
							.reduce((line, model) => line + (modelPickerDetail(model) ? 2 : 1), 0)
					: 1;
		this.modalViewport.ensureVisibleFromStart(selectedLine, selectedLine, lines.length, this.modalVisibleRows());
	}
	private runtimeModelLabel(): string | undefined {
		const provider = this.runtimeModel.provider;
		const model = this.runtimeModel.modelName ?? this.options.model;
		if (!provider && !model) return undefined;
		const route = this.runtimeModel.authMode ? ` · ${this.runtimeModel.authMode}` : "";
		const capabilities = this.runtimeModel.capabilities?.length
			? ` · ${this.runtimeModel.capabilities.slice(0, 3).join(",")}`
			: "";
		return `${provider ?? "provider?"} / ${model ?? "model?"}${route}${capabilities}`;
	}
}
const SPINNER_FRAMES = ["◐", "◓", "◑", "◒"] as const;
function inputBoxMetrics(columns: number): { readonly boxWidth: number; readonly textWidth: number } {
	const boxWidth = Math.max(14, Math.min(64, columns - 10));
	return { boxWidth, textWidth: Math.max(4, boxWidth - 6) };
}
function inputTextWindow(
	value: string,
	cursorIndex: number,
	fieldWidth: number,
): { readonly start: number; readonly end: number } {
	const count = graphemeCount(value);
	const cursor = Math.max(0, Math.min(cursorIndex, count));
	const textBudget = Math.max(1, fieldWidth - 3);
	let start = cursor;
	let end = cursor;
	let leftWidth = 0;
	let rightWidth = 0;
	let leftBlocked = false;
	let rightBlocked = false;
	while (!leftBlocked || !rightBlocked) {
		const preferLeft = !leftBlocked && (rightBlocked || leftWidth <= rightWidth);
		if (preferLeft) {
			if (start === 0) {
				leftBlocked = true;
				continue;
			}
			const nextWidth = displayWidth(sliceGraphemes(value, start - 1, start));
			if (leftWidth + rightWidth + nextWidth > textBudget) leftBlocked = true;
			else {
				start -= 1;
				leftWidth += nextWidth;
			}
		} else {
			if (end >= count) {
				rightBlocked = true;
				continue;
			}
			const nextWidth = displayWidth(sliceGraphemes(value, end, end + 1));
			if (leftWidth + rightWidth + nextWidth > textBudget) rightBlocked = true;
			else {
				end += 1;
				rightWidth += nextWidth;
			}
		}
	}
	return { start, end };
}
function textInputRows(
	label: string,
	value: string,
	cursorIndex: number,
	columns: number,
	options: { readonly masked?: boolean; readonly placeholder?: string; readonly hint?: string } = {},
): RenderRow[] {
	const { boxWidth, textWidth } = inputBoxMetrics(columns);
	const displayValue = options.masked ? "•".repeat(graphemeCount(value)) : value;
	const source = displayValue || options.placeholder || "";
	const visibleCursor = displayValue ? cursorIndex : 0;
	const window = inputTextWindow(source, visibleCursor, textWidth);
	const leftClipped = window.start > 0;
	const rightClipped = window.end < graphemeCount(source);
	const before = sliceGraphemes(source, window.start, visibleCursor);
	const after = sliceGraphemes(source, visibleCursor, window.end);
	return [
		row({ text: "  " + label, tone: "primary", bold: true }),
		row({ text: "  ╭" + "─".repeat(boxWidth - 2) + "╮", tone: "faint" }),
		row(
			{ text: "  │ ", tone: "faint" },
			...(leftClipped ? [{ text: "‹", tone: "faint" as const }] : []),
			{ text: before, tone: displayValue ? "strong" : "faint" },
			{ text: "█", tone: "primary", bold: true },
			{ text: after, tone: displayValue ? "strong" : "faint" },
			...(rightClipped ? [{ text: "›", tone: "faint" as const }] : []),
			{ text: " │", tone: "faint" },
		),
		row({ text: "  ╰" + "─".repeat(boxWidth - 2) + "╯", tone: "faint" }),
		...(options.hint && columns >= 60 ? [row({ text: "  " + options.hint, tone: "faint" })] : []),
	];
}
function graphFieldHint(field: Exclude<GraphField, "route" | "reset" | "remove">): string | undefined {
	if (field === "description") return "Short summary shown to the coordinator.";
	if (field === "whenToUse") return "Guidance the coordinator uses to choose this worker.";
	if (field === "systemPrompt") return "Instructions added to this worker's context.";
	if (field === "baseUrl") return "Provider endpoint for this worker's model route.";
	if (
		field === "contextLength" ||
		field === "maxContextSize" ||
		field === "maxOutputTokens" ||
		field === "maxSteps" ||
		field === "timeoutMs" ||
		field === "runTimeoutMs" ||
		field === "maxQueuedRuns"
	)
		return "Enter a positive number.";
	return undefined;
}
function formatWorkerToolSelection(value: unknown): string {
	if (!Array.isArray(value)) return "Inherit all session tools";
	const tools = value.filter((item): item is string => typeof item === "string");
	if (!tools.length) return "No tools";
	const preview = tools.slice(0, 3).join(", ");
	return tools.length + " selected · " + preview + (tools.length > 3 ? ", …" : "");
}
function isObjectValue(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}
function panelRow(selected: boolean, label: string, detail?: string): RenderRow {
	return selected
		? row(
				{ text: "  ", tone: "strong", background: "primary", bold: true },
				{ text: label, tone: "strong", background: "primary", bold: true },
				...(detail ? [{ text: `  ${detail}`, tone: "strong" as const, background: "primary" as const }] : []),
			)
		: row(
				{ text: "  ", tone: "default" },
				{ text: label, tone: "default" },
				...(detail ? [{ text: `  ${detail}`, tone: "faint" as const }] : []),
			);
}
function visibleModelChoices(panel: ModelPanelState): readonly DiscoveredModel[] {
	return filterDiscoveredModels(panel.models, panel.modelQuery);
}
function visibleMenuItems(panel: MenuPanelState): readonly PanelMenuItem[] {
	const query = panel.query.trim().toLocaleLowerCase();
	if (!query) return panel.items;
	return panel.items.filter((item) => `${item.label} ${item.detail ?? ""}`.toLocaleLowerCase().includes(query));
}
export function historySafeInput(value: string): string {
	if (/^\/(?:auth\s+set|config\s+set)(?:\s|$)/i.test(value.trim())) {
		const command = value.trim().match(/^\/(auth|config)\s+set/i)?.[0] ?? "/command";
		return `${command} [redacted]`;
	}
	return value;
}
export function commandPanelQuery(panel: InteractivePanelName, args: readonly string[]): string {
	if (!args.length) return "";
	const [subcommand, value] = args;
	switch (panel) {
		case "sessions":
			return args.join(" ");
		case "compact":
			return args.join(" ");
		case "help":
			return subcommand!.startsWith("/") ? subcommand! : `/${subcommand}`;
		case "theme":
			return subcommand!;
		case "archive":
			return subcommand === "off" ? "restore" : subcommand!;
		case "delete":
			return args.join(" ");
		case "activity":
			return args.join(" ");
		case "cron":
			return subcommand === "create" ? "create" : subcommand === "delete" ? (value ?? "delete") : "";
		case "goal":
			return subcommand === "create" ? "create" : subcommand!;
		case "plan":
			return subcommand === "revise" ? "revise" : subcommand === "status" ? "status" : subcommand!;
		case "memory":
			return subcommand === "query"
				? "search"
				: subcommand === "remember"
					? "remember"
					: subcommand === "index"
						? "index"
						: (subcommand ?? "");
		case "learn":
			return subcommand === "approve" || subcommand === "reject"
				? (value ?? "")
				: subcommand === "pending"
					? ""
					: subcommand!;
		case "skills":
			return subcommand === "list" ? "" : subcommand === "remove" ? (value ?? "") : subcommand!;
		case "mcp":
			return subcommand === "list"
				? ""
				: subcommand === "remove" || subcommand === "auth"
					? (value ?? "")
					: subcommand!;
		case "plugins":
			return subcommand === "list"
				? ""
				: subcommand === "install"
					? "install"
					: subcommand === "uninstall"
						? (value ?? "")
						: subcommand!;
		case "capabilities":
			return subcommand ?? "";
		case "trust":
			return subcommand!;
		case "auth":
			return subcommand === "status" || subcommand === "set" || subcommand === "remove" || subcommand === "login"
				? (value ?? "")
				: subcommand!;
		case "config":
			return subcommand === "get" || subcommand === "path" || subcommand === "set" ? "" : subcommand!;
		case "graph":
			return subcommand === "show" || subcommand === "set" ? "" : subcommand!;
		default:
			return subcommand ?? "";
	}
}
export function commandPanelPrefills(panel: InteractivePanelName, args: readonly string[]): string[] {
	if (!args.length) return [];
	const [subcommand, ...rest] = args;
	switch (panel) {
		case "new":
		case "rename":
			return [args.join(" ")];
		case "cron":
			return subcommand === "create" ? [rest[0] ?? "", rest.slice(1).join(" ")] : [];
		case "goal":
			return subcommand === "create" ? [rest.join(" ")] : [];
		case "plan":
			return subcommand === "revise" || subcommand === "start" ? [rest.join(" ")] : [];
		case "memory":
			return subcommand === "query" || subcommand === "remember" ? [rest.join(" ")] : [];
		case "plugins":
			return subcommand === "install" ? [rest.join(" ")] : [];
		default:
			return [];
	}
}
export function splitCommandArguments(value: string): string[] {
	const args: string[] = [];
	let current = "";
	let quote: "'" | '"' | undefined;
	let started = false;
	for (let index = 0; index < value.length; index += 1) {
		const character = value[index]!;
		if (character === "\\" && quote !== "'") {
			const next = value[index + 1];
			if (next === undefined) current += "\\";
			else if (next === "\\" || next === quote || /\s/u.test(next)) {
				current += next;
				index += 1;
			} else current += "\\";
			started = true;
		} else if (quote) {
			if (character === quote) quote = undefined;
			else current += character;
			started = true;
		} else if (character === "'" || character === '"') {
			quote = character;
			started = true;
		} else if (/\s/u.test(character)) {
			if (started) args.push(current);
			current = "";
			started = false;
		} else {
			current += character;
			started = true;
		}
	}
	if (quote) throw new Error("Unclosed quote in slash command arguments.");
	if (started) args.push(current);
	return args;
}
function quoteCommandArgument(value: string): string {
	return /[\s"'\\]/u.test(value) ? JSON.stringify(value) : value;
}
type ModelPickerDisplay = {
	readonly name?: string;
	readonly contextLength?: number;
	readonly contextLimit?: number;
	readonly maxOutputTokens?: number;
	readonly reasoningLevels?: readonly string[];
	readonly capabilities?: readonly string[];
	readonly provenance?: DiscoveredModel["provenance"];
};
function modelPickerDetail(model: ModelPickerDisplay): string | undefined {
	const details = [
		typeof model.contextLength === "number" ? `context ${formatTokenCount(model.contextLength)}` : undefined,
		typeof model.contextLimit === "number" ? `max ${formatTokenCount(model.contextLimit)}` : undefined,
		typeof model.maxOutputTokens === "number" ? `output ${formatTokenCount(model.maxOutputTokens)}` : undefined,
		model.reasoningLevels?.length ? `reasoning ${model.reasoningLevels.join("/")}` : undefined,
		model.capabilities?.length ? model.capabilities.slice(0, 4).join(" · ") : undefined,
		...(modelMetadataStatus(model).complete ? [] : [`metadata incomplete · retry discovery`]),
	].filter((detail): detail is string => detail !== undefined);
	return details.length ? details.join("  ·  ") : undefined;
}
function setupKeyIs(key: KeyInput, name: "up" | "down"): boolean {
	if (key.name === name) return true;
	return name === "up"
		? key.sequence === "\x1b[A" || key.sequence === "\x1bOA"
		: key.sequence === "\x1b[B" || key.sequence === "\x1bOB";
}
const BUILTIN_SUBAGENT_PROFILE_IDS = new Set(["coder", "explore", "plan"]);
function subagentTarget(profileId: string, profile?: unknown): AgentTarget {
	const builtin = BUILTIN_SUBAGENT_PROFILE_IDS.has(profileId);
	const description =
		isObjectValue(profile) && typeof profile["description"] === "string" ? profile["description"] : undefined;
	return {
		id: `subagent:${profileId}`,
		label: profileId,
		detail: `${builtin ? "Built-in worker" : "Custom worker"}${description ? ` · ${description}` : ""}`,
		kind: "subagent",
		profileId,
		builtin,
	};
}
function agentTargets(config: Record<string, unknown>): readonly AgentTarget[] {
	const graph = isObjectValue(config["agentGraph"]) ? config["agentGraph"] : {};
	const targets: AgentTarget[] = [
		{ id: "coordinator", label: "Coordinator", detail: "Graph role · main user-facing agent", kind: "coordinator" },
		{ id: "learner", label: "Learner", detail: "Graph role · resident learning agent", kind: "learner" },
	];
	const profiles = isObjectValue(graph["subagents"]) ? graph["subagents"] : {};
	for (const profileId of Object.keys(profiles).sort((left, right) => left.localeCompare(right)))
		targets.push(subagentTarget(profileId, profiles[profileId]));
	if (isObjectValue(graph["executor"]) && !Object.hasOwn(profiles, "default")) {
		targets.push({
			id: "legacy:default",
			label: "default",
			detail: "Legacy default worker route",
			kind: "subagent",
			profileId: "default",
			legacyExecutor: true,
		});
	}
	return targets;
}
function customSubagentTargets(config: Record<string, unknown>): readonly AgentTarget[] {
	return agentTargets(config).filter((target) => target.kind === "subagent");
}
function agentTargetConfig(config: Record<string, unknown>, target: AgentTarget): Record<string, unknown> {
	const graph = isObjectValue(config["agentGraph"]) ? config["agentGraph"] : {};
	if (target.legacyExecutor) return isObjectValue(graph["executor"]) ? { ...graph["executor"] } : {};
	if (target.kind === "coordinator" || target.kind === "learner") {
		const value = graph[target.kind];
		return isObjectValue(value) ? { ...value } : {};
	}
	const profiles = isObjectValue(graph["subagents"]) ? graph["subagents"] : {};
	const configured = target.profileId ? profiles[target.profileId] : undefined;
	if (isObjectValue(configured)) return { ...configured };
	return {};
}
function agentTargetPatch(target: AgentTarget, value: Record<string, unknown>): Record<string, unknown> {
	if (target.kind === "coordinator") return { model: value, agentGraph: { coordinator: value } };
	if (target.kind === "learner") return { agentGraph: { learner: value } };
	if (target.legacyExecutor) return { agentGraph: { executor: value } };
	return { agentGraph: { subagents: { [target.profileId!]: value } } };
}
function isSubagentProfileId(value: string): boolean {
	return (
		/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(value) &&
		!["coordinator", "learner", "default", "executor", ...BUILTIN_SUBAGENT_PROFILE_IDS].includes(value)
	);
}
function modelMetadataLines(model: ModelPickerDisplay): readonly RenderRow[] {
	const provenance = model.provenance;
	const field = (
		label: string,
		value: number | undefined,
		source: "authoritative" | "catalog" | "configured" | "estimated" | "unknown" | undefined,
	): RenderRow =>
		typeof value === "number"
			? row({ text: `${label}: ${formatTokenCount(value)} · ${source ?? "source not reported"}`, tone: "default" })
			: row({ text: `${label}: not reported by provider`, tone: "faint" });
	return [
		field("Context", model.contextLength, provenance?.contextLength),
		field("Max context", model.contextLimit, provenance?.maxContextSize),
		field("Max output", model.maxOutputTokens, provenance?.maxOutputTokens),
		row({
			text: model.capabilities?.length
				? `Capabilities: ${model.capabilities.join(", ")} · ${provenance?.capabilities ?? "source not reported"}`
				: "Capabilities: not reported by provider",
			tone: model.capabilities?.length ? "default" : "faint",
		}),
	];
}
function modelConfirmActions(
	panel: ModelPanelState,
): readonly ("permanent" | "session" | "policy" | "retry" | "back")[] {
	const target = panel.targets[panel.targetIndex];
	if (target?.kind === "coordinator") return ["permanent", "session", "retry", "back"];
	if (target?.kind === "learner") return ["permanent", "retry", "back"];
	return ["permanent", "policy", "retry", "back"];
}
function panelLabel(panel: InteractivePanelName): string {
	return panel.charAt(0).toUpperCase() + panel.slice(1);
}
const LEARN_PANEL_REFRESH_MS = 4_000;
const LEARN_PROPOSAL_DETAIL_MAX_CHARS = 4_000;
const LEARNING_DIAGNOSTIC_DEDUPE_MS = 60_000;
function learningProposalDetailLines(entry: LearningPendingEntry): string[] {
	const output = isObjectValue(entry.output) ? entry.output : undefined;
	const args = Array.isArray(output?.["args"]) ? (output!["args"] as readonly unknown[]).join(" ") : "";
	const command = typeof output?.["command"] === "string" ? (output["command"] as string) : undefined;
	const kind = typeof output?.["kind"] === "string" ? (output["kind"] as string) : entry.kind;
	const name = typeof output?.["name"] === "string" ? (output["name"] as string) : entry.event?.id;
	return [
		`Kind: ${kind ?? "learning proposal"}`,
		`Name: ${name ?? "unknown"}`,
		...(typeof output?.["description"] === "string" ? [`Description: ${output["description"] as string}`] : []),
		...(command ? [`Command: ${command}${args ? ` ${args}` : ""}`] : []),
		...(output?.["parameters"] !== undefined ? [`Parameters: ${JSON.stringify(output["parameters"])}`] : []),
		`Source: ${entry.event?.source ?? "unknown"}`,
		`Recorded: ${typeof entry.event?.timestamp === "number" ? new Date(entry.event.timestamp).toISOString() : "unknown"}`,
		`Target: ${entry.decision?.target ?? "unknown"}`,
		"",
		"Full proposal:",
		...prettyJsonLines(entry),
	];
}
function prettyJsonLines(value: unknown): string[] {
	let text: string;
	try {
		text = JSON.stringify(value, null, 2) ?? "undefined";
	} catch {
		text = "[unserializable]";
	}
	if (text.length > LEARN_PROPOSAL_DETAIL_MAX_CHARS) text = `${text.slice(0, LEARN_PROPOSAL_DETAIL_MAX_CHARS)}…`;
	return text.split("\n");
}
function panelLoadingLabel(panel: InteractivePanelName): string | undefined {
	return panel === "model"
		? "Loading provider routes…"
		: panel === "graph"
			? "Loading worker profiles…"
			: panel === "auth"
				? "Checking provider credentials…"
				: panel === "undo"
					? "Loading session timeline…"
					: panel === "cron"
						? "Loading scheduled prompts…"
						: panel === "tools" || panel === "skills" || panel === "plugins" || panel === "mcp"
							? "Loading capabilities…"
							: panel === "learn"
								? "Loading learner state…"
								: panel === "trust"
									? "Inspecting workspace trust…"
									: panel === "sessions" || panel === "delete"
										? "Loading sessions…"
										: panel === "config"
											? "Loading settings…"
											: undefined;
}
function graphFieldLabel(field: GraphField): string {
	return field === "description"
		? "Description"
		: field === "whenToUse"
			? "When to use"
			: field === "route"
				? "Model route"
				: field === "baseUrl"
					? "Provider base URL"
					: field === "contextLength"
						? "Provider context window"
						: field === "maxContextSize"
							? "Local context limit"
							: field === "maxOutputTokens"
								? "Output limit"
								: field === "maxSteps"
									? "Maximum steps"
									: field === "timeoutMs"
										? "Run timeout"
										: field === "runTimeoutMs"
											? "Learner run timeout"
											: field === "maxQueuedRuns"
												? "Maximum queued runs"
												: field === "systemPrompt"
													? "System prompt"
													: field === "permissionProfile"
														? "Permission profile"
														: field === "interactionMode"
															? "Interaction mode"
															: field === "tools"
																? "Tools"
																: field === "reset"
																	? "Restore defaults"
																	: "Delete profile";
}
function shortId(value: string | undefined): string {
	return value ? value.slice(0, 8) : "--------";
}
function messageOf(error: unknown): string {
	return sanitizeTerminalText(error instanceof Error ? error.message : String(error));
}

function isPermissionProfile(value: unknown): value is "manual" | "workspace" | "unrestricted" {
	return value === "manual" || value === "workspace" || value === "unrestricted";
}

function isInteractionMode(value: unknown): value is "interactive" | "unattended" {
	return value === "interactive" || value === "unattended";
}

function throwIfAborted(signal: AbortSignal | undefined): void {
	if (!signal?.aborted) return;
	throw signal.reason instanceof Error ? signal.reason : new Error("Panel operation was cancelled");
}

// Placeholder filtering duplicated from kosong's `hasUsableSecret`
// (packages/kosong/src/provider-parity.ts): the interface freeze allows
// apps/kageko to import only @kageko/node-sdk and @kageko/tui-kit, and neither
// re-exports it, so the readiness probe keeps this tiny copy in sync manually.
const PLACEHOLDER_SECRET_VALUES: ReadonlySet<string> = new Set([
	"*",
	"**",
	"***",
	"changeme",
	"your_api_key",
	"your_api_key_here",
	"your-api-key",
	"placeholder",
	"example",
	"dummy",
	"null",
	"none",
]);

function hasUsableEnvSecret(value: string | undefined): boolean {
	if (typeof value !== "string") return false;
	const cleaned = value.trim();
	if (cleaned.length < 4) return false;
	return !PLACEHOLDER_SECRET_VALUES.has(cleaned.toLowerCase());
}

function modelIdsMatch(providerId: string, left: string, right: string): boolean {
	const normalize = (value: string) =>
		value
			.trim()
			.toLowerCase()
			.replace(/^models\//, "");
	const a = normalize(left);
	const b = normalize(right);
	if (a === b) return true;
	const provider = providerId.trim().toLowerCase();
	if (provider === "kimi" || provider === "kimi-code") {
		const canonical = (value: string) =>
			value === "kimi-k3" || value === "k3[1m]" ? "k3" : value === "kimi-k3-256k" ? "k3-256k" : value;
		return canonical(a) === canonical(b);
	}
	return false;
}
