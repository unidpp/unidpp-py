#!/usr/bin/env node
// Transpile a TypeScript fixture (e.g. open-dpp's
// `apps/e2e/tests/api/battery-passport.ts`) with esbuild and write the
// named export as JSON. Used to capture machine-checkable artifacts
// from competitor repos whose only published examples are TS object
// literals.
//
// Usage: node scripts/extract-ts-fixture.mjs <input.ts> <exportName> <output.json>
//
// Requires esbuild. The unidpp-py repo's glossarist concept-browser
// transitively installs esbuild; the runner falls back to the bundled
// copy at @glossarist/concept-browser/node_modules/esbuild when no
// top-level esbuild is installed.

const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");

function resolveEsmBuild() {
  const candidates = [
    () => require.resolve("esbuild"),
    () => path.join(
      process.env.HOME || "/Users/mulgogi",
      ".local/share/mise/installs/node/24.14.0/lib/node_modules/@glossarist/concept-browser/node_modules/esbuild",
    ),
  ];
  for (const c of candidates) {
    try {
      const p = c();
      return require(p);
    } catch (_) { /* try next */ }
  }
  throw new Error(
    "esbuild not found — install it (npm i -g esbuild) or set HOME so the " +
    "mise node path resolves"
  );
}

function main() {
  const [, , inputPath, exportName, outputPath] = process.argv;
  if (!inputPath || !exportName || !outputPath) {
    console.error(
      "usage: extract-ts-fixture.mjs <input.ts> <exportName> <output.json>"
    );
    process.exit(2);
  }

  const esbuild = resolveEsmBuild();
  const absInput = path.resolve(inputPath);
  const src = fs.readFileSync(absInput, "utf8");
  const { code } = esbuild.transformSync(src, {
    loader: "ts",
    format: "cjs",
  });
  const tmp = absInput + ".cjs";
  fs.writeFileSync(tmp, code);

  // Bust Node's CJS cache for the temp file.
  delete require.cache[require.resolve(tmp)];
  const mod = require(tmp);
  const obj = exportName === "default" ? mod.default : mod[exportName];
  if (obj === undefined) {
    console.error(
      `export ${exportName} not found in ${absInput}; available: ` +
        Object.keys(mod).join(", ")
    );
    process.exit(1);
  }
  fs.writeFileSync(path.resolve(outputPath), JSON.stringify(obj, null, 2));
  console.log(`wrote ${path.resolve(outputPath)} (${JSON.stringify(obj).length} bytes)`);
}

main();
