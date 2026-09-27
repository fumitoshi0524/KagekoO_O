// Mirrors kimi-code's apps/kimi-code/scripts/copy-native-assets.mjs, adapted
// for Kageko: copies tui-kit's win32 VT input helper next to this app
// (apps/kageko/native) so the bundled CLI — a single dist/main.mjs with
// @kageko/* inlined — still resolves the native helper via the loader's first
// candidate, <dist>/../native. Without it, Shift+Tab arrives as plain Tab.
import { cp, mkdir, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(appRoot, "../..");
const source = resolve(repoRoot, "packages/tui-kit/native");
const target = resolve(appRoot, "native");

// tui-kit ships the VT key input helper only for win32.
const PLATFORMS = ["win32"];

async function assertPrebuilds(platform) {
	const dir = resolve(source, platform, "prebuilds");
	try {
		const info = await stat(dir);
		if (!info.isDirectory()) {
			throw new Error("not a directory");
		}
	} catch {
		throw new Error(`tui-kit native prebuilds were not found at ${dir}. Build or restore packages/tui-kit first.`);
	}
	return dir;
}

await mkdir(target, { recursive: true });

for (const platform of PLATFORMS) {
	const srcPrebuilds = await assertPrebuilds(platform);
	const dstPrebuilds = resolve(target, platform, "prebuilds");
	// Do not unlink an existing native module: Windows keeps a loaded `.node`
	// file locked, and a running TUI/test process should not make packaging
	// fail. The source tree is immutable during a build, so keeping identical
	// existing files is safe; missing files are still copied into the target.
	await cp(srcPrebuilds, dstPrebuilds, { recursive: true, force: false, errorOnExist: false });
}

console.log(`Copied tui-kit native prebuilds to ${target}`);
