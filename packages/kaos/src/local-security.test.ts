import { mkdtemp, mkdir, rm, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { LocalKaos, PathSecurityError } from "./local.js";

const roots: string[] = [];
afterEach(async () => {
	for (const root of roots.splice(0)) {
		if (!path.resolve(root).startsWith(`${path.resolve(tmpdir())}${path.sep}`)) throw new Error("Unsafe test cleanup path");
		await rm(root, { recursive: true, force: true });
	}
});

describe("workspace path boundary", () => {
	it("rejects lexical traversal beyond the workspace", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-path-"));
		roots.push(root);
		const workspace = path.join(root, "workspace");
		await mkdir(workspace);
		const kaos = new LocalKaos({ cwd: workspace });
		await expect(kaos.writeText("../outside.txt", "blocked")).rejects.toBeInstanceOf(PathSecurityError);
	});

	it("rejects symlink targets beyond the workspace", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-path-"));
		roots.push(root);
		const workspace = path.join(root, "workspace");
		const outside = path.join(root, "outside");
		await mkdir(workspace);
		await mkdir(outside);
		await symlink(outside, path.join(workspace, "linked"), process.platform === "win32" ? "junction" : "dir");
		const kaos = new LocalKaos({ cwd: workspace });
		await expect(kaos.resolveForPolicy("linked/new.txt")).rejects.toBeInstanceOf(PathSecurityError);
		await expect(kaos.writeText("linked/new.txt", "blocked")).rejects.toBeInstanceOf(PathSecurityError);
	});
});
