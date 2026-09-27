import { defineConfig } from "tsdown";

export default defineConfig({
	entry: ["./src/index.ts"],
	format: "esm",
	outDir: "dist",
	codeSplitting: false,
	dts: { generator: "oxc" },
});
