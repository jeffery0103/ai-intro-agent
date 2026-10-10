const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType, ImageRun, AlignmentType, LevelFormat,
  ExternalHyperlink, PageBreak, convertInchesToTwip
} = require("docx");
const sizeOf = (() => { try { return require("image-size").imageSize; } catch { return null; } })();

const ROOT = "D:\\使用者\\下載\\AI導論";
const srcName = process.argv[2] || "學習文件_單元1-4.md";
const outName = process.argv[3] || srcName.replace(/\.md$/, ".docx");
const SRC = path.join(ROOT, srcName);
const SHOTS = path.join(ROOT, "截圖");
const OUT = path.join(ROOT, outName);

let raw = fs.readFileSync(SRC, "utf8");
raw = raw.replace(/\r\n/g, "\n"); // normalize CRLF -> LF (some files were saved with Windows line endings, which silently breaks every regex below that relies on $/heading matches)
raw = raw.replace(/^---\n[\s\S]*?\n---\n/, ""); // strip frontmatter
const lines = raw.split("\n");

// ---- inline markdown -> TextRun[] ----
function inline(text, opts = {}) {
  const forceBold = opts === true || opts.bold; // back-compat: inline(text, true) still means forceBold
  const forceItalic = !!opts.italics;
  const forceColor = opts.color;
  const runs = [];
  let i = 0;
  let buf = "";
  let bold = false;
  const flush = () => { if (buf) { runs.push(new TextRun({ text: buf, bold: bold || forceBold, italics: forceItalic, color: forceColor })); buf = ""; } };
  while (i < text.length) {
    if (text.startsWith("**", i)) {
      flush(); bold = !bold; i += 2; continue;
    }
    if (text[i] === "`") {
      flush();
      let j = text.indexOf("`", i + 1);
      if (j === -1) j = text.length;
      const code = text.slice(i + 1, j);
      runs.push(new TextRun({ text: code, bold: forceBold, italics: forceItalic, color: forceColor, font: "Consolas", shading: { type: ShadingType.CLEAR, fill: "F0F0F0" } }));
      i = j + 1; continue;
    }
    buf += text[i]; i++;
  }
  flush();
  if (runs.length === 0) runs.push(new TextRun({ text: "" }));
  return runs;
}

function para(text, opts = {}) {
  return new Paragraph({ children: inline(text), spacing: { after: 120 }, ...opts });
}

// ---- table parsing (GFM pipe tables) ----
function parseTableRow(line) {
  let l = line.trim();
  if (l.startsWith("|")) l = l.slice(1);
  if (l.endsWith("|")) l = l.slice(0, -1);
  return l.split("|").map(c => c.trim());
}
function isSepRow(line) {
  return /^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$/.test(line.trim());
}

function buildTable(headerCells, bodyRows) {
  const nCols = headerCells.length;
  const totalWidth = 9000; // DXA, fits A4 with margins
  const colWidth = Math.floor(totalWidth / nCols);
  const colWidths = new Array(nCols).fill(colWidth);
  const mkCell = (text, isHeader) => new TableCell({
    width: { size: colWidth, type: WidthType.DXA },
    shading: isHeader ? { type: ShadingType.CLEAR, fill: "EEF2F7" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: inline(text, { bold: isHeader }) })],
  });
  const rows = [];
  rows.push(new TableRow({ children: headerCells.map(c => mkCell(c, true)), tableHeader: true }));
  for (const r of bodyRows) {
    const cells = parseTableRow(r);
    while (cells.length < nCols) cells.push("");
    rows.push(new TableRow({ children: cells.slice(0, nCols).map(c => mkCell(c, false)) }));
  }
  return new Table({ rows, width: { size: totalWidth, type: WidthType.DXA }, columnWidths: colWidths });
}

// ---- image handling ----
const imgCache = {};
function imageParagraph(caption, filename) {
  const p = path.join(SHOTS, filename);
  if (!fs.existsSync(p)) {
    return [para("【缺圖:" + filename + "】" + caption)];
  }
  const buf = fs.readFileSync(p);
  const maxW = 560, maxH = 720; // px; cap both dimensions so tall (portrait) screenshots don't overflow the page
  let w = maxW, h = Math.round(maxW * 0.643); // fallback only used if dimension probing fails
  if (sizeOf) {
    const d = sizeOf(buf); // throws on failure now (no try/catch swallow) so a bad read is visible, not silently wrong
    const scale = Math.min(1, maxW / d.width, maxH / d.height);
    w = Math.round(d.width * scale);
    h = Math.round(d.height * scale);
  }
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 100, after: 40 },
      children: [ new ImageRun({ data: buf, type: filename.endsWith(".jpg") ? "jpg" : "png", transformation: { width: w, height: h } }) ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 160 },
      children: [ new TextRun({ text: caption, italics: true, size: 18, color: "555555" }) ],
    }),
  ];
}

// ---- main parse loop ----
const children = [];
let i = 0;
let firstH1Seen = false;

while (i < lines.length) {
  let line = lines[i];

  // skip fully blank lines (handled by paragraph spacing)
  if (line.trim() === "") { i++; continue; }

  // screenshot line: - 【截圖:caption】 `filename`
  let m = line.match(/^-\s*【截圖[::]?([^】]*)】\s*`([^`]+)`/);
  if (m) {
    children.push(...imageParagraph(m[1].trim(), m[2].trim()));
    i++; continue;
  }

  // horizontal rule
  if (/^-{3,}\s*$/.test(line.trim())) {
    children.push(new Paragraph({ border: { bottom: { color: "999999", space: 1, style: BorderStyle.SINGLE, size: 6 } }, spacing: { after: 200 } }));
    i++; continue;
  }

  // code fence
  if (/^```/.test(line.trim())) {
    i++;
    const codeLines = [];
    while (i < lines.length && !/^```/.test(lines[i].trim())) { codeLines.push(lines[i]); i++; }
    i++; // skip closing fence
    for (const cl of codeLines) {
      children.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
        spacing: { after: 0 },
        children: [ new TextRun({ text: cl.length ? cl : " ", font: "Consolas", size: 18 }) ],
      }));
    }
    children.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    continue;
  }

  // table
  if (line.trim().startsWith("|") && i + 1 < lines.length && isSepRow(lines[i + 1])) {
    const header = parseTableRow(line);
    i += 2;
    const bodyRows = [];
    while (i < lines.length && lines[i].trim().startsWith("|")) { bodyRows.push(lines[i]); i++; }
    children.push(buildTable(header, bodyRows));
    children.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
    continue;
  }

  // blockquote
  if (line.startsWith("> ")) {
    const qLines = [];
    while (i < lines.length && lines[i].startsWith("> ")) { qLines.push(lines[i].slice(2)); i++; }
    for (const ql of qLines) {
      children.push(new Paragraph({
        indent: { left: 400 },
        border: { left: { color: "AAAAAA", space: 8, style: BorderStyle.SINGLE, size: 12 } },
        shading: { type: ShadingType.CLEAR, fill: "FAFAFA" },
        spacing: { after: 120 },
        children: inline(ql, { italics: true, color: "333333" }),
      }));
    }
    continue;
  }

  // headings
  m = line.match(/^(#{1,4})\s+(.*)$/);
  if (m) {
    const level = m[1].length;
    const levelMap = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3, 4: HeadingLevel.HEADING_4 };
    const opts = { heading: levelMap[level] || HeadingLevel.HEADING_4, spacing: { before: level <= 2 ? 300 : 200, after: 140 } };
    if (level === 1 && firstH1Seen) opts.pageBreakBefore = false;
    if (level === 1) firstH1Seen = true;
    children.push(new Paragraph({ ...opts, children: inline(m[2]) }));
    i++; continue;
  }

  // numbered list
  m = line.match(/^(\d+)\.\s+(.*)$/);
  if (m) {
    children.push(new Paragraph({ numbering: { reference: "num-list", level: 0 }, spacing: { after: 80 }, children: inline(m[2]) }));
    i++; continue;
  }

  // bullet list
  m = line.match(/^-\s+(.*)$/);
  if (m) {
    children.push(new Paragraph({ numbering: { reference: "bullet-list", level: 0 }, spacing: { after: 80 }, children: inline(m[1]) }));
    i++; continue;
  }

  // plain paragraph (collect consecutive non-blank plain lines)
  const buf2 = [line];
  i++;
  while (i < lines.length && lines[i].trim() !== "" &&
         !/^(#{1,4})\s/.test(lines[i]) && !lines[i].trim().startsWith("|") &&
         !lines[i].startsWith("> ") && !/^```/.test(lines[i].trim()) &&
         !/^-{3,}\s*$/.test(lines[i].trim()) && !/^-\s/.test(lines[i]) && !/^\d+\.\s/.test(lines[i]) &&
         !/^-\s*【截圖/.test(lines[i])) {
    buf2.push(lines[i]); i++;
  }
  children.push(para(buf2.join(" ")));
}

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullet-list", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 260 } } } }] },
      { reference: "num-list", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 260 } } } }] },
    ],
  },
  styles: {
    default: { document: { run: { font: "Microsoft JhengHei", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", run: { size: 32, bold: true, color: "1A1A1A" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", run: { size: 27, bold: true, color: "2E4A73" } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", run: { size: 24, bold: true, color: "333333" } },
      { id: "Heading4", name: "Heading 4", basedOn: "Normal", next: "Normal", run: { size: 22, bold: true, italics: true } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1000, bottom: 1000, left: 1100, right: 1100 } } },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT, buf);
  console.log("WROTE:", OUT, (buf.length / 1024).toFixed(0) + " KB", "| paragraphs/elements:", children.length);
});
