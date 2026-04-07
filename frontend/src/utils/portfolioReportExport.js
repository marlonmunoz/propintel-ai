function formatCurrency(value) {
  if (value == null) return ''
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value) {
  if (value == null) return ''
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

function escapeCsvField(value) {
  if (value == null || value === '') return ''
  const s = String(value)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

/** One header row + one data row for this saved property. */
export function buildPropertyCsv(property) {
  const a = property?.analysis
  const v = a?.valuation
  const inv = a?.investment_analysis
  const headers = [
    'property_id',
    'address',
    'zipcode',
    'bedrooms',
    'bathrooms',
    'sqft',
    'listing_price',
    'saved_at',
    'deal_label',
    'investment_score',
    'predicted_price',
    'market_price',
    'price_difference_pct',
    'roi_estimate',
    'recommendation',
    'analysis_summary',
  ]
  const row = [
    property.id,
    property.address,
    property.zipcode,
    property.bedrooms,
    property.bathrooms,
    property.sqft,
    property.listing_price,
    property.created_at ?? '',
    inv?.deal_label ?? '',
    inv?.investment_score ?? '',
    v?.predicted_price ?? '',
    v?.market_price ?? '',
    v?.price_difference_pct ?? '',
    inv?.roi_estimate ?? '',
    inv?.recommendation ?? '',
    inv?.analysis_summary ?? '',
  ]
  return [headers.map(escapeCsvField).join(','), row.map(escapeCsvField).join(',')].join('\r\n')
}

export function downloadPropertyCsv(property) {
  const csv = buildPropertyCsv(property)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `propintel-report-${property.id}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const MARGIN = 18
const PAGE_W = 210
const LINE_H = 5
const MAX_W = PAGE_W - MARGIN * 2

function ensureY(doc, y) {
  if (y > 278) {
    doc.addPage()
    return MARGIN
  }
  return y
}

function paragraph(doc, text, y, opts = { size: 10 }) {
  doc.setFontSize(opts.size)
  const body = text == null || text === '' ? '—' : String(text)
  const lines = doc.splitTextToSize(body, MAX_W)
  for (let i = 0; i < lines.length; i += 1) {
    y = ensureY(doc, y)
    doc.text(lines[i], MARGIN, y)
    y += LINE_H
  }
  return y + 2
}

function heading(doc, title, y) {
  y = ensureY(doc, y)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.text(title, MARGIN, y)
  doc.setFont('helvetica', 'normal')
  return y + LINE_H + 2
}

export async function downloadPropertyPdf(property) {
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })
  let y = MARGIN

  doc.setFontSize(16)
  doc.setFont('helvetica', 'bold')
  doc.text('PropIntel AI', MARGIN, y)
  y += 8
  doc.setFontSize(10)
  doc.setFont('helvetica', 'normal')
  doc.text('Saved analysis report', MARGIN, y)
  y += 6
  y = paragraph(
    doc,
    'Estimates are for education and decision support only — not financial, legal, or investment advice.',
    y,
    { size: 8 }
  )

  y = heading(doc, 'Property', y)
  doc.setFontSize(10)
  y = paragraph(doc, `Record ID: ${property.id}`, y)
  y = paragraph(doc, `Address: ${property.address}`, y)
  y = paragraph(doc, `ZIP: ${property.zipcode}`, y)
  y = paragraph(doc, `Beds / baths: ${property.bedrooms} / ${property.bathrooms}`, y)
  y = paragraph(doc, `Sq ft: ${property.sqft}`, y)
  y = paragraph(doc, `Listing price: ${formatCurrency(property.listing_price)}`, y)
  y = paragraph(
    doc,
    `Saved: ${property.created_at ? new Date(property.created_at).toLocaleString('en-US') : '—'}`,
    y
  )

  const a = property.analysis
  const v = a?.valuation
  if (v) {
    y = heading(doc, 'Valuation', y)
    y = paragraph(doc, `Predicted: ${formatCurrency(v.predicted_price)}`, y)
    if (v.price_low != null && v.price_high != null) {
      y = paragraph(
        doc,
        `Range: ${formatCurrency(v.price_low)} – ${formatCurrency(v.price_high)}`,
        y
      )
    }
    y = paragraph(doc, `Market: ${formatCurrency(v.market_price)}`, y)
    y = paragraph(doc, `Difference: ${formatPercent(v.price_difference_pct)}`, y)
  }

  const inv = a?.investment_analysis
  if (inv) {
    y = heading(doc, 'Investment analysis', y)
    y = paragraph(doc, `Deal label: ${inv.deal_label ?? '—'}`, y)
    y = paragraph(
      doc,
      `Score: ${inv.investment_score != null ? `${inv.investment_score}/100` : '—'}`,
      y
    )
    y = paragraph(doc, `ROI estimate: ${formatPercent(inv.roi_estimate)}`, y)
    if (inv.recommendation) {
      y = paragraph(doc, `Recommendation: ${inv.recommendation}`, y)
    }
    if (inv.analysis_summary) {
      y = paragraph(doc, inv.analysis_summary, y)
    }
  }

  const exp = a?.explanation
  if (exp && (exp.summary || exp.opportunity || exp.risks)) {
    y = heading(doc, 'AI narrative', y)
    if (exp.summary) {
      y = paragraph(doc, `Summary: ${exp.summary}`, y)
    }
    if (exp.opportunity) {
      y = paragraph(doc, `Opportunity: ${exp.opportunity}`, y)
    }
    if (exp.risks) {
      y = paragraph(doc, `Risks: ${exp.risks}`, y)
    }
  }

  y = ensureY(doc, y + 4)
  doc.setFontSize(8)
  doc.setTextColor(100)
  doc.text(`Generated ${new Date().toLocaleString('en-US')}`, MARGIN, y)

  doc.save(`propintel-report-${property.id}.pdf`)
}
