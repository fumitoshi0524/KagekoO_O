import { describe, expect, it, vi } from "vitest";
import { replaceAtomically, retryTransientFileOperation } from "./atomic-replace.js";

describe("replaceAtomically", () => {
	it("retries transient Windows sharing errors before publishing", async () => {
		const transient = Object.assign(new Error("temporarily locked"), { code: "EPERM" });
		const renameFile = vi
			.fn()
			.mockRejectedValueOnce(transient)
			.mockRejectedValueOnce(transient)
			.mockResolvedValueOnce(undefined);
		const sleep = vi.fn().mockResolvedValue(undefined);

		await replaceAtomically("trust.tmp", "trust.json", { renameFile, sleep });

		expect(renameFile).toHaveBeenCalledTimes(3);
		expect(sleep).toHaveBeenNthCalledWith(1, 25);
		expect(sleep).toHaveBeenNthCalledWith(2, 50);
	});

	it("does not retry non-transient filesystem errors", async () => {
		const permanent = Object.assign(new Error("missing temporary file"), { code: "ENOENT" });
		const renameFile = vi.fn().mockRejectedValue(permanent);
		const sleep = vi.fn();

		await expect(replaceAtomically("trust.tmp", "trust.json", { renameFile, sleep })).rejects.toBe(permanent);
		expect(renameFile).toHaveBeenCalledOnce();
		expect(sleep).not.toHaveBeenCalled();
	});

	it("retries transient temporary-file creation failures before writing", async () => {
		const transient = Object.assign(new Error("scanner held the new file"), { code: "EPERM" });
		const write = vi.fn().mockRejectedValueOnce(transient).mockResolvedValueOnce(undefined);
		const sleep = vi.fn().mockResolvedValue(undefined);

		await retryTransientFileOperation(write, { sleep });

		expect(write).toHaveBeenCalledTimes(2);
		expect(sleep).toHaveBeenCalledWith(25);
	});

	it("bounds repeated transient failures", async () => {
		const transient = Object.assign(new Error("still locked"), { code: "EBUSY" });
		const write = vi.fn().mockRejectedValue(transient);
		const sleep = vi.fn().mockResolvedValue(undefined);

		await expect(retryTransientFileOperation(write, { attempts: 3, sleep })).rejects.toBe(transient);
		expect(write).toHaveBeenCalledTimes(3);
		expect(sleep).toHaveBeenNthCalledWith(1, 25);
		expect(sleep).toHaveBeenNthCalledWith(2, 50);
	});
});
