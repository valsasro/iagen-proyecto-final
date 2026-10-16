import { stat } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { chromium } from 'playwright-core'

const projectDir = resolve(fileURLToPath(new URL('..', import.meta.url)))
const htmlPath = resolve(projectDir, 'entregable.html')
const pdfPath = resolve(projectDir, 'entregable.pdf')

const browser = await chromium.launch({ channel: 'msedge', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load' })
  await page.waitForFunction(() => [...document.images].every((image) => image.complete && image.naturalWidth > 0))
  const sheets = await page.locator('.sheet').count()
  const missing = await page.locator('img').evaluateAll((images) =>
    images.filter((image) => !image.complete || image.naturalWidth === 0).map((image) => image.getAttribute('src')),
  )
  if (missing.length) throw new Error(`No se pudieron cargar imágenes: ${missing.join(', ')}`)

  await page.emulateMedia({ media: 'print' })
  const pdf = await page.pdf({
    path: pdfPath,
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: '0mm', right: '0mm', bottom: '0mm', left: '0mm' },
  })
  const pdfText = Buffer.from(pdf).toString('latin1')
  const pages = [...pdfText.matchAll(/\/Type\s*\/Page\b/g)].length
  const bytes = (await stat(pdfPath)).size
  console.log(`PDF: ${pdfPath}`)
  console.log(`Páginas A4: ${pages}`)
  console.log(`Tamaño: ${bytes} bytes`)
  if (pages !== sheets) console.warn(`El PDF tiene ${pages} páginas y el HTML ${sheets} hojas; revisa los saltos A4.`)
} finally {
  await browser.close()
}
