import * as fs from "node:fs/promises";
import * as path from "node:path";
import { inflateSync } from "node:zlib";
import { readFileAccess, literalApprovalRule, matchesRuleSubject } from "../accesses.js";
import type { Tool, ToolContext } from "../types.js";

const MAX_MEDIA_BYTES = 100 * 1024 * 1024;

interface ReadMediaArgs {
	path: string;
}

interface Dimensions {
	width: number;
	height: number;
}

interface FileType {
	kind: "image" | "video" | "text" | "unknown";
	mimeType?: string;
	dimensions?: Dimensions | null;
}

/**
 * Read an image file and return it as a base64 data URL part.
 *
 * The tool intentionally exposes only behavior implemented by this package:
 * complete media reads with a fixed safety size limit. Crop and provider-size
 * negotiation are not part of the contract until their implementations exist.
 */
export const readMediaTool: Tool<ReadMediaArgs> = {
	name: "read_media",
	description: "Read an image file for multimodal input. Returns a base64 data URL and metadata.",
	parameters: {
		type: "object",
		properties: {
			path: { type: "string", description: "Path to an image file" },
		},
		required: ["path"],
	},
	resolveExecution({ path: filePath }: ReadMediaArgs) {
		return {
			accesses: readFileAccess(filePath),
			approvalRule: literalApprovalRule("read_media", filePath),
			matchesRule: (ruleArgs) => matchesRuleSubject(ruleArgs, filePath),
			execute: this.execute,
		};
	},
	async execute({ path: filePath }: ReadMediaArgs, { kaos }: ToolContext) {
		const fullPath = await kaos!.resolveReal(filePath);
		const flags = process.platform === "win32" ? "r" : fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW;
		let handle: fs.FileHandle | undefined;
		let data: Buffer;
		try {
			handle = await fs.open(fullPath, flags);
			const stat = await handle.stat();
			if (!stat.isFile()) {
				return { output: "Path is not a regular file.", isError: true };
			}
			if (stat.size > MAX_MEDIA_BYTES) {
				return { output: `Media file exceeds ${MAX_MEDIA_BYTES / 1024 / 1024}MB limit.`, isError: true };
			}
			data = await handle.readFile();
		} catch (err) {
			return { output: `Failed to read media file: ${(err as Error).message}`, isError: true };
		} finally {
			await handle?.close().catch(() => {});
		}

		if (data.length === 0) {
			return { output: "Media file is empty.", isError: true };
		}

		let fileType: FileType;
		try {
			fileType = detectFileType(data, fullPath);
		} catch {
			fileType = { kind: "unknown" };
		}
		if (fileType.kind === "text") {
			return { output: "This is a text file. Use read instead.", isError: true };
		}
		if (fileType.kind === "unknown") {
			return { output: "Unsupported media format.", isError: true };
		}
		if (fileType.kind !== "image") {
			return {
				output: "Only image media is supported. Video remains unregistered until its complete media pipeline exists.",
				isError: true,
			};
		}

		if (fileType.mimeType === "image/png" && !isDecodablePng(data)) {
			return {
				output:
					"The file has a PNG signature but its image data is corrupt or undecodable (bad chunk layout, " +
					"truncated IDAT stream, or invalid scanline filters). Regenerate or repair the file before attaching it.",
				isError: true,
			};
		}

		const base64 = data.toString("base64");
		const tag = "image";
		const systemParts = [
			`Read ${fileType.kind} file.`,
			`Mime type: ${fileType.mimeType}.`,
			`Size: ${data.length} bytes.`,
		];
		if (fileType.dimensions) {
			systemParts.push(`Original dimensions: ${fileType.dimensions.width}x${fileType.dimensions.height} pixels.`);
		}
		systemParts.push(
			"If you generate or edit an image via commands or scripts, read the result back immediately before continuing.",
		);

		const output = [
			{ type: "text", text: `<system>${systemParts.join(" ")}</system>` },
			{ type: "text", text: `<${tag} path="${escapeAttr(filePath)}">` },
			{ type: `${tag}_url`, [`${tag}Url`]: { url: `data:${fileType.mimeType};base64,${base64}` } },
			{ type: "text", text: `</${tag}>` },
		];
		return { output };
	},
};

function escapeAttr(value: string): string {
	return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function detectFileType(data: Buffer, filePath: string): FileType {
	void filePath;
	if (data.length >= 2 && data[0] === 0xff && data[1] === 0xd8) {
		return { kind: "image", mimeType: "image/jpeg", dimensions: parseJpegDimensions(data) };
	}
	if (data.length >= 8 && data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4e && data[3] === 0x47) {
		return { kind: "image", mimeType: "image/png", dimensions: parsePngDimensions(data) };
	}
	if (data.length >= 10 && data[0] === 0x47 && data[1] === 0x49 && data[2] === 0x46) {
		return { kind: "image", mimeType: "image/gif", dimensions: parseGifDimensions(data) };
	}
	if (
		data.length >= 12 &&
		data[0] === 0x52 &&
		data[1] === 0x49 &&
		data[2] === 0x46 &&
		data[3] === 0x46 &&
		data[8] === 0x57 &&
		data[9] === 0x45 &&
		data[10] === 0x42 &&
		data[11] === 0x50
	) {
		return { kind: "image", mimeType: "image/webp", dimensions: parseWebpDimensions(data) };
	}
	if (data.length >= 12 && data[4] === 0x66 && data[5] === 0x74 && data[6] === 0x79 && data[7] === 0x70) {
		return { kind: "video", mimeType: "video/mp4" };
	}
	// Never trust the extension for media classification. The bytes are sent to
	// a model as a data URL, so an extension-only guess can mislabel arbitrary
	// content and bypass the text/unsupported checks above.
	// Heuristic: if mostly printable, treat as text.
	const printable = Array.from(data.slice(0, 256)).filter(
		(b) => (b >= 0x20 && b < 0x7f) || b === 0x0a || b === 0x0d,
	).length;
	if (data.length > 0 && printable / Math.min(data.length, 256) > 0.95) {
		return { kind: "text" };
	}
	return { kind: "unknown" };
}

function parsePngDimensions(data: Buffer): Dimensions | null {
	if (data.length < 24) return null;
	const width = data.readUInt32BE(16);
	const height = data.readUInt32BE(20);
	return { width, height };
}

function parseGifDimensions(data: Buffer): Dimensions | null {
	if (data.length < 10) return null;
	const width = data.readUInt16LE(6);
	const height = data.readUInt16LE(8);
	return { width, height };
}

function parseJpegDimensions(data: Buffer): Dimensions | null {
	let i = 2;
	while (i < data.length) {
		if (data[i] !== 0xff) {
			i++;
			continue;
		}
		const marker = data[i + 1]!;
		if (marker === 0xd9 || marker === 0xd8) {
			i += 2;
			continue;
		}
		const length = data.readUInt16BE(i + 2);
		if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
			const height = data.readUInt16BE(i + 5);
			const width = data.readUInt16BE(i + 7);
			return { width, height };
		}
		i += 2 + length;
	}
	return null;
}

function parseWebpDimensions(data: Buffer): Dimensions | null {
	if (data.length < 30) return null;
	const chunkStart = 12;
	const chunkId = data.toString("ascii", chunkStart, chunkStart + 4);
	if (chunkId === "VP8 " && data.length >= 30) {
		const width = data.readUInt16LE(chunkStart + 14) & 0x3fff;
		const height = data.readUInt16LE(chunkStart + 16) & 0x3fff;
		return { width, height };
	}
	if (chunkId === "VP8L" && data.length >= 25) {
		const bits = data.readUInt32LE(chunkStart + 5);
		const width = (bits & 0x3fff) + 1;
		const height = ((bits >> 14) & 0x3fff) + 1;
		return { width, height };
	}
	return null;
}

const PNG_CHANNELS_BY_COLOR_TYPE: Readonly<Record<number, number>> = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 };

/**
 * Decode-check a PNG before its bytes are sent to a model as a data URL.
 *
 * Magic-byte sniffing alone accepts files whose signature, chunk CRCs, and
 * IEND marker are intact while the actual scanline data is undecodable (for
 * example output of hand-rolled encoders that omit per-scanline filter
 * bytes). Providers reject such images, and a rejected image in conversation
 * history poisons every subsequent request, so the tool must refuse them here.
 */
function isDecodablePng(data: Buffer): boolean {
	try {
		let offset = 8; // skip the 8-byte signature (already verified by detectFileType)
		let ihdr: { width: number; height: number; bitDepth: number; colorType: number; interlace: number } | undefined;
		const idat: Buffer[] = [];
		let sawIend = false;
		while (offset + 12 <= data.length) {
			const length = data.readUInt32BE(offset);
			const type = data.toString("ascii", offset + 4, offset + 8);
			if (length > data.length - offset - 12) return false;
			const body = data.subarray(offset + 8, offset + 8 + length);
			if (type === "IHDR") {
				if (length !== 13 || ihdr) return false;
				ihdr = {
					width: body.readUInt32BE(0),
					height: body.readUInt32BE(4),
					bitDepth: body[8]!,
					colorType: body[9]!,
					interlace: body[12]!,
				};
			} else if (type === "IDAT") {
				if (!ihdr) return false;
				idat.push(body);
			} else if (type === "IEND") {
				sawIend = true;
				break;
			}
			offset += 12 + length;
		}
		if (!sawIend || !ihdr || idat.length === 0) return false;
		const channels = PNG_CHANNELS_BY_COLOR_TYPE[ihdr.colorType];
		if (!channels || ihdr.width < 1 || ihdr.height < 1) return false;
		const rowBits = (width: number) => width * channels * ihdr!.bitDepth;
		const scanlines: Array<{ offset: number; length: number }> = [];
		let expected = 0;
		const addPass = (passWidth: number, passHeight: number) => {
			if (passWidth < 1 || passHeight < 1) return;
			const rowBytes = Math.ceil(rowBits(passWidth) / 8);
			for (let row = 0; row < passHeight; row += 1) {
				scanlines.push({ offset: expected, length: rowBytes });
				expected += 1 + rowBytes;
			}
		};
		if (ihdr.interlace === 0) {
			addPass(ihdr.width, ihdr.height);
		} else if (ihdr.interlace === 1) {
			// Adam7 passes: [x0, y0, xStep, yStep].
			for (const [x0, y0, dx, dy] of [
				[0, 0, 8, 8],
				[4, 0, 8, 8],
				[0, 4, 4, 8],
				[2, 0, 4, 4],
				[0, 2, 2, 4],
				[1, 0, 2, 2],
				[0, 1, 1, 2],
			] as const) {
				addPass(Math.ceil((ihdr.width - x0) / dx), Math.ceil((ihdr.height - y0) / dy));
			}
		} else {
			return false;
		}
		const raw = inflateSync(Buffer.concat(idat));
		if (raw.length !== expected) return false;
		for (const scanline of scanlines) {
			if (raw[scanline.offset]! > 4) return false;
		}
		return true;
	} catch {
		return false;
	}
}
