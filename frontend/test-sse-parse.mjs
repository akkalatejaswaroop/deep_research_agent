import fs from "node:fs";

// Replicate EXACT frontend parsing logic from src/app/page.tsx
async function parseExactLikeFrontend(rawText, chunkSize) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(rawText);

  // Simulate network chunks of fixed size
  const chunks = [];
  for (let i = 0; i < bytes.length; i += chunkSize) {
    chunks.push(bytes.slice(i, i + chunkSize));
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let report = "";
  let receivedEnd = false;
  let jsonErrors = 0;
  const seenNodes = new Set();

  for (let ci = 0; ci < chunks.length; ci++) {
    const value = chunks[ci];
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith(":")) continue;
      if (!trimmed.startsWith("data: ")) continue;

      let data;
      try {
        data = JSON.parse(trimmed.slice(6));
      } catch {
        jsonErrors++;
        continue;
      }

      if (typeof data.node === "string") {
        const node = data.node;
        seenNodes.add(node);
        if (node === "end") {
          receivedEnd = true;
          if (typeof data.report === "string" && data.report.trim()) {
            let clean = data.report.replace(/\s*\([^)]*reported by(?: the)? source[^)]*\)/gi, "");
            clean = clean.replace(/\n### Source Notes\n[\s\S]*?(?=\n###|\n##|$)/g, "");
            report = clean;
          }
        }
      }
    }
  }

  return { report, receivedEnd, jsonErrors, seenNodes: [...seenNodes] };
}

async function main() {
  const file = process.argv[2] || "research_stream_output.txt";
  const raw = fs.readFileSync(file, "utf-8");
  console.log(`File: ${file}, bytes: ${raw.length}`);

  for (const chunkSize of [32768, 16384, 8192, 4096, 2048, 1024, 512, 256, 128]) {
    const r = await parseExactLikeFrontend(raw, chunkSize);
    console.log(
      `chunk=${chunkSize} end=${r.receivedEnd} reportChars=${r.report.length} jsonErrors=${r.jsonErrors} nodes=${r.seenNodes.join(",")}`
    );
  }
}

main();