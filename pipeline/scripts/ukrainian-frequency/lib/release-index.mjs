// ---------------------------------------------------------------------------
// Ukrainian Frequency - the download-directory index page.
//
// A versioned release dir under public/ has no route of its own, so hitting the
// bare directory URL would 404. This renders a tiny, self-contained,
// dependency-free index.html the generator drops into the release root, so the
// raw URL resolves to a human-readable listing.
//
// Pure: string in, string out. No IO. House rule: no em-dashes.
// ---------------------------------------------------------------------------

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function renderReleaseIndex({ kicker, title, subject, version, license, canonical, citation, files = [] }) {
  const rows = [...files, "manifest.json", "SHA256SUMS"]
    .map((f) => {
      const kind = f.endsWith(".json")
        ? "JSON"
        : f.endsWith(".csv")
          ? "CSV"
          : f.endsWith(".tsv")
            ? "TSV"
            : f === "SHA256SUMS"
              ? "checksums"
              : "file";
      return `      <li><a href="./${esc(f)}" download>${esc(f)}</a> <span class="k">${esc(kind)}</span></li>`;
    })
    .join("\n");

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="noindex" />
<title>${esc(title)} (${esc(version)}) - open data</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #F6F4EE; color: #191815;
    font-family: 'Source Serif 4', Georgia, serif; line-height: 1.55; }
  main { max-width: 720px; margin: 0 auto; padding: 48px 24px 64px; }
  .kicker { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 1.5px;
    text-transform: uppercase; color: #2A5C84; margin-bottom: 12px; }
  h1 { font-family: 'DM Serif Display', Georgia, serif; font-size: clamp(26px,5vw,40px);
    line-height: 1.1; margin: 0 0 12px; }
  p { color: #3C3A34; margin: 0 0 16px; }
  a { color: #2A5C84; }
  ul { list-style: none; padding: 0; margin: 18px 0; display: grid; gap: 8px; }
  li { font-family: 'IBM Plex Mono', monospace; font-size: 14px; padding: 10px 14px;
    background: #FFFFFF; border: 1px solid #E2DDD2; border-radius: 6px; }
  .k { color: #8A8477; font-size: 12px; margin-left: 6px; }
  .meta { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #615D54; }
  pre { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #3C3A34;
    white-space: pre-wrap; word-break: break-word; background: #FBFAF6;
    border: 1px solid #E2DDD2; border-radius: 6px; padding: 14px; }
</style>
</head>
<body>
<main>
  <div class="kicker">${esc(kicker)}</div>
  <h1>${esc(title)}</h1>
  <p>${esc(subject)}</p>
  <p class="meta">${esc(version)} &middot; ${esc(license)} &middot; <a href="${esc(canonical)}">back to the study</a></p>
  <ul>
${rows}
  </ul>
  <p class="meta">Cite:</p>
  <pre>${esc(citation)}</pre>
</main>
</body>
</html>
`;
}
