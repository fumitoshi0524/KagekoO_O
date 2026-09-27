/**
 * Semantic color palette, terminal capability detection, and tone mapping.
 * Dark/light token values follow kimi-code's palettes, with Kageko's violet
 * brand hue swapped into `primary` and blue into `shellMode`.
 */

export type Tone =
	| "default"
	| "strong"
	| "muted"
	| "faint"
	| "primary"
	| "accent"
	| "success"
	| "warning"
	| "danger"
	| "user"
	| "assistant"
	| "surface"
	| "code"
	| "shell"
	| "diffAdded"
	| "diffRemoved"
	| "diffAddedStrong"
	| "diffRemovedStrong"
	| "diffGutter"
	| "diffMeta";

export interface ColorPalette {
	readonly primary: string;
	readonly accent: string;
	readonly text: string;
	readonly textStrong: string;
	readonly textDim: string;
	readonly textMuted: string;
	readonly border: string;
	readonly borderFocus: string;
	readonly success: string;
	readonly warning: string;
	readonly error: string;
	readonly diffAdded: string;
	readonly diffRemoved: string;
	readonly diffAddedStrong: string;
	readonly diffRemovedStrong: string;
	readonly diffGutter: string;
	readonly diffMeta: string;
	readonly roleUser: string;
	readonly shellMode: string;
}

export const darkColors: ColorPalette = {
	primary: "#A78BFA",
	accent: "#5BC0BE",
	text: "#E0E0E0",
	textStrong: "#F5F5F5",
	textDim: "#888888",
	textMuted: "#6B6B6B",
	border: "#5A5A5A",
	borderFocus: "#E8A838",
	success: "#4EC87E",
	warning: "#E8A838",
	error: "#E85454",
	diffAdded: "#4EC87E",
	diffRemoved: "#E85454",
	diffAddedStrong: "#7AD99B",
	diffRemovedStrong: "#F08585",
	diffGutter: "#6B6B6B",
	diffMeta: "#888888",
	roleUser: "#FFCB6B",
	shellMode: "#4FA8FF",
};

export const lightColors: ColorPalette = {
	primary: "#6D28D9",
	accent: "#00838F",
	text: "#1A1A1A",
	textStrong: "#1A1A1A",
	textDim: "#454545",
	textMuted: "#5F5F5F",
	border: "#737373",
	borderFocus: "#92660A",
	success: "#0E7A38",
	warning: "#92660A",
	error: "#B91C1C",
	diffAdded: "#0E7A38",
	diffRemoved: "#B91C1C",
	diffAddedStrong: "#0E7A38",
	diffRemovedStrong: "#B91C1C",
	diffGutter: "#737373",
	diffMeta: "#5F5F5F",
	roleUser: "#9A4A00",
	shellMode: "#1565C0",
};

/** Selection/highlight fills behind text; deliberately not semantic tokens. */
export type ToneBackgrounds = Readonly<Record<Tone, string>>;

export const darkBackgrounds: ToneBackgrounds = {
	default: "#18181B",
	strong: "#18181B",
	muted: "#27272A",
	faint: "#27272A",
	primary: "#312E81",
	accent: "#312E81",
	success: "#134E4A",
	warning: "#5C3D12",
	danger: "#5C1D2D",
	user: "#312E81",
	assistant: "#27272A",
	surface: "#27272A",
	code: "#27272A",
	shell: "#312E81",
	diffAdded: "#27272A",
	diffRemoved: "#27272A",
	diffAddedStrong: "#27272A",
	diffRemovedStrong: "#27272A",
	diffGutter: "#27272A",
	diffMeta: "#27272A",
};

export const lightBackgrounds: ToneBackgrounds = {
	default: "#FFFFFF",
	strong: "#FFFFFF",
	muted: "#F3F3F3",
	faint: "#F3F3F3",
	primary: "#E9E3FB",
	accent: "#E9E3FB",
	success: "#E3F4EA",
	warning: "#F9EFDB",
	danger: "#F9E3E3",
	user: "#E9E3FB",
	assistant: "#F3F3F3",
	surface: "#F3F3F3",
	code: "#F3F3F3",
	shell: "#E9E3FB",
	diffAdded: "#F3F3F3",
	diffRemoved: "#F3F3F3",
	diffAddedStrong: "#F3F3F3",
	diffRemovedStrong: "#F3F3F3",
	diffGutter: "#F3F3F3",
	diffMeta: "#F3F3F3",
};

/** Existing view tone names resolve onto palette tokens at paint time. */
export const TONE_TOKEN: Readonly<Record<Tone, keyof ColorPalette>> = {
	default: "text",
	strong: "textStrong",
	muted: "textDim",
	faint: "textMuted",
	primary: "primary",
	accent: "accent",
	success: "success",
	warning: "warning",
	danger: "error",
	user: "roleUser",
	assistant: "text",
	surface: "border",
	code: "primary",
	shell: "shellMode",
	diffAdded: "diffAdded",
	diffRemoved: "diffRemoved",
	diffAddedStrong: "diffAddedStrong",
	diffRemovedStrong: "diffRemovedStrong",
	diffGutter: "diffGutter",
	diffMeta: "diffMeta",
};

export type ColorMode = "truecolor" | "ansi256" | "ansi16" | "none";

export interface ResolvedTheme {
	readonly name: "dark" | "light";
	readonly palette: ColorPalette;
	readonly backgrounds: ToneBackgrounds;
	/** Terminal-default background when undefined; set only by themes that need a custom canvas. */
	readonly canvas?: string;
	readonly mode: ColorMode;
}

export function resolveTheme(env: NodeJS.ProcessEnv = process.env): ResolvedTheme {
	const forced = env["KAGEKO_THEME"] === "light" || env["KAGEKO_THEME"] === "dark" ? env["KAGEKO_THEME"] : undefined;
	const name = forced ?? (colorFgBgLight(env["COLORFGBG"]) ? "light" : "dark");
	return {
		name,
		palette: name === "dark" ? darkColors : lightColors,
		backgrounds: name === "dark" ? darkBackgrounds : lightBackgrounds,
		mode: colorMode(env),
	};
}

function colorFgBgLight(value: string | undefined): boolean {
	const background = Number(value?.split(";").at(-1));
	return background === 7 || background === 15;
}

function colorMode(env: NodeJS.ProcessEnv): ColorMode {
	if (env["NO_COLOR"] !== undefined) return "none";
	const colorterm = (env["COLORTERM"] ?? "").toLowerCase();
	if (colorterm.includes("truecolor") || colorterm.includes("24bit")) return "truecolor";
	if ((env["TERM"] ?? "").toLowerCase() === "dumb") return "ansi16";
	return "ansi256";
}

export function hexToRgb(hex: string): { readonly r: number; readonly g: number; readonly b: number } {
	const value = Number.parseInt(hex.slice(1), 16);
	return { r: (value >> 16) & 0xff, g: (value >> 8) & 0xff, b: value & 0xff };
}

/** Nearest xterm-256 index within the 6x6x6 color cube plus grayscale ramp. */
export function xterm256Index(hex: string): number {
	const { r, g, b } = hexToRgb(hex);
	let best = 16;
	let bestDistance = Number.POSITIVE_INFINITY;
	for (let index = 16; index < 256; index += 1) {
		const candidate = xterm256Rgb(index);
		const distance = (candidate.r - r) ** 2 + (candidate.g - g) ** 2 + (candidate.b - b) ** 2;
		if (distance < bestDistance) {
			best = index;
			bestDistance = distance;
		}
	}
	return best;
}

function xterm256Rgb(index: number): { readonly r: number; readonly g: number; readonly b: number } {
	if (index < 232) {
		const offset = index - 16;
		const level = (value: number) => (value === 0 ? 0 : 55 + value * 40);
		return { r: level(Math.floor(offset / 36)), g: level(Math.floor((offset % 36) / 6)), b: level(offset % 6) };
	}
	const gray = 8 + (index - 232) * 10;
	return { r: gray, g: gray, b: gray };
}

const ANSI16: readonly (readonly [number, number, number])[] = [
	[0, 0, 0],
	[205, 0, 0],
	[0, 205, 0],
	[205, 205, 0],
	[0, 0, 238],
	[205, 0, 205],
	[0, 205, 205],
	[229, 229, 229],
	[127, 127, 127],
	[255, 0, 0],
	[0, 255, 0],
	[255, 255, 0],
	[92, 92, 255],
	[255, 0, 255],
	[0, 255, 255],
	[255, 255, 255],
];

/** Nearest of the sixteen basic ANSI colors (0-7 normal, 8-15 bright). */
export function ansi16Index(hex: string): number {
	const { r, g, b } = hexToRgb(hex);
	let best = 0;
	let bestDistance = Number.POSITIVE_INFINITY;
	for (let index = 0; index < ANSI16.length; index += 1) {
		const [cr, cg, cb] = ANSI16[index]!;
		const distance = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2;
		if (distance < bestDistance) {
			best = index;
			bestDistance = distance;
		}
	}
	return best;
}

export function foregroundCode(theme: ResolvedTheme, tone: Tone): string {
	return colorCode(theme.mode, theme.palette[TONE_TOKEN[tone]], 38);
}

export function backgroundCode(theme: ResolvedTheme, tone: Tone): string {
	return colorCode(theme.mode, theme.backgrounds[tone], 48);
}

export function canvasCode(theme: ResolvedTheme): string {
	return theme.canvas === undefined ? "" : colorCode(theme.mode, theme.canvas, 48);
}

function colorCode(mode: ColorMode, hex: string, base: 38 | 48): string {
	if (mode === "none") return "";
	if (mode === "truecolor") {
		const { r, g, b } = hexToRgb(hex);
		return `\x1b[${base};2;${r};${g};${b}m`;
	}
	if (mode === "ansi256") return `\x1b[${base};5;${xterm256Index(hex)}m`;
	const index = ansi16Index(hex);
	return `\x1b[${index < 8 ? base - 8 + index : base + 44 + index}m`;
}
