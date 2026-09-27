/** User-correctable CLI input failure; mapped to exit code 2 by the host. */
export class CliUsageError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "CliUsageError";
	}
}
