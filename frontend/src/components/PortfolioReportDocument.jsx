/**
 * Print-oriented report layout for a saved portfolio property.
 * Renders light theme only — suitable for iframe print and PDF-style reference.
 */
function formatCurrency(value) {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatPercent(value) {
  if (value == null) return '—'
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export default function PortfolioReportDocument({ property }) {
  const a = property?.analysis
  const valuation = a?.valuation
  const inv = a?.investment_analysis
  const exp = a?.explanation
  const saved =
    property.created_at != null
      ? new Date(property.created_at).toLocaleString('en-US', {
          dateStyle: 'long',
          timeStyle: 'short',
        })
      : '—'

  return (
    <article className="portfolio-report-doc text-slate-900">
      <header className="mb-6 border-b border-slate-200 pb-4">
        <h1 className="text-xl font-bold tracking-tight">PropIntel AI</h1>
        <p className="mt-1 text-sm font-medium text-slate-600">Saved analysis report</p>
        <p className="mt-3 text-xs leading-relaxed text-slate-500">
          Estimates are for education and decision support only — not financial, legal, or investment
          advice.
        </p>
      </header>

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-700">Property</h2>
        <table className="w-full text-sm">
          <tbody className="align-top">
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Record ID</td>
              <td className="py-1">{property.id}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Address</td>
              <td className="py-1 font-semibold">{property.address}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">ZIP</td>
              <td className="py-1">{property.zipcode}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Beds / baths</td>
              <td className="py-1">
                {property.bedrooms} / {property.bathrooms}
              </td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Sq ft</td>
              <td className="py-1">{property.sqft?.toLocaleString?.() ?? property.sqft}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Listing price</td>
              <td className="py-1">{formatCurrency(property.listing_price)}</td>
            </tr>
            <tr>
              <td className="py-1 pr-4 font-medium text-slate-600">Saved</td>
              <td className="py-1">{saved}</td>
            </tr>
          </tbody>
        </table>
      </section>

      {valuation && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-700">Valuation</h2>
          <table className="w-full text-sm">
            <tbody>
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">Predicted</td>
                <td className="py-1 font-semibold">{formatCurrency(valuation.predicted_price)}</td>
              </tr>
              {valuation.price_low != null && valuation.price_high != null && (
                <tr>
                  <td className="py-1 pr-4 font-medium text-slate-600">Range</td>
                  <td className="py-1">
                    {formatCurrency(valuation.price_low)} – {formatCurrency(valuation.price_high)}
                  </td>
                </tr>
              )}
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">Market (comparable)</td>
                <td className="py-1">{formatCurrency(valuation.market_price)}</td>
              </tr>
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">Difference</td>
                <td className="py-1">{formatPercent(valuation.price_difference_pct)}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      {inv && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-700">
            Investment analysis
          </h2>
          <table className="mb-3 w-full text-sm">
            <tbody>
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">Deal label</td>
                <td className="py-1 font-semibold uppercase">{inv.deal_label ?? '—'}</td>
              </tr>
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">Score</td>
                <td className="py-1">
                  {inv.investment_score != null ? `${inv.investment_score}/100` : '—'}
                </td>
              </tr>
              <tr>
                <td className="py-1 pr-4 font-medium text-slate-600">ROI estimate</td>
                <td className="py-1">{formatPercent(inv.roi_estimate)}</td>
              </tr>
            </tbody>
          </table>
          {inv.recommendation && (
            <div className="mb-3 text-sm leading-relaxed">
              <span className="font-semibold">Recommendation: </span>
              {inv.recommendation}
            </div>
          )}
          {inv.analysis_summary && (
            <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">
              {inv.analysis_summary}
            </p>
          )}
        </section>
      )}

      {exp && (exp.summary || exp.opportunity || exp.risks) && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-700">AI narrative</h2>
          <div className="space-y-4 text-sm leading-relaxed text-slate-700">
            {exp.summary && (
              <div>
                <p className="mb-1 text-xs font-bold uppercase text-slate-500">Summary</p>
                <p className="whitespace-pre-wrap">{exp.summary}</p>
              </div>
            )}
            {exp.opportunity && (
              <div>
                <p className="mb-1 text-xs font-bold uppercase text-slate-500">Opportunity</p>
                <p className="whitespace-pre-wrap">{exp.opportunity}</p>
              </div>
            )}
            {exp.risks && (
              <div>
                <p className="mb-1 text-xs font-bold uppercase text-slate-500">Risks</p>
                <p className="whitespace-pre-wrap">{exp.risks}</p>
              </div>
            )}
          </div>
        </section>
      )}

      <footer className="mt-8 border-t border-slate-200 pt-4 text-center text-xs text-slate-500">
        Generated by PropIntel AI · {new Date().toLocaleString('en-US')}
      </footer>
    </article>
  )
}
