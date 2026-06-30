#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const { dirname, join, resolve } = require("node:path");

const here = dirname(__filename);
const root = resolve(here, "..");
const cli = join(root, "src", "apexpowers_cli", "cli.py");
const python = process.env.PYTHON || process.env.PYTHON_BIN || (process.platform === "win32" ? "python" : "python3");

const env = {
  ...process.env,
  APEXPOWERS_ROOT: root,
};

const result = spawnSync(python, [cli, ...process.argv.slice(2)], {
  cwd: process.cwd(),
  env,
  stdio: "inherit",
});

if (result.error) {
  console.error(`apex: failed to run ${python}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
