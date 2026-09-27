import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { deflateSync } from "node:zlib";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { readMediaTool } from "./read-media.js";
import type { ToolContext } from "../types.js";

let workDir: string;

beforeAll(async () => {
	workDir = await fs.mkdtemp(path.join(os.tmpdir(), "read-media-test-"));
});

afterAll(async () => {
	await fs.rm(workDir, { recursive: true, force: true });
});

function fakeContext(): ToolContext {
	return {
		kaos: {
			resolveReal: async (filePath: string) => filePath,
		},
	} as unknown as ToolContext;
}

function pngChunk(type: string, body: Buffer): Buffer {
	const chunk = Buffer.alloc(12 + body.length);
	chunk.writeUInt32BE(body.length, 0);
	chunk.write(type, 4, "ascii");
	body.copy(chunk, 8);
	// The decoder check does not validate CRCs; zero-fill keeps the fixture small.
	chunk.writeUInt32BE(0, 8 + body.length);
	return chunk;
}

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function ihdr(width: number, height: number): Buffer {
	const body = Buffer.alloc(13);
	body.writeUInt32BE(width, 0);
	body.writeUInt32BE(height, 4);
	body[8] = 8; // bit depth
	body[9] = 2; // color type RGB
	body[12] = 0; // no interlace
	return pngChunk("IHDR", body);
}

/** A well-formed RGB PNG: every scanline carries a valid filter byte (0). */
function buildValidPng(width: number, height: number): Buffer {
	const raw = Buffer.alloc(height * (1 + width * 3));
	return Buffer.concat([
		PNG_SIGNATURE,
		ihdr(width, height),
		pngChunk("IDAT", deflateSync(raw)),
		pngChunk("IEND", Buffer.alloc(0)),
	]);
}

/**
 * The benchmark incident shape: signature, IHDR, IDAT, and IEND are all
 * intact and the inflated length matches, but the scanlines were written by a
 * hand-rolled encoder that omitted per-scanline filter bytes — the leading
 * byte of each row is pixel data (0xf6), so no strict decoder accepts it.
 */
function buildFilterlessPng(width: number, height: number): Buffer {
	const raw = Buffer.alloc(height * (1 + width * 3), 0xf6);
	return Buffer.concat([
		PNG_SIGNATURE,
		ihdr(width, height),
		pngChunk("IDAT", deflateSync(raw)),
		pngChunk("IEND", Buffer.alloc(0)),
	]);
}

describe("readMediaTool PNG validation", () => {
	it("attaches a well-formed PNG as a data URL", async () => {
		const file = path.join(workDir, "valid.png");
		await fs.writeFile(file, buildValidPng(4, 3));

		const result = await readMediaTool.execute!({ path: file }, fakeContext());

		expect(result.isError).toBeFalsy();
		const output = result.output as Array<Record<string, unknown>>;
		const image = output.find((part) => part["type"] === "image_url");
		expect(image).toBeDefined();
		const url = (image?.["imageUrl"] as { url: string }).url;
		expect(url.startsWith("data:image/png;base64,")).toBe(true);
	});

	it("rejects a PNG whose scanlines lack filter bytes instead of poisoning the conversation", async () => {
		const file = path.join(workDir, "filterless.png");
		await fs.writeFile(file, buildFilterlessPng(4, 3));

		const result = await readMediaTool.execute!({ path: file }, fakeContext());

		expect(result.isError).toBe(true);
		expect(String(result.output)).toContain("corrupt or undecodable");
	});

	it("rejects a PNG with a truncated IDAT stream", async () => {
		const valid = buildValidPng(4, 3);
		// Truncate inside the IDAT payload but keep the signature intact.
		const file = path.join(workDir, "truncated.png");
		await fs.writeFile(file, valid.subarray(0, valid.length - 20));

		const result = await readMediaTool.execute!({ path: file }, fakeContext());

		expect(result.isError).toBe(true);
		expect(String(result.output)).toContain("corrupt or undecodable");
	});
});
