import { createRoot } from 'react-dom/client'
import PortfolioReportDocument from '../components/PortfolioReportDocument'

const PRINT_STYLES = `
  * { box-sizing: border-box; }
  body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; color: #0f172a; background: #fff; }
  .portfolio-report-doc { padding: 24px 32px; max-width: 720px; margin: 0 auto; }
`

/** Opens a minimal iframe, renders the report, triggers print, then cleans up. */
export function printPortfolioReport(property) {
  const iframe = document.createElement('iframe')
  iframe.setAttribute('aria-hidden', 'true')
  Object.assign(iframe.style, {
    position: 'fixed',
    width: '0',
    height: '0',
    border: '0',
    visibility: 'hidden',
    pointerEvents: 'none',
  })
  document.body.appendChild(iframe)

  const doc = iframe.contentDocument
  const win = iframe.contentWindow
  if (!doc || !win) {
    document.body.removeChild(iframe)
    return
  }

  doc.open()
  doc.write(`<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>PropIntel — Report #${property.id}</title><style>${PRINT_STYLES}</style></head><body><div id="print-root"></div></body></html>`)
  doc.close()

  const container = doc.getElementById('print-root')
  const root = createRoot(container)
  root.render(<PortfolioReportDocument property={property} />)

  let cleaned = false
  const cleanup = () => {
    if (cleaned) return
    cleaned = true
    try {
      root.unmount()
    } catch {
      // ignore
    }
    iframe.remove()
  }

  win.addEventListener('afterprint', cleanup)

  requestAnimationFrame(() => {
    setTimeout(() => {
      try {
        win.focus()
        win.print()
      } catch {
        cleanup()
      }
      setTimeout(cleanup, 2_000)
    }, 0)
  })
}
