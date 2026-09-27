import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

export function resolveEditorCommand(configured?: string | null): string | undefined {
	return [configured, process.env["VISUAL"], process.env["EDITOR"]]
		.find((candidate): candidate is string => typeof candidate === "string" && candidate.trim().length > 0)
		?.trim();
}

export async function editDraft(initial: string, command: string): Promise<string | undefined> {
	const directory = await mkdtemp(path.join(tmpdir(), "kageko-edit-"));
	const file = path.join(directory, "prompt.md");
	await writeFile(file, initial, "utf8");
	try {
		const quoted =
			process.platform === "win32" ? `"${file.replaceAll('"', '\\"')}"` : `'${file.replaceAll("'", "'\\''")}'`;
		const code = await new Promise<number>((resolve, reject) => {
			const child = spawn(`${command} ${quoted}`, { shell: true, stdio: "inherit" });
			child.once("error", reject);
			child.once("exit", (value) => resolve(value ?? 1));
		});
		return code === 0 ? await readFile(file, "utf8") : undefined;
	} finally {
		await rm(directory, { recursive: true, force: true }).catch(() => {});
	}
}
