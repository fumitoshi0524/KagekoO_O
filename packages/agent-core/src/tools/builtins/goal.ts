import * as crypto from "node:crypto";
import type { Tool, ToolContext } from "../types.js";
import type { DurableEvent } from "@kageko/protocol";

export interface GoalBudget {
	maxTurns?: number;
	maxTokens?: number;
	maxWallClockMs?: number;
}

export interface Goal {
	id: string;
	objective: string;
	completionCriterion?: string;
	status: "active" | "paused" | "completed" | "blocked" | "failed";
	budget: GoalBudget | null;
	turnsUsed: number;
	createdAt: number;
	note?: string;
	terminalReason?: string;
	pauseReason?: string;
	blockReason?: string;
}

interface GoalEventGoal {
	id: string;
	description: string;
	status: string;
	budget?: GoalBudget | null;
	turnsUsed?: number;
	createdAt?: number;
}

export interface GoalStore {
	activeGoal?: Goal | null;
	goals?: Goal[];
	_replayed?: boolean;
	[key: string]: unknown;
}

interface CreateGoalArgs {
	objective: string;
	completionCriterion?: string;
	budget?: GoalBudget;
}

interface UpdateGoalArgs {
	status?: "active" | "paused" | "completed" | "blocked" | "failed";
	note?: string;
}

interface SetGoalBudgetArgs {
	maxTurns?: number;
	maxTokens?: number;
	maxWallClockMs?: number;
}

function asGoalStore(session: NonNullable<ToolContext["session"]>): GoalStore {
	if (!session.goalStore) {
		session.goalStore = {};
	}
	return session.goalStore as GoalStore;
}

export const createGoalTool: Tool = {
	name: "create_goal",
	description: "Create a new tracked goal for the session.",
	parameters: {
		type: "object",
		properties: {
			objective: { type: "string", description: "Goal objective" },
			completionCriterion: { type: "string", description: "How to know the goal is complete" },
			budget: {
				type: "object",
				description: "Optional budget for this goal",
				properties: {
					maxTurns: { type: "number" },
					maxTokens: { type: "number" },
					maxWallClockMs: { type: "number" },
				},
			},
		},
		required: ["objective"],
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { objective, completionCriterion, budget } = args as unknown as CreateGoalArgs;
		const session = context.session;
		if (!session) {
			throw new Error("Goal tools require a session");
		}
		const store = asGoalStore(session);
		const now = Date.now();
		const goal: Goal = {
			id: crypto.randomUUID(),
			objective,
			completionCriterion,
			status: "active",
			budget: budget ?? null,
			turnsUsed: 1,
			createdAt: now,
		};
		await session.recordStore?.append({
			type: "goal.created",
			data: { goal: toEventGoal(goal) },
		});
		store.activeGoal = goal;
		if (!store.goals) store.goals = [];
		store.goals.push(goal);
		return { output: `Goal created: ${objective}` };
	},
};

export const updateGoalTool: Tool = {
	name: "update_goal",
	description: "Update the active goal status or progress.",
	parameters: {
		type: "object",
		properties: {
			status: { type: "string", enum: ["active", "paused", "completed", "blocked", "failed"] },
			note: { type: "string" },
		},
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { status, note } = args as unknown as UpdateGoalArgs;
		const session = context.session;
		if (!session) {
			throw new Error("Goal tools require a session");
		}
		const store = asGoalStore(session);
		if (!store.activeGoal) return { output: "No active goal.", isError: true };
		const nextGoal = { ...store.activeGoal };
		let changed = false;
		if (status) {
			const nextStatus = status === "failed" ? "blocked" : status;
			if (nextGoal.status !== nextStatus) {
				nextGoal.status = nextStatus;
				changed = true;
			}
		}
		if (note !== undefined && nextGoal.note !== note) {
			nextGoal.note = note;
			changed = true;
		}
		if (changed) {
			if (nextGoal.status === "completed") {
				// Emit the dedicated terminal event so replay hydrates
				// terminalReason and clears activeGoal exactly like the live
				// path; a plain goal.updated would leave both divergent.
				await session.recordStore?.append({
					type: "goal.completed",
					data: note === undefined ? { goalId: nextGoal.id } : { goalId: nextGoal.id, reason: note },
				});
				nextGoal.terminalReason = note;
				// The completion note is carried as terminalReason; drop it
				// from the goal itself — note is not durable, so keeping it
				// would leave live state divergent from replay.
				delete nextGoal.note;
				const active = store.activeGoal;
				Object.assign(active, nextGoal);
				delete active.note;
				store.activeGoal = null;
			} else {
				await session.recordStore?.append({
					type: "goal.updated",
					data: { goal: toEventGoal(nextGoal) },
				});
				Object.assign(store.activeGoal, nextGoal);
			}
		}
		return { output: `Goal updated: ${status ?? note}` };
	},
};

export const getGoalTool: Tool = {
	name: "get_goal",
	description: "Get the active goal.",
	parameters: { type: "object", properties: {} },
	execute(_args: Record<string, unknown>, context: ToolContext) {
		const session = context.session;
		if (!session) {
			throw new Error("Goal tools require a session");
		}
		const store = asGoalStore(session);
		if (!store.activeGoal) return { output: "No active goal." };
		return { output: JSON.stringify(store.activeGoal, null, 2) };
	},
};

export const setGoalBudgetTool: Tool = {
	name: "set_goal_budget",
	description: "Set a budget (max turns, tokens, or wall-clock ms) for the active goal.",
	parameters: {
		type: "object",
		properties: {
			maxTurns: { type: "number" },
			maxTokens: { type: "number" },
			maxWallClockMs: { type: "number" },
		},
	},
	async execute(args: Record<string, unknown>, context: ToolContext) {
		const { maxTurns, maxTokens, maxWallClockMs } = args as unknown as SetGoalBudgetArgs;
		const session = context.session;
		if (!session) {
			throw new Error("Goal tools require a session");
		}
		const store = asGoalStore(session);
		if (!store.activeGoal) return { output: "No active goal.", isError: true };
		const budget: GoalBudget = {};
		if (maxTurns !== undefined) budget.maxTurns = maxTurns;
		if (maxTokens !== undefined) budget.maxTokens = maxTokens;
		if (maxWallClockMs !== undefined) budget.maxWallClockMs = maxWallClockMs;
		await session.recordStore?.append({
			type: "goal.updated",
			data: { goal: toEventGoal({ ...store.activeGoal, budget }) },
		});
		store.activeGoal.budget = budget;
		const parts: string[] = [];
		if (budget.maxTurns !== undefined) parts.push(`${budget.maxTurns} turns`);
		if (budget.maxTokens !== undefined) parts.push(`${budget.maxTokens} tokens`);
		if (budget.maxWallClockMs !== undefined) parts.push(`${budget.maxWallClockMs} ms`);
		return { output: `Goal budget set: ${parts.join(", ") || "none"}` };
	},
};

function toEventGoal(goal: Goal): GoalEventGoal {
	return {
		id: goal.id,
		description: goal.objective,
		status: goal.status,
		budget: goal.budget,
		turnsUsed: goal.turnsUsed,
		createdAt: goal.createdAt,
	};
}

/**
 * Replay goal lifecycle events into a goal store.
 * Maintains activeGoal as the most recent active goal.
 */
export function replayGoalEvents(events: DurableEvent[] | undefined, goalStore: GoalStore): void {
	if (!goalStore || goalStore._replayed) return;
	if (!goalStore.goals) goalStore.goals = [];
	for (const event of events ?? []) {
		if (!event || !event.type) continue;
		switch (event.type) {
			case "goal.created": {
				const g = event.data.goal as GoalEventGoal | undefined;
				if (!g || !g.id) continue;
				const goal: Goal = {
					id: g.id,
					objective: g.description,
					status: (g.status ?? "active") as Goal["status"],
					budget: g.budget ?? null,
					turnsUsed: g.turnsUsed ?? 1,
					createdAt: g.createdAt ?? Date.now(),
				};
				goalStore.goals.push(goal);
				if (goal.status === "active") {
					goalStore.activeGoal = goal;
				}
				break;
			}
			case "goal.updated": {
				const g = event.data.goal as GoalEventGoal | undefined;
				if (!g || !g.id) continue;
				const goal = goalStore.goals.find((existing) => existing.id === g.id);
				if (!goal) continue;
				if (g.description !== undefined) goal.objective = g.description;
				if (g.status !== undefined) goal.status = g.status as Goal["status"];
				if (g.budget !== undefined) goal.budget = g.budget;
				if (g.turnsUsed !== undefined) goal.turnsUsed = g.turnsUsed;
				if (goal.status === "active") {
					goalStore.activeGoal = goal;
				}
				break;
			}
			case "goal.completed":
			case "goal.blocked":
			case "goal.paused": {
				const goalId = event.data.goalId;
				if (!goalId) continue;
				const goal = goalStore.goals.find((existing) => existing.id === goalId);
				if (!goal) continue;
				const status = event.type.slice("goal.".length) as Goal["status"];
				goal.status = status;
				// Mirror the live write path (agent.ts): each terminal-ish event
				// records its reason on the matching field.
				const reason = event.data.reason as string | undefined;
				if (status === "paused") {
					goal.pauseReason = reason;
				} else if (status === "blocked") {
					goal.blockReason = reason;
				} else {
					goal.terminalReason = reason;
				}
				// Older journals can contain goal.paused. Paused goals remain
				// resumable state, unlike completed or blocked goals.
				if (status === "paused") goalStore.activeGoal = goal;
				else if (goalStore.activeGoal?.id === goalId) goalStore.activeGoal = null;
				break;
			}
		}
	}
	goalStore._replayed = true;
}
