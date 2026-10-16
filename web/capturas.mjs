import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const appUrl = process.env.APP_URL ?? 'http://127.0.0.1:5173/'
const projectDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const outputDir = join(projectDir, 'capturas')
const questions = [
  {
    id: '06-plazo',
    question: '¿Cuánto tiempo tengo para registrar la actividad de tiempo libre en JCYL, porque mi campamento comienza dentro de 2 semanas?',
  },
  {
    id: '07-tiempo',
    question: 'Dime la previsión del tiempo para mañana en Valladolid',
    expectNoConsta: true,
  },
  {
    id: '08-monitores',
    question: '¿Cuántos monitores necesito para un campamento evaluado con riesgo moderado, donde participan 38 niños?',
  },
  {
    id: '09-evaluacion',
    question: '¿Es obligatoria siempre hacer la evaluación de riesgos?',
  },
  {
    id: '10-recuento',
    question: 'Dime cuántos campamentos llevamos en el año actual',
    expectNoConsta: true,
  },
]

await mkdir(outputDir, { recursive: true })
const verificationPath = join(outputDir, 'verificacion.json')
let previous = { questions: [], documents: [] }
try {
  previous = JSON.parse(await readFile(verificationPath, 'utf8'))
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}

const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 })
const results = []

try {
  page.setDefaultTimeout(180_000)
  page.on('pageerror', (error) => console.error(`Error de página: ${error.message}`))

  const response = await page.goto(appUrl, { waitUntil: 'domcontentloaded' })
  if (!response?.ok()) throw new Error(`La aplicación no respondió correctamente en ${appUrl}`)
  await page.locator('#question-input').waitFor({ state: 'visible' })
  await page.locator('.nav-item').filter({ hasText: 'Documentos' }).waitFor({ state: 'visible' })
  const chatCaptureStyle = await page.addStyleTag({
    content: `
      .welcome-row, .chat-aside, .disclosure { display: none !important; }
      .page-wrap { width: calc(100% - 48px) !important; margin: 18px auto !important; }
      .workspace { min-height: 0 !important; }
      .chat-layout { display: block !important; }
      .conversation { height: auto !important; min-height: 0 !important; max-height: none !important; overflow: visible !important; }
      .turn:not(:nth-last-child(-n + 2)) { display: none !important; }
      .main-panel { padding-bottom: 16px !important; }
    `,
  })

  for (const item of questions) {
    await page.locator('#question-input').fill(item.question)
    await page.locator('.send-button').click()

    const card = page.locator('.answer-card').last()
    await card.locator('.answer-text').waitFor({ state: 'visible', timeout: 180_000 })
    const answer = (await card.locator('.answer-text').innerText()).trim()
    const noConsta = (await card.locator('.not-found-notice').count()) > 0

    if (!answer || answer.includes('Consultando documentos')) {
      throw new Error(`La respuesta de «${item.id}» está vacía o sigue pendiente.`)
    }
    if (item.expectNoConsta && !noConsta) {
      throw new Error(`«${item.id}» no mostró el aviso esperado de dato no disponible.`)
    }

    const sources = []
    if (!noConsta) {
      const sourceBlock = card.locator('.sources-block')
      await sourceBlock.waitFor({ state: 'visible', timeout: 30_000 })
      const sourceCards = card.locator('.source-card')
      const count = await sourceCards.count()
      if (count === 0) throw new Error(`«${item.id}» no incluyó fuentes.`)
      for (let index = 0; index < count; index += 1) {
        const source = sourceCards.nth(index)
        sources.push({
          id: (await source.locator('.source-label').innerText()).trim(),
          title: (await source.locator('strong').innerText()).trim(),
          fragment: (await source.locator('.source-fragment').innerText()).trim(),
          url: await source.getAttribute('href'),
        })
      }
    }

    await page.locator('.conversation').evaluate((element) => {
      element.scrollTop = element.scrollHeight
    })
    await page.waitForTimeout(300)
    const imagePath = join(outputDir, `${item.id}.png`)
    await page.screenshot({ path: imagePath, fullPage: true })
    results.push({ ...item, answer, noConsta, sources, image: `capturas/${item.id}.png` })
    console.log(`${item.id}: ${noConsta ? 'No consta' : `respuesta con ${sources.length} fuentes`} · ${imagePath}`)
  }

  await chatCaptureStyle.evaluate((element) => element.remove())
  await page.locator('.nav-item').filter({ hasText: 'Documentos' }).click()
  await page.locator('.document-row').first().waitFor({ state: 'visible', timeout: 30_000 })
  await page.waitForTimeout(300)
  const documentsImage = join(outputDir, '05-documentos.png')
  await page.screenshot({ path: documentsImage })
  const documentTitles = await page.locator('.document-row h3').allInnerTexts()
  if (documentTitles.length === 0) throw new Error('La biblioteca no mostró documentos.')

  const byId = new Map((previous.questions ?? []).map((item) => [item.id, item]))
  for (const item of results) byId.set(item.id, item)
  await writeFile(
    verificationPath,
    JSON.stringify({
      appUrl,
      viewport: { width: 1366, height: 900 },
      questions: [...byId.values()],
      documents: documentTitles,
    }, null, 2),
    'utf8',
  )
  console.log(`05-documentos: captura guardada (${documentTitles.length} documentos visibles).`)
} finally {
  await browser.close()
}
