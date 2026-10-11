// Fails if the built JS+CSS exceeds the low-bandwidth budget (docs/PRODUCT_REQUIREMENTS.md NFR-1).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const BUDGET_BYTES = 250 * 1024
const dir = 'dist/assets'

let total = 0
for (const name of readdirSync(dir)) {
  if (!/\.(js|css)$/.test(name)) continue
  const path = join(dir, name)
  if (!statSync(path).isFile()) continue
  const gz = gzipSync(readFileSync(path)).length
  total += gz
  console.log(`${(gz / 1024).toFixed(1).padStart(7)} KB  ${name}`)
}
console.log(`${(total / 1024).toFixed(1).padStart(7)} KB  total gzip (budget ${BUDGET_BYTES / 1024} KB)`)
if (total > BUDGET_BYTES) {
  console.error('Bundle exceeds budget.')
  process.exit(1)
}
