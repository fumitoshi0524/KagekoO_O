import { appendFile, mkdir, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import os from "node:os";
import path from "node:path";

export interface InputHistoryEntry {
	readonly content: string;
}

/** Kimi-compatible append-only history location, isolated per working directory. */
export function inputHistoryFile(
	workDir: string,
	dataDir = process.env["KAGEKO_DATA_DIR"] ?? path.join(os.homedir(), ".kageko"),
): string {
	const digest = createHash("md5").update(workDir, "utf8").digest("hex");
	return path.join(dataDir, "user-history", `${digest}.jsonl`);
}

export async function loadInputHistory(file: string): Promise<string[]> {
	try {
		const contents = await readFile(file, "utf8");
		const entries: string[] = [];
		for (const line of contents.split(/\r?\n/u)) {
			if (!line.trim()) continue;
			try {
				const parsed: unknown = JSON.parse(line);
				if (isHistoryEntry(parsed) && parsed.content.trim()) entries.push(parsed.content);
			} catch {
				// Corrupt history lines should not make the TUI unusable.
			}
		}
		return entries;
	} catch {
		return [];
	}
}

export async function appendInputHistory(file: string, text: string, lastContent?: string): Promise<boolean> {
	const content = text.trim();
	if (!content || content === lastContent) return false;
	await mkdir(path.dirname(file), { recursive: true });
	await appendFile(file, `${JSON.stringify({ content })}\n`, "utf8");
	return true;
}

function isHistoryEntry(value: unknown): value is InputHistoryEntry {
	return typeof value === "object" && value !== null && "content" in value && typeof value.content === "string";
}
