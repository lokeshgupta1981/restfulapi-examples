import { jsonrepair } from 'jsonrepair'
import { z } from 'zod'
import { CASES } from './cases.mjs'

const Order = z.object({
  order_id: z.string().regex(/^A-\d{4}$/),
  items: z.array(z.object({ sku: z.string().regex(/^[A-Z]{2}-\d{2}$/), qty: z.number().int().min(1) })).min(1),
  total: z.number().positive(),
  currency: z.enum(['EUR', 'USD']),
})

for (const [name, text] of Object.entries(CASES)) {
  let strict = 'ok'
  try { JSON.parse(text) } catch (e) { strict = e.message.split('\n')[0] }
  let repaired, check
  try {
    const data = JSON.parse(jsonrepair(text))
    repaired = JSON.stringify(data)
    const result = Order.safeParse(data)
    check = result.success ? 'valid' : 'invalid: ' + result.error.issues.map(i => `${i.path.join('.') || '(root)'} ${i.code}`).join(', ')
  } catch (e) {
    repaired = 'ERROR ' + e.message
    check = 'invalid'
  }
  console.log(`${name.padEnd(20)} | ${strict.slice(0, 45).padEnd(45)} | ${check}`)
  if (name === 'prose around JSON' || name === 'NaN value') console.log(`${''.padEnd(20)} | repaired: ${repaired}`)
}
