import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { appendInputHistory, inputHistoryFile, loadInputHistory } from "../src/tui/utils/input-history.js";

const directories: string[] = [];

afterEach(async () => {
	await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })));
});

describe("input history", () => {
	it("persists valid prompts per workspace and ignores duplicate consecutive writes", async () => {
		const dataDirectory = await mkdtemp(path.join(tmpdir(), "kageko-history-"));
		directories.push(dataDirectory);
		const file = inputHistoryFile("F:/workspace", dataDirectory);

		expect(await appendInputHistory(file, "first prompt")).toBe(true);
		expect(await appendInputHistory(file, "first prompt", "first prompt")).toBe(false);
		expect(await appendInputHistory(file, "second prompt", "first prompt")).toBe(true);
		expect(await loadInputHistory(file)).toEqual(["first prompt", "second prompt"]);
	});

	it("isolates histories by working directory", () => {
		const dataDirectory = path.join(tmpdir(), "kageko-history-paths");
		expect(inputHistoryFile("F:/one", dataDirectory)).not.toBe(inputHistoryFile("F:/two", dataDirectory));
	});
});
