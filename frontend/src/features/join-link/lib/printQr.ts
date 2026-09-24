import { qrSvg } from '@/shared/lib'

function escapeHtml(text: string) {
  return text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
}

/**
 * Печатает лист с QR-кодом встречи через скрытый iframe,
 * чтобы на листе не было интерфейса приложения.
 */
export function printQr(link: string, title: string, subtitle: string) {
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  document.body.append(iframe)

  const doc = iframe.contentDocument!
  // Лист для печати — всегда чёрным по белому, токены темы здесь не нужны.
  doc.open()
  doc.write(`<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  body { margin: 0; font-family: Manrope, system-ui, sans-serif; color: #000; text-align: center; }
  .sheet { padding: 20mm 15mm; }
  h1 { margin: 0 0 4mm; font-size: 28pt; }
  p { margin: 0 0 10mm; font-size: 16pt; }
  .qr { width: 120mm; height: 120mm; margin: 0 auto 10mm; }
  .qr svg { width: 100%; height: 100%; }
  .link { font-family: monospace; font-size: 11pt; word-break: break-all; }
</style></head>
<body><div class="sheet">
  <h1>${escapeHtml(title)}</h1>
  <p>${escapeHtml(subtitle)}</p>
  <div class="qr">${qrSvg(link)}</div>
  <div class="link">${escapeHtml(link)}</div>
</div></body></html>`)
  doc.close()

  const win = iframe.contentWindow!
  win.addEventListener('afterprint', () => iframe.remove())
  win.focus()
  win.print()
}
