// QR codes with uqr: SVG for display and printing, PNG for download.
// Black on white (the uqr default): any phone can read that.
import { renderSVG } from 'uqr'

export function qrSvg(value: string): string {
  // A white margin around the code is needed for a phone to recognize it.
  return renderSVG(value, { border: 2 })
}

/** PNG of the given size for download. */
export function qrPng(value: string, size = 1024): Promise<Blob> {
  const image = new Image()
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qrSvg(value))}`
  return new Promise((resolve, reject) => {
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const context = canvas.getContext('2d')!
      // No smoothing: sharp module edges.
      context.imageSmoothingEnabled = false
      context.drawImage(image, 0, 0, size, size)
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('PNG не создан'))))
    }
    image.onerror = () => reject(new Error('SVG не загрузился'))
  })
}

/** Saves a file through a temporary link. */
export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}
