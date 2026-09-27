import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { WorkspaceTrustError, WorkspaceTrustService } from "./workspace-trust-service.js";

const roots: string[] = [];
afterEach(async () => {
	for (const root of roots.splice(0)) {
		if (!path.resolve(root).startsWith(`${path.resolve(tmpdir())}${path.sep}`)) throw new Error("Unsafe test cleanup path");
		await rm(root, { recursive: true, force: true });
	}
});

describe("project extension trust boundary", () => {
	it("requires explicit trust and revokes it when extension code changes", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-extension-trust-"));
		roots.push(root);
		const workspace = path.join(root, "workspace");
		const extension = path.join(workspace, ".kageko", "plugins", "sample", "index.js");
		await mkdir(path.dirname(extension), { recursive: true });
		await writeFile(extension, "export default 'reviewed';\n");
		const trust = new WorkspaceTrustService(path.join(root, "trust.json"));

		await expect(trust.assertTrusted(workspace)).rejects.toMatchObject({
			name: "WorkspaceTrustError",
			status: { reason: "not_trusted" },
		});
		await trust.grant(workspace);
		await expect(trust.assertTrusted(workspace)).resolves.toMatchObject({ trusted: true });

		await writeFile(extension, "export default 'changed';\n");
		await expect(trust.assertTrusted(workspace)).rejects.toMatchObject({
			name: WorkspaceTrustError.name,
			status: { reason: "configuration_changed" },
		});
	});
});
