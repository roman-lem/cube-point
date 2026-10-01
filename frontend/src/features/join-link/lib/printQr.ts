import { qrSvg } from '@/shared/lib'

function escapeHtml(text: string) {
  return text.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
}

/**
 * Prints a sheet with the meetup QR code through a hidden iframe,
 * so the sheet has none of the app's interface. The link itself is only in the QR code.
 */
export function printQr(link: string, title: string, subtitle: string) {
  const iframe = document.createElement('iframe')
  iframe.style.position = 'fixed'
  iframe.style.width = '0'
  iframe.style.height = '0'
  iframe.style.border = '0'
  document.body.append(iframe)

  const doc = iframe.contentDocument!
  // The print sheet is always black on white, theme tokens are not needed here.
  doc.open()
  doc.write(`<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  body { margin: 0; font-family: Manrope, system-ui, sans-serif; color: #000; text-align: center; }
  .sheet { padding: 20mm 15mm; }
  h1 { margin: 0 0 4mm; font-size: 28pt; }
  p { margin: 0 0 10mm; font-size: 16pt; }
  .qr { width: 120mm; height: 120mm; margin: 0 auto; }
  .qr svg { width: 100%; height: 100%; }
</style></head>
<body><div class="sheet">
  <h1>${escapeHtml(title)}</h1>
  <p>${escapeHtml(subtitle)}</p>
  <div class="qr">${qrSvg(link)}</div>
</div></body></html>`)
  doc.close()

  const win = iframe.contentWindow!
  win.addEventListener('afterprint', () => iframe.remove())
  win.focus()
  win.print()
}
