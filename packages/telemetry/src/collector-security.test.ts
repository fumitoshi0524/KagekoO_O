import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { expect, it } from "vitest";
import { TelemetryCollector } from "./collector.js";

it("keeps telemetry disabled by default and redacts secrets when enabled", async () => {
	const root = await mkdtemp(path.join(tmpdir(), "kageko-telemetry-"));
	try {
		const disabled = new TelemetryCollector({ kagekoDir: root });
		disabled.record({ type: "test", api_key: "sk-abcdefghijklmnop" });
		expect((await disabled.previewUpload()).events).toEqual([]);
		await disabled.close();

		const enabled = new TelemetryCollector({ enabled: true, kagekoDir: root });
		enabled.record({ type: "test", api_key: "sk-abcdefghijklmnop", message: "Bearer sk-abcdefghijklmnop" });
		const preview = await enabled.previewUpload();
		expect(JSON.stringify(preview.events)).not.toContain("sk-abcdefghijklmnop");
		expect(JSON.stringify(preview.events)).toContain("[REDACTED]");
		await enabled.close();
	} finally {
		if (!path.resolve(root).startsWith(`${path.resolve(tmpdir())}${path.sep}`)) throw new Error("Unsafe test cleanup path");
		await rm(root, { recursive: true, force: true });
	}
});
