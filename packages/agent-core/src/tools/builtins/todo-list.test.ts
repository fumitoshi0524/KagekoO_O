import { describe, expect, it, vi } from "vitest";
import { todoListTool } from "./todo-list.js";

describe("todo_list", () => {
	it("persists every mutation when its session provides a durable store", async () => {
		const save = vi.fn(async () => {});
		const session = { todoStore: { todos: [], save } };
		const execute = todoListTool.execute!;
		await execute({ action: "add", title: "publish workflow" }, { session } as never);
		await execute({ action: "done", index: 1 }, { session } as never);
		await execute({ action: "clear" }, { session } as never);
		expect(save).toHaveBeenCalledTimes(3);
		expect(session.todoStore.todos).toEqual([]);
	});
});
