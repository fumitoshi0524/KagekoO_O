import { describe, expect, it } from "vitest";

import {
	formatSettingValue,
	parseSettingInput,
	readSettingValue,
	SETTINGS_SECTIONS,
	settingsSectionById,
	type SettingField,
} from "../src/tui/settings-catalog.js";

describe("settings catalog sections", () => {
	it("covers every section the settings panel exposes", () => {
		expect(SETTINGS_SECTIONS.map((section) => section.id)).toEqual([
			"permission",
			"interaction",
			"shell",
			"telemetry",
			"memory",
			"learning",
			"agents",
			"turns",
			"mcp",
		]);
	});

	it("keeps field paths safe for buildConfigPatch (letters/digits segments only)", () => {
		for (const section of SETTINGS_SECTIONS)
			for (const field of section.fields)
				for (const segment of field.path.split(".")) expect(segment).toMatch(/^[A-Za-z][A-Za-z0-9]*$/);
	});

	it("keeps field paths unique inside each section", () => {
		for (const section of SETTINGS_SECTIONS) {
			const paths = section.fields.map((field) => field.path);
			expect(new Set(paths).size).toBe(paths.length);
		}
	});

	it("exposes the thirteen learning keys", () => {
		const learning = settingsSectionById("learning");
		expect(learning?.fields.map((field) => field.path)).toEqual([
			"learning.autoApproveSkills",
			"learning.autoApproveCapabilities",
			"learning.minContentLength",
			"learning.maxContentLength",
			"learning.erroneousToolThreshold",
			"learning.maxPendingEntries",
			"learning.skillMinEvents",
			"learning.skillMinCompletedTurns",
			"learning.skillSynthesisCooldownEvents",
			"learning.skillSynthesisTimeoutMs",
			"learning.capabilitySynthesisTimeoutMs",
			"learning.mcpSynthesisTimeoutMs",
			"learning.skillSimilarityThreshold",
		]);
	});

	it("declares enum values for every enum field", () => {
		for (const section of SETTINGS_SECTIONS)
			for (const field of section.fields)
				if (field.type === "enum") expect(field.enumValues?.length).toBeGreaterThan(0);
	});
});

describe("readSettingValue", () => {
	const config = {
		telemetry: { enabled: true },
		agentGraph: { learner: { runTimeoutMs: 120_000 } },
		permission: { allowList: ["bash(git status)"] },
	};

	it("reads nested values", () => {
		expect(readSettingValue(config, "telemetry.enabled")).toBe(true);
		expect(readSettingValue(config, "agentGraph.learner.runTimeoutMs")).toBe(120_000);
		expect(readSettingValue(config, "permission.allowList")).toEqual(["bash(git status)"]);
	});

	it("returns undefined for absent or non-object segments", () => {
		expect(readSettingValue(config, "agentGraph.learner.maxQueuedRuns")).toBeUndefined();
		expect(readSettingValue(config, "telemetry.enabled.deeper")).toBeUndefined();
		expect(readSettingValue(config, "mcp.connectTimeoutMs")).toBeUndefined();
	});
});

describe("formatSettingValue", () => {
	const boolField = settingsSectionById("telemetry")!.fields[0]!;
	const listField = settingsSectionById("permission")!.fields.find((field) => field.type === "stringList")!;
	const numberField = settingsSectionById("agents")!.fields[0]!;

	it("formats booleans as on/off", () => {
		expect(formatSettingValue(boolField, true)).toBe("on");
		expect(formatSettingValue(boolField, false)).toBe("off");
	});

	it("formats absent values as default", () => {
		expect(formatSettingValue(numberField, undefined)).toBe("default");
		expect(formatSettingValue(boolField, undefined)).toBe("default");
	});

	it("formats lists inline or as a count", () => {
		expect(formatSettingValue(listField, [])).toBe("empty");
		expect(formatSettingValue(listField, ["a", "b"])).toBe("a, b");
		expect(
			formatSettingValue(
				listField,
				Array.from({ length: 8 }, (_, index) => `rule-${index}-long`),
			),
		).toBe("8 entries");
	});

	it("formats numbers and strings plainly", () => {
		expect(formatSettingValue(numberField, 12)).toBe("12");
		const executable = settingsSectionById("shell")!.fields.find((field) => field.path === "shell.executable")!;
		expect(formatSettingValue(executable, "pwsh")).toBe("pwsh");
	});
});

describe("parseSettingInput", () => {
	const concurrency = settingsSectionById("turns")!.fields.find((field) => field.path === "turns.toolConcurrency")!;
	const ratio = settingsSectionById("turns")!.fields.find((field) => field.path === "compaction.targetRatio")!;
	const executable = settingsSectionById("shell")!.fields.find((field) => field.path === "shell.executable")!;
	const dialect = settingsSectionById("shell")!.fields.find((field) => field.path === "shell.dialect")!;
	const contentLength = settingsSectionById("learning")!.fields.find(
		(field) => field.path === "learning.minContentLength",
	)!;

	it("accepts in-range integers", () => {
		expect(parseSettingInput(concurrency, "4")).toEqual({ ok: true, value: 4 });
	});

	it("rejects out-of-range numbers with a range message", () => {
		const result = parseSettingInput(concurrency, "99");
		expect(result).toEqual({ ok: false, message: "Tool concurrency must be between 1 and 16." });
	});

	it("rejects non-numbers and non-integers", () => {
		expect(parseSettingInput(concurrency, "abc").ok).toBe(false);
		expect(parseSettingInput(concurrency, "1.5")).toEqual({
			ok: false,
			message: "Tool concurrency must be an integer.",
		});
	});

	it("accepts fractional ratios inside 0–1", () => {
		expect(parseSettingInput(ratio, "0.5")).toEqual({ ok: true, value: 0.5 });
		expect(parseSettingInput(ratio, "1.5").ok).toBe(false);
	});

	it("applies minimum-only bounds", () => {
		expect(parseSettingInput(contentLength, "0")).toEqual({ ok: true, value: 0 });
		expect(parseSettingInput(contentLength, "-1")).toEqual({
			ok: false,
			message: "Minimum content length must be at least 0.",
		});
	});

	it("validates strings and enum members", () => {
		expect(parseSettingInput(executable, "pwsh")).toEqual({ ok: true, value: "pwsh" });
		expect(parseSettingInput(executable, "  ").ok).toBe(false);
		expect(parseSettingInput(dialect, "zsh").ok).toBe(false);
		expect(parseSettingInput(dialect, "bash")).toEqual({ ok: true, value: "bash" });
	});

	it("rejects text input for boolean fields", () => {
		const enabled: SettingField = settingsSectionById("telemetry")!.fields[0]!;
		expect(parseSettingInput(enabled, "true").ok).toBe(false);
	});
});
