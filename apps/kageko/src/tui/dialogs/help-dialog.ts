import type { RenderLine } from "@kageko/tui-kit";
import { slashCommands } from "../commands/registry.js";

export const helpDialogLines = (): readonly RenderLine[] => {
	const categories = ["session", "modes", "memory", "capabilities", "config", "info"] as const;
	const lines: RenderLine[] = [];
	for (const category of categories) {
		const commands = slashCommands.filter((command) => command.category === category && !command.hidden);
		if (!commands.length) continue;
		lines.push({ text: category[0]!.toUpperCase() + category.slice(1), tone: "primary", bold: true });
		for (const command of commands) {
			lines.push({
				text: `  /${command.name}${command.argumentHint ? ` ${command.argumentHint}` : ""} — ${command.description}`,
				tone: "default",
			});
		}
	}
	lines.push({ text: "Keyboard shortcuts", tone: "primary", bold: true });
	lines.push({ text: "  Enter send · Alt+Enter newline · Up/Down history", tone: "faint" });
	lines.push({ text: "  Ctrl+G editor · Ctrl+O expand output · Ctrl+T activity", tone: "faint" });
	lines.push({ text: "  Esc interrupt/back · Ctrl+C cancel/clear · Ctrl+D exit", tone: "faint" });
	return lines;
};
