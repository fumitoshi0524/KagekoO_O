import Parser from "tree-sitter";
import Bash from "tree-sitter-bash";
import type { ParsedCommand } from "./types.js";

const parser = new Parser();
parser.setLanguage(Bash as unknown as Parser.Language);

export function parseBash(source: string): { commands: ParsedCommand[]; hasErrors: boolean } {
	const tree = parser.parse(source);
	const commands: ParsedCommand[] = [];
	walk(tree.rootNode, (node) => {
		if (node.type !== "command") return;
		const nameNode = node.childForFieldName("name");
		const name = nameNode?.text;
		const args: string[] = [];
		for (const child of node.namedChildren) {
			if (child === nameNode) continue;
			if (["word", "string", "raw_string", "concatenation", "number"].includes(child.type)) args.push(child.text);
		}
		commands.push({
			name,
			text: node.text,
			arguments: args,
			dynamic: !name || containsDynamic(node),
		});
	});
	return { commands, hasErrors: tree.rootNode.hasError };
}

function walk(node: Parser.SyntaxNode, visit: (node: Parser.SyntaxNode) => void): void {
	visit(node);
	for (const child of node.namedChildren) walk(child, visit);
}

function containsDynamic(node: Parser.SyntaxNode): boolean {
	let dynamic = false;
	walk(node, (child) => {
		if (
			[
				"command_substitution",
				"process_substitution",
				"expansion",
				"simple_expansion",
				"arithmetic_expansion",
			].includes(child.type)
		) {
			dynamic = true;
		}
	});
	return dynamic;
}
