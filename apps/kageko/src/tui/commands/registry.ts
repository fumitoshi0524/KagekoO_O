import type { SlashCommand } from "./types.js";
import { SETUP_PROVIDERS } from "../controllers/setup-controller.js";
import { formatTokenCount } from "../views/status-view.js";

export const slashCommands: readonly SlashCommand[] = [
	// — Session
	{
		name: "new",
		category: "session",
		description: "Create a new session for this workspace",
		argumentHint: "(interactive)",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("new", args);
				return;
			}
			await ctx.switchSession(await ctx.client.createSession({ cwd: ctx.cwd }));
		},
	},
	{
		name: "sessions",
		aliases: ["resume"],
		category: "session",
		description: "Browse, search, and resume a saved session",
		argumentHint: "(interactive)",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("sessions", args);
				return;
			}
			if (args[0]) {
				await ctx.client.resumeSession(args[0]);
				await ctx.switchSession(ctx.client.session(args[0]));
			} else return ctx.showOverlay("sessions");
		},
	},
	{
		name: "fork",
		category: "session",
		description: "Fork the current session",
		argumentHint: "(no arguments)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("fork", args);
				return;
			}
			if (!(await ctx.confirm("Fork the current session and continue in the new copy?"))) return;
			await ctx.switchSession(await ctx.client.forkSession(ctx.session!.id));
		},
	},
	{
		name: "rename",
		aliases: ["title"],
		category: "session",
		description: "Rename the current session",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("rename", args);
				return;
			}
			const title = args.join(" ").trim();
			if (!title) {
				ctx.notice("warning", "Usage: /rename <title>");
				return;
			}
			await ctx.client.renameSession(ctx.session!.id, title);
			ctx.notice("status", `Session renamed to "${title}".`);
		},
	},
	{
		name: "archive",
		category: "session",
		description: "Archive (or /archive off to unarchive) the current session",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("archive", args);
				return;
			}
			const archived = args[0] !== "off";
			await ctx.client.archiveSession(ctx.session!.id, archived);
			ctx.notice("status", archived ? "Session archived." : "Session unarchived.");
		},
	},
	{
		name: "delete",
		category: "session",
		description: "Delete a session",
		argumentHint: "(interactive)",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("delete", args);
				return;
			}
			const id = args[0];
			if (!id) {
				ctx.notice("warning", "Usage: /delete <session-id>");
				return;
			}
			if (!(await ctx.confirm(`Delete session ${id.slice(0, 8)}? This cannot be undone.`))) return;
			await ctx.client.deleteSession(id);
			ctx.notice("status", `Deleted session ${id.slice(0, 8)}.`);
		},
	},
	// — Info & system
	{
		name: "exit",
		aliases: ["quit"],
		category: "info",
		description: "Close the TUI",
		argumentHint: "(no arguments)",
		availability: "always",
		async run(_args, ctx) {
			await ctx.quit();
		},
	},
	{
		name: "help",
		category: "info",
		description: "Show commands and keybindings",
		argumentHint: "(no arguments)",
		availability: "always",
		async run(_args, ctx) {
			if (ctx.openPanel) await ctx.openPanel("help", _args);
			else ctx.showOverlay("help");
		},
	},
	{
		name: "cancel",
		category: "modes",
		description: "Cancel the current turn",
		argumentHint: "(no arguments)",
		availability: "always",
		needsSession: true,
		async run(_args, ctx) {
			await ctx.session!.cancel();
		},
	},
	{
		name: "activity",
		aliases: ["activities", "tasks", "task"],
		category: "info",
		description: "Inspect live agent work, or browse recorded activity history",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("activity", args);
				return;
			}
			if (args[0] === "history") {
				const activities = await ctx.client.listActivities({ activeOnly: false });
				ctx.showLines(
					activities.length
						? activities.map(
								(item) =>
									`${item.status.padEnd(9)} ${item.kind.padEnd(9)} ${item.sessionId.slice(0, 8)} ${item.taskId ?? item.subagentId ?? item.activityId}`,
							)
						: ["No recorded activity history."],
				);
				return;
			}
			if (args[0] === "current" || !args[0]) {
				const activities = await ctx.client.listActivities({ sessionId: ctx.session?.id, activeOnly: true });
				ctx.showLines(
					activities.length
						? activities.map(
								(item) =>
									`${item.status.padEnd(9)} ${item.kind.padEnd(9)} ${item.taskId ?? item.subagentId ?? item.activityId}`,
							)
						: ["No agent activity is running."],
				);
				return;
			}
			if (!ctx.session) {
				ctx.notice("warning", "/activity <task-id> requires an active session.");
				return;
			}
			ctx.showDetails([(await ctx.session.readActivityOutput(args[0])).content]);
		},
	},
	{
		name: "theme",
		category: "config",
		description: "Choose the terminal theme for this TUI session",
		argumentHint: "(interactive)",
		availability: "always",
		async run(_args, ctx) {
			await ctx.openPanel?.("theme", _args);
		},
	},
	{
		name: "undo",
		category: "modes",
		description: "Browse the complete session timeline and restore a prior state",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("undo", args);
				return;
			}
			if (args.length) {
				ctx.notice("warning", "/undo is an interactive timeline. Select the exact state to restore.");
				return;
			}
			ctx.notice("warning", "Session timeline is unavailable in this host.");
		},
	},
	{
		name: "interactions",
		hidden: true,
		category: "info",
		description: "Reopen a pending approval or question",
		argumentHint: "(no arguments)",
		availability: "always",
		run(_args, ctx) {
			ctx.showInteractions();
		},
	},
	{
		name: "capabilities",
		category: "capabilities",
		description: "List session capabilities (plugins, skills, MCP)",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(_args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("capabilities", _args);
				return;
			}
			const capabilities = await ctx.client.listCapabilities(ctx.session!.id);
			ctx.showLines(
				capabilities.length
					? capabilities.map(
							(item) => `${item.kind.padEnd(10)} ${item.id}${item.description ? ` — ${item.description}` : ""}`,
						)
					: ["No active capabilities."],
			);
		},
	},
	{
		name: "cron",
		category: "info",
		description: "List, create or delete scheduled prompts",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("cron", args);
				return;
			}
			const [sub, ...rest] = args;
			if (sub === "create") {
				if (rest.length < 2) {
					ctx.notice("warning", "Usage: /cron create <cron-expression> <prompt>");
					return;
				}
				await ctx.client.createCron(ctx.session!.id, {
					cron: rest[0]!,
					prompt: rest.slice(1).join(" "),
					recurring: true,
				});
				ctx.notice("status", "Cron created.");
				return;
			}
			if (sub === "delete") {
				if (!rest[0]) {
					ctx.notice("warning", "Usage: /cron delete <id>");
					return;
				}
				if (!(await ctx.confirm(`Delete cron ${rest[0]}?`))) return;
				const deleted = await ctx.client.deleteCron(ctx.session!.id, rest[0]);
				if (!deleted) {
					ctx.notice("warning", `Cron ${rest[0]} was not found; it was already removed.`);
					return;
				}
				ctx.notice("status", "Cron deleted.");
				return;
			}
			const cronJobs = await ctx.client.listCron(ctx.session!.id);
			ctx.showLines(
				cronJobs.length
					? cronJobs.map((item) => `${item.id}  ${item.cron}  ${item.nextFireAt ?? "unscheduled"}`)
					: ["No scheduled prompts."],
			);
		},
	},
	{
		name: "shell",
		category: "info",
		description: "Open an embedded workspace shell inside this TUI; F2 enters and returns",
		argumentHint: "(no arguments)",
		async run(_args, ctx) {
			await ctx.openShell();
		},
	},
	{
		name: "goal",
		category: "modes",
		description: "Create or manage the session goal; does not draft or execute a plan",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("goal", args);
				return;
			}
			const session = ctx.session!;
			const sub = args[0];
			if (!sub || sub === "status") {
				const goal = (await session.getGoal()) as { objective?: string; status?: string; turnsUsed?: number } | null;
				ctx.showLines([goal ? `Goal (${goal.status}): ${goal.objective}` : "No active goal."]);
				return;
			}
			if (sub === "pause" || sub === "resume") {
				const updated = await session.updateGoal({ status: sub === "pause" ? "paused" : "active" });
				if (updated === null) {
					ctx.notice("warning", sub === "pause" ? "No active goal." : "No goal to resume.");
					return;
				}
				ctx.notice("status", sub === "pause" ? "Goal paused." : "Goal resumed.");
				return;
			}
			if (sub === "complete") {
				const completed = await session.updateGoal({ status: "completed" });
				if (completed === null) {
					ctx.notice("warning", "No active goal.");
					return;
				}
				ctx.notice("status", "Goal completed.");
				return;
			}
			const existing = await session.getGoal();
			if (existing !== null) await session.updateGoal({ status: "completed" });
			await session.createGoal({ objective: args.join(" ") });
			ctx.notice(
				"status",
				existing !== null
					? "Goal replaced. Use /plan to draft an execution plan."
					: "Goal created. Use /plan to draft an execution plan.",
			);
		},
	},
	{
		name: "plan",
		category: "modes",
		description: "Ask the coordinator agent to draft, review, and gate an execution plan before executor agents work",
		argumentHint: "(interactive)",
		needsSession: true,
		// The panel owns the approval/revision/cancellation controls for a live
		// coordinator turn.  Blocking the command while that turn is live makes its
		// own "Cancel plan turn" action unreachable.
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("plan", args);
				return;
			}
			const sub = args[0];
			if (sub === "status") {
				ctx.notice(
					"status",
					"Plan state is owned by the coordinator turn; inspect the latest coordinator response and pending question with /interactions.",
				);
				return;
			}
			if (sub === "approve") {
				if (typeof ctx.session!.prompt === "function")
					await ctx.session!.prompt({
						parts: [
							{
								type: "text",
								text: "The human approved the current coordinator plan. Dispatch each approved step to an independent executor agent using function-calling. Do not execute workspace tools in the coordinator.",
							},
						],
					});
				ctx.notice("status", "Plan approval sent to the coordinator.");
				return;
			}
			if (sub === "revise") {
				const feedback = args.slice(1).join(" ");
				if (!feedback) {
					ctx.notice("warning", "Usage: /plan revise <feedback>");
					return;
				}
				if (typeof ctx.session!.prompt === "function")
					await ctx.session!.prompt({
						parts: [
							{
								type: "text",
								text: `Revise the current execution plan using this human feedback: ${feedback}. Keep execution gated until approval.`,
							},
						],
					});
				ctx.notice("status", "Plan revision sent to the coordinator.");
				return;
			}
			if (sub === "cancel") {
				await ctx.session!.cancel();
				ctx.notice("status", "Coordinator plan turn cancelled.");
				return;
			}
			const objective = args.join(" ").trim();
			if (!objective) {
				ctx.notice("warning", "Usage: /plan <objective> | status | approve | revise <feedback> | cancel");
				return;
			}
			if (typeof ctx.session!.prompt !== "function") {
				ctx.notice("error", "This session cannot run a coordinator plan.");
				return;
			}
			await ctx.session!.prompt({
				parts: [
					{
						type: "text",
						text: [
							"You are the coordinator agent for this session.",
							`Draft an execution plan for: ${objective}`,
							"Do not execute workspace tools yourself. Break the plan into independent executor-agent work units, identify dependencies and function calls, and keep the resident learner informed.",
							"Present the plan, then call ask_user with Approve, Revise, or Cancel. Only after Approve may you dispatch executor agents; learner work remains continuous and may synthesize approved tools/skills, never silently mutate the plan.",
							"Return a concise plan with step ids, role, inputs, outputs, and approval state.",
						].join("\n"),
					},
				],
			});
			ctx.notice(
				"status",
				"Coordinator is drafting the plan; approve it through the pending question or /plan approve.",
			);
		},
	},
	{
		name: "compact",
		category: "modes",
		description: "Compact the conversation context now",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("compact", args);
				return;
			}
			const result = (await ctx.session!.compact(args.join(" ") || undefined)) as {
				outcome?: string;
				reason?: string;
			} | null;
			if (result?.outcome && result.outcome !== "compacted") {
				ctx.notice("warning", `Compaction ${result.outcome}${result.reason ? ` (${result.reason})` : ""}.`);
				return;
			}
			ctx.notice("status", "Context compacted.");
		},
	},
	{
		name: "memory",
		category: "memory",
		description: "Inspect and query long-term memory",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("memory", args);
				return;
			}
			const sessionId = ctx.session!.id;
			const [sub, ...rest] = args;
			switch (sub) {
				case undefined:
				case "status": {
					const status = await ctx.client.memoryStatus(sessionId);
					ctx.showLines([
						`Knowledge entries: ${status.knowledgeEntries}`,
						`Repo files indexed: ${status.repoFilesIndexed}`,
						`Profile entries: ${status.profileEntries}`,
						`Pending learning: ${status.pendingLearning}`,
					]);
					return;
				}
				case "query": {
					if (!rest.length) {
						ctx.notice("warning", "Usage: /memory query <text>");
						return;
					}
					const answer = await ctx.client.queryMemory(sessionId, rest.join(" "));
					ctx.showLines([typeof answer === "string" ? answer : JSON.stringify(answer, null, 2)]);
					return;
				}
				case "remember": {
					if (!rest.length) {
						ctx.notice("warning", "Usage: /memory remember <fact>");
						return;
					}
					await ctx.client.rememberFact(sessionId, rest.join(" "));
					ctx.notice("status", "Remembered.");
					return;
				}
				case "recall": {
					// A query is required: ProfileMemory.recall tokenizes the query and
					// filters zero-score entries, so a query-less recall always returns [].
					if (!rest.length) {
						ctx.notice("warning", "Usage: /memory recall <query>");
						return;
					}
					const entries = await ctx.client.recallProfile(sessionId, rest.join(" "));
					ctx.showLines(
						entries.length
							? entries.map((entry) => {
									if (typeof entry !== "object" || entry === null) return String(entry);
									const profile = entry as { scope?: unknown; fact?: unknown };
									return `${String(profile.scope ?? "profile")} · ${String(profile.fact ?? "")}`;
								})
							: ["No matching profile memories."],
					);
					return;
				}
				case "index": {
					ctx.notice("status", "Indexing repository…");
					const result = await ctx.client.indexRepository(sessionId);
					ctx.notice("status", `Index complete: ${JSON.stringify(result)}`);
					return;
				}
				default:
					ctx.notice("warning", "Usage: /memory status|query|remember|recall|index");
			}
		},
	},
	{
		name: "learn",
		category: "memory",
		description: "Inspect the resident learning agent and approve auto-generated tools or skills",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("learn", args);
				return;
			}
			const sessionId = ctx.session!.id;
			const [sub, id] = args;
			if (sub === "status") {
				const status = await ctx.client.memoryStatus(sessionId);
				ctx.showLines([
					status.learningEnabled === false ? "Resident learner: disabled" : "Resident learner: active",
					`Pending proposals: ${String((status as { pendingLearning?: unknown }).pendingLearning ?? "unknown")}`,
					"Approved proposals become function-callable tools or skills after capability reload.",
				]);
				return;
			}
			if (!sub || sub === "pending") {
				const pending = await ctx.client.listLearningPending(sessionId);
				ctx.showLines(
					pending.length ? pending.map((entry) => JSON.stringify(entry)) : ["No pending learning entries."],
				);
				return;
			}
			if ((sub === "approve" || sub === "reject") && id) {
				if (sub === "reject" && !(await ctx.confirm(`Reject learning entry ${id}?`))) return;
				const result = (await ctx.client.resolveLearning(sessionId, id, sub)) as {
					resolved?: boolean;
					reason?: string;
				};
				if (result?.resolved === false) {
					ctx.notice("warning", `Could not ${sub}: ${result.reason ?? "unknown reason"}.`);
					return;
				}
				ctx.notice("status", `Learning entry ${sub === "approve" ? "approved" : "rejected"}.`);
				// This path resolves outside the /learn panel, so it must refresh the
				// host's pending-proposal indicator itself.
				ctx.refreshLearningPending?.();
				return;
			}
			ctx.notice("warning", "Usage: /learn status|pending|approve <id>|reject <id>");
		},
	},
	{
		name: "skills",
		category: "capabilities",
		description: "List, reload or remove skills",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("skills", args);
				return;
			}
			const sessionId = ctx.session!.id;
			const [sub, name] = args;
			if (!sub || sub === "list") {
				const skills = await ctx.client.listCapabilities(sessionId, "skill");
				ctx.showLines(
					skills.length
						? skills.map((skill) => `${skill.id}${skill.description ? ` — ${skill.description}` : ""}`)
						: ["No skills loaded."],
				);
				return;
			}
			if (sub === "reload") {
				await ctx.client.reloadCapabilities(sessionId);
				ctx.notice("status", "Capabilities reloaded.");
				return;
			}
			if (sub === "remove" && name) {
				if (!(await ctx.confirm(`Remove skill ${name}?`))) return;
				await ctx.client.removeSkill(name);
				ctx.notice("status", `Skill ${name} removed.`);
				return;
			}
			ctx.notice("warning", "Usage: /skills [list]|reload|remove <name>");
		},
	},
	{
		name: "mcp",
		category: "capabilities",
		description: "Connect external MCP tools; list, add, remove, or authenticate a server",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("mcp", args);
				return;
			}
			const sessionId = ctx.session!.id;
			const [sub, name, ...rest] = args;
			if (!sub || sub === "list") {
				const servers = await ctx.client.listCapabilities(sessionId, "mcp");
				ctx.showLines(servers.length ? servers.map((server) => server.id) : ["No MCP servers connected."]);
				return;
			}
			if (sub === "add" && name && rest.length) {
				ctx.notice(
					"warning",
					"MCP servers must be added through the guided /mcp form; JSON command arguments are no longer accepted.",
				);
				return;
			}
			if (sub === "remove" && name) {
				if (!(await ctx.confirm(`Remove MCP server ${name}?`))) return;
				const config = (await ctx.client.getConfiguration()) as { mcp?: { servers?: Record<string, unknown> } };
				const servers = config.mcp?.servers ?? {};
				if (!servers[name]) {
					ctx.notice("warning", `Unknown MCP server: ${name}`);
					return;
				}
				// ConfigService deep-merges patches and never deletes keys, so removal is
				// a null tombstone; filterMcpServers drops entries that fail validation.
				await ctx.client.updateConfiguration({ mcp: { servers: { [name]: null } } });
				await ctx.client.reloadCapabilities(sessionId);
				ctx.notice("status", `MCP server ${name} removed.`);
				return;
			}
			if (sub === "auth" && name) {
				ctx.notice("status", `Starting OAuth for ${name}; watch for a verification URL…`);
				await ctx.client.authenticateMcpServer(name);
				ctx.notice("status", `MCP server ${name} authenticated.`);
				return;
			}
			ctx.notice("warning", "Usage: /mcp [list]|add <name> <json>|remove <name>|auth <name>");
		},
	},
	{
		name: "plugins",
		category: "capabilities",
		description: "List, install or uninstall plugins",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("plugins", args);
				return;
			}
			const sessionId = ctx.session!.id;
			const [sub, value] = args;
			if (!sub || sub === "list") {
				const plugins = await ctx.client.listCapabilities(sessionId, "plugin");
				ctx.showLines(
					plugins.length
						? plugins.map((plugin) => `${plugin.id}${plugin.description ? ` — ${plugin.description}` : ""}`)
						: ["No plugins installed."],
				);
				return;
			}
			if (sub === "install" && value) {
				const id = await ctx.client.installPlugin(value);
				await ctx.client.reloadCapabilities(sessionId);
				ctx.notice("status", `Plugin installed: ${id}`);
				return;
			}
			if (sub === "uninstall" && value) {
				if (!(await ctx.confirm(`Uninstall plugin ${value}?`))) return;
				await ctx.client.uninstallPlugin(value);
				ctx.notice("status", `Plugin ${value} uninstalled.`);
				return;
			}
			ctx.notice("warning", "Usage: /plugins [list]|install <source>|uninstall <id>");
		},
	},
	{
		name: "tools",
		category: "capabilities",
		description: "List tools available to the agent",
		argumentHint: "(interactive)",
		needsSession: true,
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("tools", args);
				return;
			}
			const tools = await ctx.client.listTools(ctx.session!.id);
			ctx.showLines(tools.map((tool) => `${tool.provenance.kind.padEnd(12)} ${tool.name}`));
		},
	},
	{
		name: "model",
		category: "config",
		description: "Choose model routes and reasoning for agents or this session",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("model", args);
				return;
			}
			const config = (await ctx.client.getConfiguration()) as { model?: Record<string, unknown> };
			if (!args.length || args[0] === "show") {
				const model = config.model ?? {};
				const providerId = typeof model["provider"] === "string" ? model["provider"] : undefined;
				const modelId = typeof model["modelName"] === "string" ? model["modelName"] : undefined;
				const configuredAuthMode: "api" | "oauth" | undefined =
					model["authMode"] === "api" || model["authMode"] === "oauth" ? model["authMode"] : undefined;
				const credentialModes: Array<"api" | "oauth"> = [];
				if (providerId && typeof ctx.client.hasCredential === "function") {
					for (const mode of ["api", "oauth"] as const)
						if (await ctx.client.hasCredential(providerId, mode).catch(() => false)) credentialModes.push(mode);
				}
				const discoveryModes = configuredAuthMode
					? [configuredAuthMode]
					: credentialModes.length
						? credentialModes
						: [providerId === "kimi-code" ? ("oauth" as const) : ("api" as const)];
				let discovered: Record<string, unknown> | undefined;
				if (providerId && modelId && typeof ctx.client.discoverModels === "function") {
					for (const mode of discoveryModes) {
						const models = await ctx.client
							.discoverModels(providerId, { authMode: mode, includeProvenance: true })
							.catch(() => []);
						discovered = models.find((entry) => modelIdsEqual(providerId, entry.id, modelId)) as
							Record<string, unknown> | undefined;
						if (discovered) break;
					}
				}
				const provenance = isRecord(model["provenance"]) ? model["provenance"] : {};
				const discoveredProvenance = isRecord(discovered?.["provenance"]) ? discovered["provenance"] : {};
				const metadataSource = isRecord(model["metadataSource"])
					? model["metadataSource"]
					: isRecord(discovered?.["metadataSource"])
						? discovered["metadataSource"]
						: undefined;
				const effectiveProvenance = { ...discoveredProvenance, ...provenance };
				const contextSource = sourceLabel(provenance["contextLength"]);
				const localSource = sourceLabel(effectiveProvenance["maxContextSize"]);
				const capabilities =
					(Array.isArray(model["capabilities"]) && model["capabilities"].length
						? model["capabilities"]
						: Array.isArray(discovered?.["capabilities"])
							? discovered["capabilities"]
							: []
					).join(", ") || "?";
				const origin = metadataSource
					? ` · ${String(metadataSource["source"] ?? metadataSource["kind"])}:${String(metadataSource["providerId"] ?? "?")}`
					: "";
				const contextLength = numberValue(model["contextLength"]) ?? numberValue(discovered?.["contextLength"]);
				const maxContextSize = numberValue(model["maxContextSize"]) ?? numberValue(discovered?.["maxContextSize"]);
				const effectiveAuthMode = configuredAuthMode ?? (credentialModes.length === 1 ? credentialModes[0] : undefined);
				ctx.showLines([
					`Provider: ${String(providerId ?? "not configured")}`,
					`Model: ${String(modelId ?? "not configured")}`,
					`Context window: ${formatTokenCount(contextLength, effectiveProvenance["contextLength"] as Parameters<typeof formatTokenCount>[1])} (${sourceLabel(effectiveProvenance["contextLength"])})`,
					`Local limit: ${formatTokenCount(maxContextSize, effectiveProvenance["maxContextSize"] as Parameters<typeof formatTokenCount>[1])} (${localSource})`,
					`Capabilities: ${capabilities}`,
					`Metadata: ${origin ? origin.slice(3) : "?"}`,
					`Route: ${effectiveAuthMode ?? "unresolved"}${credentialModes.length ? ` · ready: ${credentialModes.join(", ")}` : " · no configured credential detected"}`,
				]);
				return;
			}
			if (args[0] === "discover" && args[1]) {
				const authMode = args[2] === "oauth" ? "oauth" : "api";
				const models = await ctx.client.discoverModels(args[1], { authMode, includeProvenance: true });
				ctx.showLines(
					models.length
						? models.map((model) => {
								const source = model.provenance?.contextLength;
								const context = formatTokenCount(model.contextLength, source);
								const capabilities = model.capabilities?.length ? ` · ${model.capabilities.join(",")}` : "";
								return `${model.id} · ctx ${context}${capabilities} · ${model.metadataSource?.source ?? model.metadataSource?.kind ?? "unknown"}`;
							})
						: ["No models returned."],
				);
				return;
			}
			if (args[0] === "set" && args.length >= 3) {
				const [, provider, modelName, context] = args;
				const authMode = args[4] === "oauth" ? "oauth" : args[4] === "api" ? "api" : undefined;
				const maxContextSize = context === undefined ? undefined : Number(context);
				if (maxContextSize !== undefined && (!Number.isFinite(maxContextSize) || maxContextSize <= 0)) {
					ctx.notice("warning", "Context must be a positive token count.");
					return;
				}
				if (typeof ctx.client.switchModel === "function")
					await ctx.client.switchModel({
						provider: provider!,
						modelName: modelName!,
						maxContextSize,
						authMode,
						scope: "user",
					});
				else
					await ctx.client.updateConfiguration(
						{ model: { provider, modelName, maxContextSize, ...(authMode ? { authMode } : {}) } },
						"user",
					);
				ctx.notice(
					"status",
					`Model route changed to ${provider} / ${modelName}${maxContextSize ? ` · local limit ${maxContextSize.toLocaleString()}` : " · provider context discovered automatically"}. It applies to the next turn.`,
				);
				return;
			}
			ctx.notice(
				"warning",
				"Usage: /model show|discover <provider> [api|oauth]|set <provider> <model> [context-tokens] [api|oauth]",
			);
		},
	},
	{
		name: "graph",
		aliases: ["agents"],
		category: "config",
		description: "Manage named subagent profiles and execution policies",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("graph", args);
				return;
			}
			const config = (await ctx.client.getConfiguration()) as { agentGraph?: Record<string, unknown> };
			const graph = isRecord(config.agentGraph) ? config.agentGraph : {};
			const profiles = isRecord(graph["subagents"]) ? graph["subagents"] : {};
			const roleNames = [
				"coordinator",
				"learner",
				...Object.keys(profiles).sort((left, right) => left.localeCompare(right)),
				...(!Object.hasOwn(profiles, "default") && isRecord(graph["executor"]) ? ["default"] : []),
			];
			const roleConfig = (role: string): Record<string, unknown> => {
				if (role === "coordinator" || role === "learner") return isRecord(graph[role]) ? graph[role] : {};
				if (isRecord(profiles[role])) return profiles[role];
				return role === "default" && isRecord(graph["executor"]) ? graph["executor"] : {};
			};
			const patchForRole = (role: string, value: Record<string, unknown>) =>
				role === "coordinator" || role === "learner"
					? { agentGraph: { [role]: value } }
					: { agentGraph: { subagents: { [role]: value } } };
			if (!args.length || args[0] === "show") {
				ctx.showLines([
					"Agent profiles and policies:",
					...roleNames.flatMap((role) => {
						const value = roleConfig(role);
						return [
							`${role.padEnd(11)} ${String(value["provider"] ?? "inherit")} / ${String(value["modelName"] ?? "inherit")} · ${String(value["authMode"] ?? "inherit")}`,
							`  limits: context ${String(value["contextLength"] ?? "inherit")} · local ${String(value["maxContextSize"] ?? "inherit")} · output ${String(value["maxOutputTokens"] ?? "inherit")} · steps ${String(value["maxSteps"] ?? "inherit")}`,
							`  policy: permission ${String(value["permissionProfile"] ?? "inherit")} · interaction ${String(value["interactionMode"] ?? "inherit")} · tools ${formatGraphTools(value["tools"])}`,
						];
					}),
					"Use /graph set <agent-or-profile> <provider> <model> [api|oauth] or /graph set <agent-or-profile> <field> <value>.",
				]);
				return;
			}
			if (args[0] === "set" && args.length >= 4 && roleNames.includes(args[1]!)) {
				const [, role, providerOrField, modelOrValue, requestedAuthMode] = args;
				const fields = new Set([
					"baseUrl",
					"contextLength",
					"maxContextSize",
					"maxOutputTokens",
					"maxSteps",
					"runTimeoutMs",
					"maxQueuedRuns",
					"timeoutMs",
					"systemPrompt",
					"permissionProfile",
					"interactionMode",
					"tools",
				]);
				if (fields.has(providerOrField!)) {
					// Bounded-run parameters belong to the learner route; timeoutMs
					// belongs to worker profiles. The document schema rejects the
					// other combinations, so fail fast with a clearer message.
					if ((providerOrField === "runTimeoutMs" || providerOrField === "maxQueuedRuns") && role !== "learner") {
						ctx.notice("warning", `${providerOrField} only applies to the learner.`);
						return;
					}
					if (providerOrField === "timeoutMs" && (role === "coordinator" || role === "learner")) {
						ctx.notice("warning", "timeoutMs only applies to subagent profiles.");
						return;
					}
					const value = parseGraphField(providerOrField!, args.slice(3).join(" "));
					if (value === undefined) {
						ctx.notice("warning", `Invalid ${providerOrField} value.`);
						return;
					}
					await ctx.client.updateConfiguration(patchForRole(role!, { [providerOrField!]: value }), "user");
					ctx.notice("status", `Graph ${role} ${providerOrField} updated.`);
					return;
				}
				const provider = providerOrField;
				const modelName = modelOrValue;
				const authMode = requestedAuthMode === "oauth" || requestedAuthMode === "api" ? requestedAuthMode : undefined;
				await ctx.client.updateConfiguration(
					patchForRole(role!, { provider, modelName, ...(authMode ? { authMode } : {}) }),
					"user",
				);
				ctx.notice(
					"status",
					`Graph ${role} route set to ${provider} / ${modelName}${authMode ? ` · ${authMode}` : ""}.`,
				);
				return;
			}
			ctx.notice(
				"warning",
				"Usage: /graph show|set <agent-or-profile> <provider> <model> [api|oauth] | /graph set <agent-or-profile> <field> <value>",
			);
		},
	},
	{
		name: "config",
		aliases: ["settings"],
		category: "config",
		description: "Open the settings panel",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("config", args);
				return;
			}
			const [sub, ...rest] = args;
			if (!sub || sub === "get") {
				ctx.notice("warning", "Configuration is available through the guided Settings panel.");
				return;
			}
			if (sub === "path") {
				ctx.showLines([await ctx.client.configurationPath(rest[0] === "user" ? "user" : "project")]);
				return;
			}
			if (sub === "set" && rest.length >= 2) {
				ctx.notice(
					"warning",
					"Use the guided Settings panel to change a validated field; raw JSON values are not accepted.",
				);
				return;
			}
			ctx.notice("warning", "Usage: /config [get]|set <key> <json> [user|project]|path [user|project]");
		},
	},
	{
		name: "auth",
		category: "config",
		description: "Open the provider credential manager",
		argumentHint: "(interactive)",
		async run(args, ctx) {
			const [sub, provider, ...rest] = args;
			// Typed login intercepts before the panel: OAuth-capable providers go
			// through the same credential-only setup wizard the /auth panel uses,
			// so device codes and interactive prompts have a surface.
			if (sub === "login" && provider) {
				if (SETUP_PROVIDERS.some((entry) => entry.id === provider && entry.authMode === "oauth")) {
					if (ctx.openOAuthSetup) {
						await ctx.openOAuthSetup(provider);
						return;
					}
					if (typeof ctx.client.loginOAuth !== "function") {
						ctx.notice("warning", "OAuth login is unavailable in this host.");
						return;
					}
					ctx.notice("status", `Starting OAuth login for ${provider}; follow the verification instructions…`);
					await ctx.client.loginOAuth(provider);
					ctx.notice("status", `OAuth login complete for ${provider}.`);
					return;
				}
				if (SETUP_PROVIDERS.some((entry) => entry.id === provider)) {
					if (ctx.openPanel) {
						await ctx.openPanel("auth", ["set", provider]);
						return;
					}
					ctx.notice("warning", `${provider} uses an API key. Set it with /auth set ${provider} <api-key>.`);
					return;
				}
				ctx.notice("error", `Unknown provider: ${provider}`);
				return;
			}
			if (ctx.openPanel) {
				await ctx.openPanel("auth", args);
				return;
			}
			if (sub === "status" && provider) {
				ctx.showLines([`${provider}: ${(await ctx.client.hasCredential(provider)) ? "configured" : "not configured"}`]);
				return;
			}
			if (sub === "set" && provider && rest.length) {
				await ctx.client.setApiKey(provider, rest.join(" "));
				ctx.notice("status", `Credential set for ${provider}.`);
				return;
			}
			if (sub === "remove" && provider) {
				if (!(await ctx.confirm(`Remove credential for ${provider}?`))) return;
				await ctx.client.removeCredential(provider);
				ctx.notice("status", `Credential removed for ${provider}.`);
				return;
			}
			ctx.notice("warning", "Usage: /auth status|set|remove|login <provider> [api-key]");
		},
	},
	{
		name: "permission",
		aliases: ["permissions"],
		category: "config",
		description: "Manage default permission rules; worker policies stay in /graph",
		argumentHint: "(interactive)",
		availability: "always",
		async run(_args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("config", ["permission"]);
				return;
			}
			ctx.notice("warning", "Use /config permission for guided default permission controls.");
		},
	},
	{
		name: "setup",
		category: "config",
		description: "Connect a provider credential; assign models from /model or /graph",
		argumentHint: "(no arguments)",
		availability: "always",
		async run(_args, ctx) {
			await ctx.openSetup();
		},
	},
	{
		name: "trust",
		category: "config",
		description: "Inspect or change workspace trust",
		argumentHint: "(interactive)",
		availability: "always",
		async run(args, ctx) {
			if (ctx.openPanel) {
				await ctx.openPanel("trust", args);
				return;
			}
			const [sub] = args;
			if (!sub || sub === "status") {
				const status = await ctx.client.inspectWorkspaceTrust();
				ctx.showLines([
					`Workspace: ${status.workspace}`,
					status.hasSecurityConfiguration
						? status.trusted
							? "Trusted."
							: `Not trusted (${status.reason ?? "not_trusted"}).`
						: "No security-sensitive project configuration.",
				]);
				return;
			}
			if (sub === "grant") {
				await ctx.client.grantWorkspaceTrust();
				ctx.notice("status", "Workspace trusted.");
				return;
			}
			if (sub === "revoke") {
				if (!(await ctx.confirm("Revoke trust for this workspace?"))) return;
				await ctx.client.revokeWorkspaceTrust();
				ctx.notice("status", "Workspace trust revoked.");
				return;
			}
			ctx.notice("warning", "Usage: /trust [status]|grant|revoke");
		},
	},
];

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function numberValue(value: unknown): number | undefined {
	return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function sourceLabel(value: unknown): string {
	return value === "authoritative" ||
		value === "catalog" ||
		value === "configured" ||
		value === "estimated" ||
		value === "unknown"
		? value
		: "unknown";
}

function formatGraphTools(value: unknown): string {
	return Array.isArray(value) && value.every((item) => typeof item === "string") && value.length
		? value.join(",")
		: "inherit";
}

function parseGraphField(field: string, raw: string): string | number | string[] | undefined {
	const value = raw.trim();
	if (!value) return undefined;
	if (
		[
			"contextLength",
			"maxContextSize",
			"maxOutputTokens",
			"maxSteps",
			"runTimeoutMs",
			"maxQueuedRuns",
			"timeoutMs",
		].includes(field)
	) {
		const number = Number(value);
		return Number.isFinite(number) && number > 0 ? number : undefined;
	}
	if (field === "tools") {
		const tools = value
			.split(",")
			.map((item) => item.trim())
			.filter(Boolean);
		return tools.length ? tools : undefined;
	}
	return value;
}

function modelIdsEqual(provider: string, left: string, right: string): boolean {
	const normalize = (value: string) =>
		value
			.trim()
			.toLowerCase()
			.replace(/^models\//, "");
	const a = normalize(left);
	const b = normalize(right);
	if (a === b) return true;
	if (provider === "kimi" || provider === "kimi-code") {
		const canonical = (value: string) => (value === "kimi-k3" || value === "k3[1m]" ? "k3" : value);
		return canonical(a) === canonical(b);
	}
	return false;
}

export function findSlashCommand(name: string): SlashCommand | undefined {
	return slashCommands.find((command) => command.name === name || command.aliases?.includes(name));
}

export function slashCommandNames(): readonly string[] {
	return slashCommands.filter((command) => !command.hidden).map((command) => `/${command.name}`);
}

/** Match aliases during completion without rendering aliases as separate commands. */
export function slashCommandCompletions(query: string): readonly string[] {
	const normalized = query.trim().toLowerCase();
	return slashCommands
		.filter(
			(command) =>
				!command.hidden &&
				(command.name.startsWith(normalized) || command.aliases?.some((alias) => alias.startsWith(normalized))),
		)
		.map((command) => `/${command.name}`);
}
