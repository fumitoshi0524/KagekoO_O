import * as os from "node:os";
import * as path from "node:path";

/** Resolve Kageko's device-private home directory at the point of use. */
export function kagekoHomeDir(): string {
	const configured =
		process.env["KAGEKO_HOME"]?.trim() ||
		(process.platform === "win32" ? process.env["USERPROFILE"]?.trim() : process.env["HOME"]?.trim());
	return configured ? path.resolve(configured) : os.homedir();
}
