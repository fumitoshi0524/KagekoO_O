import js from "@eslint/js";
import globals from "globals";

export default [
	{
		ignores: [
			"**/node_modules/**",
			"**/dist/**",
			"**/build/**",
			"**/coverage/**",
			"**/.kageko/**",
			"**/.venv/**",
			"**/.benchmark-cache/**",
			"**/scripts/**",
		],
	},
	{
		files: ["**/*.mjs", "**/*.cjs", "**/*.js"],
		languageOptions: {
			ecmaVersion: "latest",
			sourceType: "module",
			globals: {
				...globals.node,
				...globals.es2024,
			},
		},
		linterOptions: {
			reportUnusedDisableDirectives: true,
		},
		rules: {
			...js.configs.recommended.rules,
			"no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
			"no-console": "off",
			"no-undef": "error",
		},
	},
	{
		files: ["**/tests/**/*.mjs", "**/*.test.mjs"],
		languageOptions: {
			globals: {
				...globals.node,
			},
		},
	},
];
