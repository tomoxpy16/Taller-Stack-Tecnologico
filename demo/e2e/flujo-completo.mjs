// Prueba de extremo a extremo del flujo completo contra el backend real.
// Requiere la demo corriendo (ver demo/README.md). Uso:
//   cd demo/e2e && npm install && npx playwright install chromium && node flujo-completo.mjs
// Variables opcionales: BASE (URL del frontend), LUNA (id del animal), SHOTS (carpeta de capturas),
// CHROMIUM_PATH (ejecutable de Chromium si no se usa el de Playwright).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const B = process.env.BASE || 'http://localhost:5174'
const LUNA = process.env.LUNA || 'a1'
const out = process.env.SHOTS || './capturas'
mkdirSync(out, { recursive: true })

const b = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {})
const errs = []

async function nuevo() {
  const c = await b.newContext({ viewport: { width: 1280, height: 900 } })
  const p = await c.newPage()
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()) })
  p.on('response', (r) => { if (r.url().includes('/api/') && r.status() >= 400) errs.push(r.status() + ' ' + r.url()) })
  return p
}

async function postular(p, nombre, email) {
  await p.goto(B + '/animales/' + LUNA); await p.waitForTimeout(800)
  await p.click('text=Postular'); await p.waitForSelector('#mensaje')
  await p.fill('#nombre', nombre); await p.fill('#email', email)
  await p.fill('#telefono', '3001234567'); await p.fill('#ciudad', 'Bogotá')
  await p.fill('#mensaje', 'Tengo casa con patio y experiencia con perros.')
  await p.click('button.btn--primary'); await p.waitForTimeout(1500)
  return p.url()
}

// 1. Catálogo
const p1 = await nuevo()
await p1.goto(B + '/animales'); await p1.waitForSelector('.animal-card')
console.log('Tarjetas en el catálogo:', await p1.locator('.animal-card').count())
await p1.screenshot({ path: out + '/1-catalogo.png' })

// 2. Postular y 3. postulación duplicada (debe responder 409)
console.log('Postulación 1:', await postular(p1, 'Ana Gómez', 'ana@x.co'))
await p1.screenshot({ path: out + '/2-postulacion.png' })
console.log('Duplicada:', await postular(p1, 'Ana Gómez', 'ana@x.co'))
await p1.screenshot({ path: out + '/3-duplicada.png' })

const p2 = await nuevo()
console.log('Postulación 2:', await postular(p2, 'Luis Pérez', 'luis@x.co'))

// 4. Panel del refugio: aprobar una postulación
const p3 = await nuevo()
await p3.goto(B + '/animales'); await p3.selectOption('header select', 'refugio'); await p3.waitForTimeout(500)
await p3.goto(B + '/refugio'); await p3.waitForTimeout(1500)
await p3.screenshot({ path: out + '/4-panel.png' })
await p3.locator('button:has-text("Aprobar")').first().click(); await p3.waitForTimeout(400)
await p3.locator('.modal button.btn--primary, [role=dialog] button.btn--primary').last().click()
  .catch(async () => { await p3.locator('button:has-text("Aprobar")').last().click() })
await p3.waitForTimeout(1500)

// 5. Las demás quedan rechazadas por cierre automático
await p3.click('button[role=tab]:has-text("Rechazadas")'); await p3.waitForTimeout(500)
await p3.screenshot({ path: out + '/5-rechazadas.png' })
console.log('Rechazadas:', (await p3.locator('main').innerText()).slice(0, 600).replace(/\n/g, ' | '))

// 6. Publicar un animal
await p3.goto(B + '/refugio/publicar')
await p3.fill('#p-nombre', 'Rocky'); await p3.fill('#p-edad', '24'); await p3.fill('#p-temp', 'tranquilo')
await p3.click('button:has-text("Publicar")'); await p3.waitForTimeout(1500)
console.log('Publicado:', p3.url())
await p3.screenshot({ path: out + '/6-publicado.png' })

// El único error esperado es el 409 de la postulación duplicada.
console.log('Errores HTTP/consola:', JSON.stringify(errs))
await b.close()
