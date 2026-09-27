import { defineConfig } from "tsdown";

export default defineConfig({
	entry: ["./src/index.ts"],
	format: "esm",
	outDir: "dist",
	codeSplitting: false,
	// Keep declaration output inside dist. The TypeScript generator follows root
	// source aliases across packages and is also incompatible with the currently
	// hoisted experimental TypeScript build; Oxc emits the public declarations
	// from this package boundary without scattering dependency artifacts.
	dts: { generator: "oxc" },
});
