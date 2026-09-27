import * as fs from "node:fs/promises";
import * as crypto from "node:crypto";
import * as path from "node:path";

const MAX_STORE_FILE_BYTES = 10 * 1024 * 1024;

/**
 * Whole-map view over a JSON-object file that holds secrets.
 *
 * Both the provider credential store and the MCP token store share these
 * mechanics: private-parent and regular-file assertions, a size cap, and
 * atomic tmp-file replacement written with mode 0600.
 */
export interface JsonFileStore {
	readAll<T = Record<string, unknown>>(): Promise<Record<string, T>>;
	writeAll<T>(data: Record<string, T>): Promise<void>;
}

export function createJsonFileStore(filePath: string): JsonFileStore {
	async function readAll<T>(): Promise<Record<string, T>> {
		await assertPrivateParent(filePath);
		let stat;
		try {
			stat = await fs.lstat(filePath);
		} catch (err) {
			if ((err as NodeJS.ErrnoException).code === "ENOENT") return {};
			throw err;
		}
		assertPrivateRegularFile(filePath, stat);
		if (stat.size > MAX_STORE_FILE_BYTES) {
			throw new Error(`JSON store ${filePath} is ${stat.size} bytes, exceeding the ${MAX_STORE_FILE_BYTES} byte limit`);
		}
		const text = await fs.readFile(filePath, "utf8");
		let data: unknown;
		try {
			data = JSON.parse(text);
		} catch (err) {
			if (err instanceof SyntaxError) {
				throw new Error(`JSON store ${filePath} contains invalid JSON`);
			}
			throw err;
		}
		return data && typeof data === "object" && !Array.isArray(data) ? (data as Record<string, T>) : {};
	}

	async function writeAll<T>(data: Record<string, T>): Promise<void> {
		const parent = path.dirname(filePath);
		await fs.mkdir(parent, { recursive: true, mode: 0o700 });
		await assertPrivateParent(filePath);
		try {
			assertPrivateRegularFile(filePath, await fs.lstat(filePath));
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
		}
		const serialized = JSON.stringify(data, null, "\t") + "\n";
		if (Buffer.byteLength(serialized) > MAX_STORE_FILE_BYTES) {
			throw new Error(`JSON store exceeds the ${MAX_STORE_FILE_BYTES} byte limit`);
		}
		const tmp = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
		try {
			const handle = await fs.open(tmp, "wx", 0o600);
			try {
				await handle.writeFile(serialized, "utf8");
				await handle.sync();
			} finally {
				await handle.close();
			}
			await fs.rename(tmp, filePath);
		} finally {
			await fs.rm(tmp, { force: true }).catch(() => undefined);
		}
	}

	return { readAll, writeAll };
}

async function assertPrivateParent(target: string): Promise<void> {
	const resolved = path.resolve(target);
	const privateParent = path.dirname(resolved);
	const root = path.parse(resolved).root;
	const relative = path.relative(root, privateParent);
	let current = root;
	for (const part of relative.split(path.sep).filter(Boolean)) {
		current = path.join(current, part);
		let stat;
		try {
			stat = await fs.lstat(current);
		} catch (error) {
			if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
			throw error;
		}
		if (stat.isSymbolicLink()) {
			// macOS uses root-owned /var and /tmp links into /private. A link
			// owned by root at the filesystem root cannot be replaced by the
			// current user; the credential directory itself must still be real.
			if (
				process.platform === "darwin" &&
				current !== privateParent &&
				path.dirname(current) === root &&
				stat.uid === 0 &&
				(await fs.stat(current)).isDirectory()
			) {
				continue;
			}
			throw new Error(`JSON store parent must be a real directory: ${current}`);
		}
		if (!stat.isDirectory()) {
			throw new Error(`JSON store parent must be a real directory: ${current}`);
		}
		// Public ancestors such as /home or /tmp are normal. The directory
		// containing the secret itself must be private.
		if (current === privateParent && process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
			throw new Error(`JSON store parent permissions are too broad: ${current}`);
		}
	}
}

function assertPrivateRegularFile(target: string, stat: import("node:fs").Stats): void {
	if (!stat.isFile() || stat.isSymbolicLink()) {
		throw new Error(`JSON store must be a real regular file: ${target}`);
	}
	if (process.platform !== "win32" && (stat.mode & 0o077) !== 0) {
		throw new Error(`JSON store permissions are too broad: ${target}`);
	}
}
