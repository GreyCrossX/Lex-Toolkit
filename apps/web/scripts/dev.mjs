#!/usr/bin/env node
import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(webDir, "..", "..");
const args = process.argv.slice(2);
const useFull = args.includes("--full");
const nextArgs = args.filter((arg) => arg !== "--full");

const withNodeBin = {
  ...process.env,
  PATH: `${path.join(webDir, "node_modules", ".bin")}${path.delimiter}${process.env.PATH}`,
};

if (useFull) {
  try {
    const result = spawnSync("docker", ["compose", "up", "-d", "pgvector", "api"], {
      cwd: repoRoot,
      stdio: "inherit",
    });

    if (result.status !== 0) {
      console.error("\nFailed to start Docker services. Is Docker running and docker compose available?");
      process.exit(result.status ?? 1);
    }
  } catch (error) {
    console.error("\nDocker is not available. Install/enable Docker to use --full.\nDetails:", error);
    process.exit(1);
  }
}

const dev = spawn("next", ["dev", ...nextArgs], {
  cwd: webDir,
  stdio: "inherit",
  env: withNodeBin,
});

dev.on("exit", (code) => process.exit(code ?? 0));
