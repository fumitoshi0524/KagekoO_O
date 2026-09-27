import { McpAuth as McpOAuthClient } from "../../capabilities/mcp/mcp-auth.js";
import type { OAuthNotifyEvent } from "../../capabilities/mcp/mcp-auth.js";
import type { Tool, ToolContext } from "../types.js";

export const mcpAuthTool: Tool<{ server: string; force?: boolean }> = {
	name: "mcp_auth",
	description: "Authenticate with a remote MCP server using OAuth.",
	parameters: {
		type: "object",
		properties: {
			server: { type: "string", description: "MCP server name" },
			force: { type: "boolean", description: "Run authentication even if a token already exists" },
		},
		required: ["server"],
	},
	async execute({ server, force = false }: { server: string; force?: boolean }, { session, signal }: ToolContext) {
		if (!session?.mcp?.configs) {
			return { output: "MCP manager not available or has no server configs.", isError: true };
		}

		const config = session.mcp.configs[server];
		if (!config) {
			return { output: `Unknown MCP server: ${server}`, isError: true };
		}

		if (!config.oauth) {
			return { output: `MCP server ${server} has no OAuth configuration.`, isError: true };
		}

		const sessionRecord = session as unknown as Record<string, unknown>;
		if (!sessionRecord["mcpOAuthClient"]) {
			if (!session.mcpTokenStore) {
				return { output: "MCP token store is not configured by the application.", isError: true };
			}
			sessionRecord["mcpOAuthClient"] = new McpOAuthClient({
				tokenStore: session.mcpTokenStore,
				callbacks: {
					notify: (event: OAuthNotifyEvent) => {
						const message = oauthNotificationMessage(event, server);
						try {
							void Promise.resolve(session.reportDiagnostic?.({ code: "mcp.oauth", message })).catch(() => {});
						} catch {
							/* host diagnostics are observational */
						}
					},
				},
			});
		}
		const client = sessionRecord["mcpOAuthClient"] as McpOAuthClient;

		if (!force) {
			const existing = await client.getToken(server);
			if (existing?.accessToken) {
				return { output: `Already authenticated with ${server}. Use force=true to re-authenticate.` };
			}
		}

		try {
			await client.authenticate(
				server,
				config as unknown as import("../../capabilities/mcp/mcp-auth.js").McpOAuthConfig,
				{ signal },
			);
			return { output: `Authenticated with ${server} and stored token.` };
		} catch (err) {
			return { output: `Authentication failed: ${(err as Error).message}`, isError: true };
		}
	},
};

function oauthNotificationMessage(event: OAuthNotifyEvent, fallbackServer: string): string {
	if (event.type === "auth_url") {
		return [`Open this URL to authenticate ${event.serverName ?? fallbackServer}:`, event.url, event.instructions]
			.filter(Boolean)
			.join("\n");
	}
	if (event.type === "device_code") {
		return [
			`Device code login for ${event.serverName ?? fallbackServer}:`,
			`User code: ${event.userCode}`,
			`Verification URI: ${event.verificationUri}`,
			event.expiresInSeconds ? `Expires in: ${event.expiresInSeconds}s` : undefined,
			event.intervalSeconds ? `Poll interval: ${event.intervalSeconds}s` : undefined,
			"Waiting for authorization...",
		]
			.filter(Boolean)
			.join("\n");
	}
	return event.message ?? `OAuth authentication update for ${event.serverName ?? fallbackServer}.`;
}
