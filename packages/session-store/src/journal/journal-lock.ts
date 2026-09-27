export class JournalLock {
	private static readonly locks = new Map<string, Promise<void>>();
	async run<T>(key: string, operation: () => Promise<T>): Promise<T> {
		const prior = JournalLock.locks.get(key) ?? Promise.resolve();
		let release!: () => void;
		const current = new Promise<void>((resolve) => {
			release = resolve;
		});
		JournalLock.locks.set(key, current);
		await prior;
		try {
			return await operation();
		} finally {
			release();
			if (JournalLock.locks.get(key) === current) JournalLock.locks.delete(key);
		}
	}
}
