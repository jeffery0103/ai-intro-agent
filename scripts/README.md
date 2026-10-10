# build-docx.js

把學習文件的 Markdown(`學習文件_單元N-M.md`)轉成 Word(.docx),含表格、截圖、粗體、程式碼區塊。

## 為什麼要自己寫

這台電腦沒有 pandoc 也沒有 LibreOffice/soffice,無法用一般轉檔指令,所以改用 Node.js 的 `docx` 套件直接組出 .docx 檔案的 XML 結構。

## 使用方式

```bash
mkdir -p /tmp/docxbuild && cd /tmp/docxbuild
npm init -y && npm install docx image-size
# 把 build-docx.js 的 SRC / OUT 路徑改成當週要轉的檔案
node build-docx.js
```

## 已知的坑

- `docx`(npm 套件)的 `TextRun` 物件**沒有公開的 `.text` 屬性**,不能先 `inline(text)` 產生 runs 再讀 `r.text` 重組。要套用粗體(例如表格標題列)必須在 `inline(text, forceBold)` 內部直接決定要不要粗體,不能事後改寫已建好的 TextRun。
- 驗證排版:這台電腦沒有 pdftoppm/soffice,改用 Word 本身(已安裝)透過 PowerShell COM 自動化轉存 PDF:
  ```powershell
  $word = New-Object -ComObject Word.Application
  $word.Visible = $false
  $doc = $word.Documents.Open("<docx路徑>", [ref]$false, [ref]$true)
  $doc.SaveAs([ref]"<pdf路徑>", [ref]17)  # wdFormatPDF
  $doc.Close([ref]$false); $word.Quit()
  ```
  再用 Python 的 `pymupdf` 把 PDF 頁面渲染成圖片來看排版。
