import { spawnSync } from "node:child_process";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const result = spawnSync(
	"git",
	[
		"-c",
		`safe.directory=${repoRoot.replaceAll("\\", "/")}`,
		"ls-files",
		"-z",
		"--",
		"benchmarks/",
		".benchmark-cache/",
	],
	{ cwd: repoRoot, encoding: "utf8" },
);

if (result.error || result.status !== 0) {
	throw new Error(`Could not inspect tracked release files: ${result.stderr ?? result.error}`);
}

const tracked = result.stdout.split("\0").filter(Boolean);
if (tracked.length > 0) {
	throw new Error(`Benchmark files are still tracked and would ship in the public source tree:\n${tracked.join("\n")}`);
}

console.log("Public source tree excludes benchmark files.");
