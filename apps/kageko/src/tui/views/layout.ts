export interface FrameAllocation {
	readonly headerRows: number;
	readonly contextRows: number;
	readonly bodyRows: number;
	readonly footerRows: number;
	readonly composerRows: number;
}
/** Protects current work/composer first when space is constrained. */
export function allocateLayout(
	columns: number,
	rows: number,
	composerRows: number,
	hasContext: boolean,
): FrameAllocation {
	const composer = Math.min(Math.max(2, composerRows), Math.max(1, rows - 2));
	const header = rows >= 10 ? (columns >= 40 ? 6 : 3) : 1;
	const footer = rows >= 5 ? (columns >= 60 ? 2 : 1) : 1;
	const context = hasContext && columns >= 52 && rows >= 9 ? 2 : 0;
	return {
		headerRows: header,
		contextRows: context,
		footerRows: footer,
		composerRows: composer,
		bodyRows: Math.max(0, rows - header - context - footer - composer),
	};
}
