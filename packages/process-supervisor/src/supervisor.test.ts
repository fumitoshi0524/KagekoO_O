import * as os from "node:os";
import * as path from "node:path";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { SessionProcessSupervisor } from "./supervisor.js";

describe("SessionProcessSupervisor crash recovery", () => {
	// A SIGKILLed or container-killed supervisor leaves its control files
	// behind, and the recorded pid is recycled by an unrelated process. The
	// descriptor below is exactly that shape: pid alive (this test process)
	// but nothing serving the endpoint. connectOrStart must discard the stale
	// credentials and boot a fresh supervisor instead of refusing ownership.
	it("replaces stale credentials whose pid is alive but not serving", async () => {
		const runtimeDir = await mkdtemp(path.join(os.tmpdir(), "supervisor-test-"));
		try {
			const endpoint = process.platform === "win32"
				? "\\\\.\\pipe\\kageko-supervisor-test-dead-endpoint"
				: path.join(runtimeDir, "dead.sock");
			const descriptor = { version: 1, pid: process.pid, endpoint, createdAt: Date.now() };
			await writeFile(path.join(runtimeDir, "supervisor.json"), JSON.stringify(descriptor), { mode: 0o600 });
			await writeFile(path.join(runtimeDir, "supervisor.token"), "a".repeat(64), { mode: 0o600 });
			const supervisor = new SessionProcessSupervisor(runtimeDir);
			await expect(supervisor.connectOrStart()).resolves.toBe("started");
			await supervisor.shutdown();
		} finally {
			await rm(runtimeDir, { recursive: true, force: true });
		}
	}, 60_000);
});
