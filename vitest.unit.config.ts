import { resolve } from "node:path";
import { defineConfig } from "vitest/config";
import { workspaceSrcAliases } from "./test/helpers/workspace-aliases.js";

export default defineConfig({
	resolve: { alias: workspaceSrcAliases(import.meta.dirname) },
	test: {
		name: "unit",
		include: ["packages/**/*.test.ts", "apps/**/*.test.ts"],
		setupFiles: [resolve(import.meta.dirname, "test/helpers/hermetic.ts")],
		testTimeout: 30_000,
	},
});
