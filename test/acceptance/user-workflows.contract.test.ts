import { afterEach, describe, expect, it } from "vitest";
import { createProductEnvironment, json, runProduct, type ProductEnvironment } from "./product-fixture.js";

const products: ProductEnvironment[] = [];

afterEach(async () => {
	await Promise.all(products.splice(0).map((product) => product.cleanup()));
});

describe("installed CLI user workflows", () => {
	it("keeps a user's session, goal, memory, schedule, trust and credentials coherent across independent processes", async () => {
		const product = await createProductEnvironment();
		products.push(product);
		const created = await runProduct(product, ["session", "create", "--title", "Release readiness", "--json"]);
		expect(created.code, created.stderr).toBe(0);
		const sessionId = (json(created) as { sessionId: string; title: string }).sessionId;
		expect((json(created) as { title: string }).title).toBe("Release readiness");

		for (const args of [
			["session", "rename", sessionId, "Release verified"],
			["goal", "create", "--session", sessionId, "--objective", "Ship only verified artifacts"],
			["goal", "pause", "--session", sessionId],
			["goal", "resume", "--session", sessionId],
			["memory", "remember", "--session", sessionId, "A release needs a clean production acceptance run."],
			["config", "set", "model.maxOutputTokens", "1024"],
			["trust", "grant"],
			["auth", "set", "acceptance-provider", "--api-key", "not-a-real-secret"],
		] as const) {
			const result = await runProduct(product, args);
			expect(result.code, `${args.join(" ")}\n${result.stderr}`).toBe(0);
		}

		const recalled = await runProduct(product, ["memory", "recall", "--session", sessionId, "production acceptance"]);
		expect(recalled.code, recalled.stderr).toBe(0);
		expect(recalled.stdout).toContain("clean production acceptance run");
		const goal = await runProduct(product, ["goal", "status", "--session", sessionId, "--json"]);
		expect(goal.code, goal.stderr).toBe(0);
		expect(json(goal)).toMatchObject({ objective: "Ship only verified artifacts", status: "active" });
		const listed = await runProduct(product, ["session", "list", "--json"]);
		expect(listed.code, listed.stderr).toBe(0);
		expect(json(listed)).toEqual(
			expect.arrayContaining([expect.objectContaining({ sessionId, title: "Release verified" })]),
		);
		const trust = await runProduct(product, ["trust", "status", "--json"]);
		expect(trust.code, trust.stderr).toBe(0);
		expect(trust.stdout).toMatch(/trusted|trust/i);
		const credential = await runProduct(product, ["auth", "status", "acceptance-provider"]);
		expect(credential.code, credential.stderr).toBe(0);
		expect(credential.stdout).toContain("Credential configured");

		const cron = await runProduct(product, [
			"cron",
			"create",
			"--session",
			sessionId,
			"--schedule",
			"*/5 * * * *",
			"--prompt",
			"check release",
			"--once",
		]);
		expect(cron.code, cron.stderr).toBe(0);
		const cronId = (json(cron) as { id: string }).id;
		const cronList = await runProduct(product, ["cron", "list", "--session", sessionId, "--json"]);
		expect(cronList.code, cronList.stderr).toBe(0);
		expect(json(cronList)).toEqual(expect.arrayContaining([expect.objectContaining({ id: cronId, recurring: false })]));
		const deletedCron = await runProduct(product, ["cron", "delete", cronId, "--session", sessionId, "--yes"]);
		expect(deletedCron.code, deletedCron.stderr).toBe(0);
		const activities = await runProduct(product, ["task", "list", "--session", sessionId, "--all", "--json"]);
		expect(activities.code, activities.stderr).toBe(0);
		expect(json(activities)).toEqual(expect.any(Array));

		for (const args of [
			["goal", "complete", "--session", sessionId],
			["session", "archive", sessionId],
			["session", "unarchive", sessionId],
			["auth", "remove", "acceptance-provider", "--yes"],
			["trust", "revoke", "--yes"],
		] as const) {
			const result = await runProduct(product, args);
			expect(result.code, `${args.join(" ")}\n${result.stderr}`).toBe(0);
		}
		const absentCredential = await runProduct(product, ["auth", "status", "acceptance-provider"]);
		expect(absentCredential.code, absentCredential.stderr).toBe(0);
		expect(absentCredential.stdout).toContain("No credential configured");
	}, 180_000);

	it("refuses destructive or malformed requests before they can mutate a user's state", async () => {
		const product = await createProductEnvironment();
		products.push(product);
		const created = await runProduct(product, ["session", "create", "--json"]);
		const sessionId = (json(created) as { sessionId: string }).sessionId;
		for (const args of [
			["session", "delete", sessionId],
			["learning", "reject", "missing", "--session", sessionId],
			["mcp", "add", "unsafe", "{not-json}", "--session", sessionId],
			["mcp", "add", "unsafe", '{"command":"cmd.exe","args":[]}', "--session", sessionId],
			["capability", "list", "--session", sessionId, "--kind", "not-a-kind"],
			["config", "set", "model.maxOutputTokens", "not-json"],
		] as const) {
			const result = await runProduct(product, args);
			expect(result.code, `${args.join(" ")} unexpectedly succeeded`).not.toBe(0);
		}
		const stillThere = await runProduct(product, ["session", "resume", sessionId, "--json"]);
		expect(stillThere.code, stillThere.stderr).toBe(0);
	}, 180_000);
});
