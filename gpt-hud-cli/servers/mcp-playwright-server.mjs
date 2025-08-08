// Simple Playwright MCP (stdio) with a /health probe to stderr only
import { createServer } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import http from "node:http";
import { chromium } from "playwright";

const HEALTH_PORT = Number(process.env.MCP_HEALTH_PORT || 8931);
http.createServer((req, res) => {
  if (req.url !== "/health") { res.statusCode = 404; return res.end(); }
  res.setHeader("content-type","application/json");
  res.end(JSON.stringify({ ok: true, service: "mcp-playwright", time: Date.now() }));
}).listen(HEALTH_PORT, "127.0.0.1", () => {
  console.error(`[health] http://127.0.0.1:${HEALTH_PORT}/health`);
});
process.stdin.resume(); // keep alive

const server = createServer({ name: "mcp-playwright", version: "0.1.0" }, { capabilities: { tools: {} } });

server.setRequestHandler("tools/list", async () => ({
  tools: [
    { name: "playwright.navigate", description: "Open a URL in headless Chromium", inputSchema: { type: "object", properties: { url: { type: "string" } }, required: ["url"] } },
    { name: "playwright.screenshot", description: "Screenshot a URL", inputSchema: { type: "object", properties: { url: { type: "string" } }, required: ["url"] } }
  ]
}));

server.setRequestHandler("tools/call", async ({ name, arguments: args }) => {
  if (!args || typeof args.url !== "string") return { content: [{ type: "text", text: "Missing { url }" }] };
  if (name === "playwright.navigate") {
    const browser = await chromium.launch(); const page = await browser.newPage();
    await page.goto(args.url, { waitUntil: "domcontentloaded" }); await browser.close();
    return { content: [{ type: "text", text: `Navigated to ${args.url}` }] };
  }
  if (name === "playwright.screenshot") {
    const browser = await chromium.launch(); const page = await browser.newPage();
    await page.goto(args.url, { waitUntil: "domcontentloaded" });
    const buf = await page.screenshot({ fullPage: true }); await browser.close();
    return { content: [{ type: "text", text: `Screenshot bytes: ${buf.length}` }] };
  }
  return { content: [{ type: "text", text: `Unknown tool ${name}` }] };
});

await server.connect(new StdioServerTransport());
