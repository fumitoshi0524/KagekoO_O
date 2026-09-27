import { resolve } from "node:path";

import { defineConfig } from "vitest/config";

import { workspaceSrcAliases } from "../../test/helpers/workspace-aliases.js";

const appRoot = import.meta.dirname;
const repoRoot = resolve(appRoot, "../..");
const sourceRoot = resolve(appRoot, "src");

export default defineConfig({
	root: appRoot,
	resolve: {
		// Project configs do not inherit the root resolve, so this project
		// installs the shared @kageko/* → src aliases itself (guarded by
		// test/src-alias.test.ts). App-specific aliases follow; "#test-helpers"
		// is regex-matched inside workspaceSrcAliases before the "#" fallback.
		alias: [
			...workspaceSrcAliases(repoRoot),
			{ find: "@", replacement: sourceRoot },
			{ find: /^#\/(.+)$/, replacement: `${sourceRoot}/$1` },
		],
	},
	test: {
		name: "kageko-cli",
		testTimeout: 15_000,
		env: {
			KAGEKO_LOG_LEVEL: "off",
		},
		// Same hermetic env scrub as the root config — this file must be
		// self-contained because project configs do not inherit setupFiles.
		setupFiles: [resolve(appRoot, "../../test/helpers/hermetic.ts")],
		include: ["test/**/*.test.ts", "test/**/*.test.tsx"],
	},
});
