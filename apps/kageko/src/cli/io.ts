export interface CliIO {
	readonly stdout: (chunk: string) => void;
	readonly stderr: (chunk: string) => void;
}

export const processCliIO: CliIO = {
	stdout: (chunk) => {
		process.stdout.write(chunk);
	},
	stderr: (chunk) => {
		process.stderr.write(chunk);
	},
};

export function writeLine(io: CliIO, value = ""): void {
	io.stdout(`${value}\n`);
}
