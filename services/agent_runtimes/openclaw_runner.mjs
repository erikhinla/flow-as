/**
 * Internal HTTP adapter for the official openclaw/openclaw runtime image.
 */

import { createServer } from "node:http";
import { mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";

const host = "0.0.0.0";
const port = Number(process.env.FLOW_RUNTIME_PORT || "18790");
const model = process.env.OPENCLAW_AGENT_MODEL || "openrouter/openai/gpt-4o-mini";
const timeoutMs = Number(process.env.FLOW_RUNTIME_TIMEOUT_SECONDS || "900") * 1000;
const stateDir = "/home/node/.openclaw/flow-state";
const upstreamRepository = "https://github.com/openclaw/openclaw";
const upstreamCommit = process.env.OPENCLAW_UPSTREAM_COMMIT || "unknown";

await mkdir(stateDir, { recursive: true });

function execute(args, input = "") {
  return new Promise((resolve, reject) => {
    const child = spawn("node", ["/app/openclaw.mjs", ...args], {
      cwd: "/workspace",
      env: process.env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error("OpenClaw execution timed out"));
    }, timeoutMs);

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error(stderr.trim() || stdout.trim() || `OpenClaw exited ${code}`));
        return;
      }
      resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
    });
    child.stdin.end(input);
  });
}

async function version() {
  const result = await execute(["--version"]);
  return result.stdout || result.stderr;
}

async function run(prompt) {
  const result = await execute(
    [
      "agent",
      "exec",
      "--message-file",
      "-",
      "--cwd",
      "/workspace",
      "--state-dir",
      stateDir,
      "--model",
      model,
      "--json",
    ],
    prompt,
  );
  const envelope = JSON.parse(result.stdout);
  if (!envelope.ok || envelope.status !== "ok") {
    throw new Error(envelope?.error?.message || `OpenClaw status: ${envelope.status}`);
  }
  const final = String(envelope.final || "").trim();
  if (!final) {
    throw new Error("OpenClaw returned an empty response");
  }
  return { final, envelope };
}

function send(response, status, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(status, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
  });
  response.end(body);
}

const server = createServer(async (request, response) => {
  if (request.method === "GET" && ["/health", "/healthz"].includes(request.url)) {
    try {
      send(response, 200, {
        ok: true,
        engine: "openclaw",
        version: await version(),
        upstream_repository: upstreamRepository,
        upstream_commit: upstreamCommit,
      });
    } catch (error) {
      send(response, 503, { ok: false, engine: "openclaw", error: String(error.message || error) });
    }
    return;
  }

  if (request.method !== "POST" || request.url !== "/run") {
    send(response, 404, { ok: false, error: "not found" });
    return;
  }

  let body = "";
  request.on("data", (chunk) => {
    body += chunk.toString();
  });
  request.on("end", async () => {
    try {
      const payload = JSON.parse(body || "{}");
      const prompt = String(payload.prompt || "").trim();
      if (!prompt) {
        send(response, 400, { ok: false, error: "prompt is required" });
        return;
      }
      const result = await run(prompt);
      send(response, 200, {
        ok: true,
        engine: "openclaw",
        final: result.final,
        usage: result.envelope.usage,
        model: result.envelope.model,
        provider: result.envelope.provider,
        upstream_repository: upstreamRepository,
        upstream_commit: upstreamCommit,
      });
    } catch (error) {
      send(response, 500, { ok: false, engine: "openclaw", error: String(error.message || error) });
    }
  });
});

server.listen(port, host, () => {
  process.stdout.write(`OpenClaw adapter listening on ${host}:${port} (upstream ${upstreamCommit})\n`);
});
