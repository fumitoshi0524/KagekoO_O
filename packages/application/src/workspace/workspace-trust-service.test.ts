import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
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

	it("treats the Kageko home directory as the inherently trusted user layer", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-home-trust-"));
		roots.push(root);
		const home = path.join(root, "home");
		const extension = path.join(home, ".kageko", "plugins", "sample", "index.js");
		await mkdir(path.dirname(extension), { recursive: true });
		await writeFile(extension, "export default 'user-layer';\n");
		await writeFile(path.join(home, ".kageko", "config.json"), JSON.stringify({ permission: { defaultProfile: "auto" } }));

		const previousHome = process.env["KAGEKO_HOME"];
		process.env["KAGEKO_HOME"] = home;
		try {
			const trust = new WorkspaceTrustService(path.join(root, "trust.json"));
			await expect(trust.assertTrusted(home)).resolves.toMatchObject({ trusted: true });
		} finally {
			if (previousHome === undefined) delete process.env["KAGEKO_HOME"];
			else process.env["KAGEKO_HOME"] = previousHome;
		}
	});

	it("still gates security configuration below the home directory", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-home-trust-"));
		roots.push(root);
		const home = path.join(root, "home");
		const workspace = path.join(home, "project");
		const extension = path.join(workspace, ".kageko", "plugins", "sample", "index.js");
		await mkdir(path.dirname(extension), { recursive: true });
		await writeFile(extension, "export default 'reviewed';\n");

		const previousHome = process.env["KAGEKO_HOME"];
		process.env["KAGEKO_HOME"] = home;
		try {
			const trust = new WorkspaceTrustService(path.join(root, "trust.json"));
			await expect(trust.assertTrusted(workspace)).rejects.toMatchObject({
				name: "WorkspaceTrustError",
				status: { reason: "not_trusted" },
			});
		} finally {
			if (previousHome === undefined) delete process.env["KAGEKO_HOME"];
			else process.env["KAGEKO_HOME"] = previousHome;
		}
	});

	it("never records a trust entry for the user layer", async () => {
		const root = await mkdtemp(path.join(tmpdir(), "kageko-home-trust-"));
		roots.push(root);
		const home = path.join(root, "home");
		const extension = path.join(home, ".kageko", "plugins", "sample", "index.js");
		await mkdir(path.dirname(extension), { recursive: true });
		await writeFile(extension, "export default 'user-layer';\n");

		const previousHome = process.env["KAGEKO_HOME"];
		process.env["KAGEKO_HOME"] = home;
		const trustFile = path.join(root, "trust.json");
		try {
			const trust = new WorkspaceTrustService(trustFile);
			await trust.grant(home);
			// The user layer is inherently trusted, so granting must not persist
			// an entry that could go live if KAGEKO_HOME later moves elsewhere.
			await expect(readFile(trustFile, "utf8")).rejects.toMatchObject({ code: "ENOENT" });
		} finally {
			if (previousHome === undefined) delete process.env["KAGEKO_HOME"];
			else process.env["KAGEKO_HOME"] = previousHome;
		}
	});
});
