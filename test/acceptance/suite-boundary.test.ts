import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";

const root = path.resolve(import.meta.dirname, "../..");

describe("acceptance-suite boundary", () => {
	it("keeps product-facing tests isolated from source internals", async () => {
		const acceptanceRoot = path.join(root, "test", "acceptance");
		const tests = await findTests(acceptanceRoot, "test/acceptance");
		expect(tests.length).toBeGreaterThanOrEqual(2);
		for (const file of tests) {
			expect(file.replaceAll("\\", "/")).toMatch(/^test\/acceptance\//);
			if (file.replaceAll("\\", "/") === "test/acceptance/suite-boundary.test.ts") continue;
			const source = await readFile(path.join(root, file), "utf8");
			expect(source).not.toMatch(
				/@kageko\/|packages\/.+\/src|apps\/kageko\/src|KagekoHarness|VirtualTerminal|KagekoTui/,
			);
		}
	});
});

async function findTests(directory: string, relative: string): Promise<string[]> {
	const entries = await readdir(directory, { withFileTypes: true });
	const matches: string[] = [];
	for (const entry of entries) {
		if (entry.name === "node_modules" || entry.name === ".git" || entry.name === "dist") continue;
		const next = path.join(relative, entry.name);
		if (entry.isDirectory()) matches.push(...(await findTests(path.join(directory, entry.name), next)));
		else if (/\.(?:test|spec)\.[cm]?[jt]sx?$/.test(entry.name)) matches.push(next);
	}
	return matches;
}
