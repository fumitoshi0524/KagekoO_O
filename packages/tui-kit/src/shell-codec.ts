import { spawnSync } from "node:child_process";
import path from "node:path";
import * as iconv from "iconv-lite";

const UTF8 = "utf8";

/** Maps the numeric code page reported by cmd.exe to an iconv-lite encoding. */
export function windowsCodePageEncoding(codePage: number | undefined): string {
	if (codePage === 65001) return UTF8;
	if (codePage === 1200) return "utf16le";
	if (codePage === 1201) return "utf16be";
	if (codePage === 54936) return "gb18030";
	const candidate = codePage === undefined ? UTF8 : `cp${String(codePage)}`;
	return iconv.encodingExists(candidate) ? candidate : UTF8;
}

export function parseWindowsCodePage(output: Buffer | string | undefined): number | undefined {
	if (output === undefined) return undefined;
	// chcp's label is localized, but the trailing code-page number is ASCII on
	// every Windows locale. latin1 preserves those bytes without guessing the
	// very encoding this probe is trying to discover.
	const matches = (typeof output === "string" ? output : output.toString("latin1")).match(/\d{3,6}/g);
	const value = Number(matches?.at(-1));
	return Number.isSafeInteger(value) && value > 0 ? value : undefined;
}

export function resolveShellEncoding(
	platform: NodeJS.Platform,
	executable: string,
	environment: NodeJS.ProcessEnv = process.env,
): string {
	const configured = environment["KAGEKO_SHELL_ENCODING"];
	if (configured && iconv.encodingExists(configured)) return configured;
	if (platform !== "win32" || !/^cmd(?:\.exe)?$/i.test(path.basename(executable))) return UTF8;
	try {
		const probe = spawnSync(executable, ["/d", "/c", "chcp"], {
			encoding: "buffer",
			stdio: ["ignore", "pipe", "ignore"],
			windowsHide: true,
			timeout: 2_000,
		});
		return windowsCodePageEncoding(parseWindowsCodePage(probe.stdout));
	} catch {
		return UTF8;
	}
}

/** Incremental decoder/encoder for redirected shells; never splits a multibyte character. */
export class ShellCodec {
	private readonly decoder: iconv.DecoderStream;
	readonly encoding: iconv.Encoding;
	constructor(encoding: string) {
		this.encoding = iconv.encodingExists(encoding) ? encoding : UTF8;
		this.decoder = iconv.getDecoder(this.encoding);
	}
	decode(value: Buffer | string): string {
		return typeof value === "string" ? value : this.decoder.write(value);
	}
	end(): string {
		return this.decoder.end() ?? "";
	}
	encode(value: string): Buffer {
		return iconv.encode(value, this.encoding);
	}
}
