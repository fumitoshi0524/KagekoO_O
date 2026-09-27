import type { KagekoClient } from "@kageko/node-sdk";
import { runAuth } from "./commands/auth.js";
import { runCapability } from "./commands/capability.js";
import { runConfig } from "./commands/config.js";
import { runCron } from "./commands/cron.js";
import { runGoal } from "./commands/goal.js";
import { runLearning } from "./commands/learning.js";
import { runMcp } from "./commands/mcp.js";
import { runMemory } from "./commands/memory.js";
import { runSession } from "./commands/session.js";
import { runSkill } from "./commands/skill.js";
import { runTask } from "./commands/task.js";
import { runTrust } from "./commands/trust.js";
import { runPlugin } from "./plugin.js";
import { printHelp } from "./help.js";

export interface OperationalCommandContext {
	readonly client: KagekoClient;
	readonly args: readonly string[];
}

export const operationalCommands = new Set([
	"session",
	"config",
	"auth",
	"plugin",
	"task",
	"cron",
	"capability",
	"memory",
	"learning",
	"goal",
	"skill",
	"mcp",
	"trust",
	"help",
]);
export function isOperationalCommand(command: string | undefined): boolean {
	return command !== undefined && operationalCommands.has(command);
}

/** Dispatch commands that do not own the interactive terminal. */
export async function dispatchOperationalCommand(
	command: string | undefined,
	context: OperationalCommandContext,
): Promise<boolean> {
	switch (command) {
		case "session":
			await runSession(context.args, context.client);
			return true;
		case "config":
			await runConfig(context.args, context.client);
			return true;
		case "auth":
			await runAuth(context.args, context.client);
			return true;
		case "plugin":
			await runPlugin(context.args, context.client);
			return true;
		case "task":
			await runTask(context.args, context.client);
			return true;
		case "cron":
			await runCron(context.args, context.client);
			return true;
		case "capability":
			await runCapability(context.args, context.client);
			return true;
		case "memory":
			await runMemory(context.args, context.client);
			return true;
		case "learning":
			await runLearning(context.args, context.client);
			return true;
		case "goal":
			await runGoal(context.args, context.client);
			return true;
		case "skill":
			await runSkill(context.args, context.client);
			return true;
		case "mcp":
			await runMcp(context.args, context.client);
			return true;
		case "trust":
			await runTrust(context.args, context.client);
			return true;
		case "help":
			printHelp();
			return true;
		default:
			return false;
	}
}
