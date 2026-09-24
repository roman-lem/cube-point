// QR-коды через uqr: SVG для показа и печати, PNG для скачивания.
// Цвета — чёрный на белом (по умолчанию в uqr): так код читает любой телефон.
import { renderSVG } from 'uqr'

export function qrSvg(value: string): string {
  // Белое поле вокруг кода нужно, чтобы телефон его распознал.
  return renderSVG(value, { border: 2 })
}

/** PNG заданного размера для скачивания. */
export function qrPng(value: string, size = 1024): Promise<Blob> {
  const image = new Image()
  image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(qrSvg(value))}`
  return new Promise((resolve, reject) => {
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = size
      canvas.height = size
      const context = canvas.getContext('2d')!
      // Без сглаживания: чёткие края модулей.
      context.imageSmoothingEnabled = false
      context.drawImage(image, 0, 0, size, size)
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('PNG не создан'))))
    }
    image.onerror = () => reject(new Error('SVG не загрузился'))
  })
}

/** Сохраняет файл через временную ссылку. */
export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}
