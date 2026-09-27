import { mkdtemp, mkdir, rm, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { createJsonFileStore } from "./json-file-store.js";

const roots: string[] = [];
afterEach(async () => {
	for (const root of roots.splice(0)) {
		if (!path.resolve(root).startsWith(`${path.resolve(tmpdir())}${path.sep}`)) throw new Error("Unsafe test cleanup path");
		await rm(root, { recursive: true, force: true });
	}
});

describe("credential JSON store directory permissions", () => {
	it("accepts a private secret directory under a public ancestor", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-secrets-"));
		roots.push(root);
		const parent = path.join(root, "private");
		await mkdir(parent, { mode: 0o700 });
		const store = createJsonFileStore(path.join(parent, "auth.json"));
		await store.writeAll({ provider: { token: "test-only" } });
		expect(await store.readAll()).toEqual({ provider: { token: "test-only" } });
	});

	it.skipIf(process.platform === "win32")("rejects a publicly readable secret directory", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-secrets-"));
		roots.push(root);
		const parent = path.join(root, "public");
		await mkdir(parent);
		await chmod(parent, 0o755);
		await expect(createJsonFileStore(path.join(parent, "auth.json")).writeAll({ token: "test-only" })).rejects.toThrow(
			"permissions are too broad",
		);
	});
});
