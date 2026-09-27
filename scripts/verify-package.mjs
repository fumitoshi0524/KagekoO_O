import { spawnSync } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const repoRoot = path.resolve(import.meta.dirname, "..");
const temporaryRoot = await mkdtemp(path.join(tmpdir(), "kageko-package-"));
const npmCli = process.env.npm_execpath;
if (!npmCli) throw new Error("Run this check with npm run verify:package");

function run(command, args, cwd) {
	const result = spawnSync(command, args, {
		cwd,
		encoding: "utf8",
		timeout: 300_000,
		maxBuffer: 16 * 1024 * 1024,
		env: {
			...process.env,
			NODE_PATH: "",
			npm_config_cache: path.join(temporaryRoot, "npm-cache"),
			KAGEKO_HOME: path.join(temporaryRoot, "isolated-home"),
			KAGEKO_DATA_DIR: path.join(temporaryRoot, "isolated-home"),
			CODEX_HOME: path.join(temporaryRoot, "isolated-home", ".codex"),
		},
	});
	if (result.error || result.status !== 0) {
		throw new Error(`${command} ${args.join(" ")} failed:\n${result.stdout ?? ""}\n${result.stderr ?? ""}`, {
			cause: result.error,
		});
	}
	return result.stdout;
}

try {
	const packed = JSON.parse(
		run(
			process.execPath,
			[npmCli, "pack", "--json", "--workspace", "apps/kageko", "--pack-destination", temporaryRoot],
			repoRoot,
		),
	);
	const artifact = packed[0];
	if (!artifact?.filename) throw new Error("npm pack did not produce a tarball");
	const forbidden = artifact.files?.filter((file) => /^(?:benchmarks|\.benchmark-cache)(?:\/|$)/.test(file.path));
	if (forbidden?.length) {
		throw new Error(`npm package includes benchmark files: ${forbidden.map((file) => file.path).join(", ")}`);
	}
	for (const required of [
		"dist/main.mjs",
		"native/win32/prebuilds/win32-x64/win32-console-mode.node",
		"native/win32/prebuilds/win32-arm64/win32-console-mode.node",
		"README.md",
		"LICENSE",
	]) {
		if (!artifact.files?.some((file) => file.path === required)) {
			throw new Error(`npm package is missing ${required}`);
		}
	}

	const installRoot = path.join(temporaryRoot, "isolated-install");
	run(
		process.execPath,
		[
			npmCli,
			"install",
			"--prefix",
			installRoot,
			"--no-audit",
			"--no-fund",
			path.join(temporaryRoot, artifact.filename),
		],
		temporaryRoot,
	);
	const packageRoot = path.join(installRoot, "node_modules", "@kageko", "app");
	const manifest = JSON.parse(await readFile(path.join(packageRoot, "package.json"), "utf8"));
	if (Object.keys(manifest.dependencies ?? {}).some((name) => name.startsWith("@kageko/"))) {
		throw new Error("Standalone CLI package still depends on unpublished @kageko workspace packages");
	}
	const installedCli = path.join(packageRoot, "dist", "main.mjs");
	const help = run(process.execPath, [installedCli, "--help"], temporaryRoot);
	if (!help.includes("kageko")) throw new Error("Installed CLI did not render help");
	const config = JSON.parse(run(process.execPath, [installedCli, "config", "get", "--json"], temporaryRoot));
	if (!config || typeof config !== "object" || !config.model) {
		throw new Error("Installed CLI did not load its configuration independently");
	}
	console.log(`Verified isolated installation of ${manifest.name}@${manifest.version}`);
} finally {
	const resolvedTemp = path.resolve(temporaryRoot);
	const resolvedBase = path.resolve(tmpdir());
	if (resolvedTemp.startsWith(`${resolvedBase}${path.sep}`)) {
		await rm(resolvedTemp, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
	}
}
