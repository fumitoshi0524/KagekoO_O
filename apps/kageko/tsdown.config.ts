import { defineConfig } from "tsdown";

export default defineConfig({
	entry: ["./src/main.ts"],
	format: "esm",
	outDir: "dist",
	codeSplitting: false,
	// No declarations: the CLI is an executable (bin target) and nothing
	// consumes its types. With dts
	// enabled, the bundled @kageko/* sources force a tsc declaration emit
	// without outDir, which scatters .d.ts files into packages/*/src.
	dts: false,
	deps: {
		onlyBundle: false,
		alwaysBundle: [/^@kageko/],
		neverBundle: [
			/^@anthropic-ai\/sdk$/,
			/^@mistralai\/mistralai$/,
			/^tree-sitter$/,
			/^tree-sitter-bash$/,
			/^node-gyp-build$/,
		],
	},
});
