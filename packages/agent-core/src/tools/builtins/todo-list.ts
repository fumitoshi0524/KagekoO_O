import { randomUUID } from "node:crypto";
import type { Tool, ToolContext, ToolSessionPort, TodoStorePort } from "../types.js";

interface TodoArgs {
	action: "add" | "done" | "list" | "clear";
	title?: string;
	index?: number;
}

export const todoListTool: Tool<TodoArgs> = {
	name: "todo_list",
	description: "Manage a session-scoped todo list. Supports add, mark done, list, and clear.",
	parameters: {
		type: "object",
		properties: {
			action: {
				type: "string",
				enum: ["add", "done", "list", "clear"],
				description: "Action to perform",
			},
			title: { type: "string", description: "Title of the todo (for add)" },
			index: { type: "number", description: "1-based index (for done)" },
		},
		required: ["action"],
	},
	async execute(args: TodoArgs, { session }: ToolContext) {
		const store = ensureStore(session);
		switch (args.action) {
			case "add": {
				if (!args.title) return { output: "Missing title", isError: true };
				store.todos.push({ todoId: randomUUID(), text: args.title, status: "pending" });
				const error = await persist(store);
				if (error) return error;
				return { output: `Added: ${args.title}` };
			}
			case "done": {
				if (!Number.isFinite(args.index) || args.index! < 1 || args.index! > store.todos.length) {
					return { output: "Invalid index", isError: true };
				}
				store.todos[args.index! - 1]!.status = "completed";
				const error = await persist(store);
				if (error) return error;
				return { output: `Marked done: ${store.todos[args.index! - 1]!.text}` };
			}
			case "clear": {
				store.todos = [];
				const error = await persist(store);
				if (error) return error;
				return { output: "Cleared todos." };
			}
			case "list":
			default: {
				if (store.todos.length === 0) return { output: "No todos." };
				const lines = store.todos.map((t, i) => `${i + 1}. [${t.status === "completed" ? "x" : " "}] ${t.text}`);
				return { output: lines.join("\n") };
			}
		}
	},
};

function ensureStore(session: ToolSessionPort | undefined): TodoStorePort {
	if (!session) throw new Error("todo_list requires a session");
	return (session.todoStore ??= { todos: [] });
}

async function persist(store: TodoStorePort): Promise<{ output: string; isError: true } | undefined> {
	try {
		await store.save?.();
	} catch (error) {
		return { output: `Failed to persist todo list: ${(error as Error).message}`, isError: true };
	}
}
