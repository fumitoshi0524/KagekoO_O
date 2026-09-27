export interface CredentialReader {
	read(providerId: string): Promise<unknown>;
}
export interface CredentialWriter {
	write(providerId: string, credential: unknown): Promise<void>;
	remove?(providerId: string): Promise<void>;
}

export class AuthService {
	constructor(
		readonly reader: CredentialReader,
		readonly writer: CredentialWriter,
	) {}
	async get(providerId: string): Promise<unknown> {
		return this.reader.read(providerId);
	}
	async set(providerId: string, credential: unknown): Promise<void> {
		await this.writer.write(providerId, credential);
	}
	async remove(providerId: string): Promise<void> {
		if (!this.writer.remove) throw new Error("Credential storage does not support removal");
		await this.writer.remove(providerId);
	}
}
