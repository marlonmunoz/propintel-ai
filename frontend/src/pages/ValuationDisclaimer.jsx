import { Link } from 'react-router-dom'
import LegalPageShell, { LegalH2, LegalP, LegalUl } from '../components/LegalPageShell'

/**
 * Standalone disclaimer for valuations / AI outputs — link from Analyze, Terms, and signup.
 */
export default function ValuationDisclaimer() {
  return (
    <LegalPageShell title="Valuation &amp; AI disclaimer" lastUpdated="May 5, 2026">
      <LegalP>
        PropIntel AI provides <strong>informational estimates and narrative summaries</strong> based on
        models, third-party data, and artificial intelligence. Read this carefully before relying on any
        output.
      </LegalP>
      <div>
        <LegalH2>Not financial, legal, tax, or brokerage advice</LegalH2>
        <LegalP>
          Outputs are <strong>not</strong> financial, investment, legal, tax, accounting, insurance, or
          real estate brokerage advice. PropIntel is not your agent, broker, attorney, accountant,
          appraiser, or financial advisor.{' '}
          <strong>Consult licensed professionals</strong> before buying, selling, leasing, financing,
          renovating, or making tax or estate decisions.
        </LegalP>
      </div>
      <div>
        <LegalH2>Not an appraisal or broker price opinion</LegalH2>
        <LegalP>
          Estimates are <strong>not</strong> a certified appraisal, broker price opinion prepared under
          regulatory standards, or a substitute for diligence appropriate to your transaction. They may
          differ materially from market clearing prices, lender valuations, or tax assessments.
        </LegalP>
      </div>
      <div>
        <LegalH2>AI &amp; model limitations</LegalH2>
        <LegalUl>
          <li>
            Models can be wrong, incomplete, or outdated; they may not reflect recent renovations,
            condition, views, noise, zoning changes, or pending litigation.
          </li>
          <li>
            Large language model text can contain errors or plausible-sounding but incorrect statements
            (&ldquo;hallucinations&rdquo;). Treat narratives as <strong>starting points</strong>, not
            conclusions.
          </li>
          <li>
            Training data and neighborhood aggregates may under- or over-represent segments of the market.
          </li>
        </LegalUl>
      </div>
      <div>
        <LegalH2>Your inputs matter</LegalH2>
        <LegalP>
          Accuracy depends on the quality of addresses, attributes, and the &ldquo;market price&rdquo; or
          listing figures you supply. Wrong inputs can produce misleading comparisons even when the math is
          internally consistent.
        </LegalP>
      </div>
      <div>
        <LegalH2>No guarantee</LegalH2>
        <LegalP>
          We do not guarantee any particular investment outcome, valuation range, rental income, cap rate,
          or deal label. Past sales in our datasets do not predict future performance.
        </LegalP>
      </div>
      <div>
        <LegalH2>Related policies</LegalH2>
        <LegalP>
          For broader terms governing use of the Service, see our{' '}
          <Link to="/terms" className="font-medium text-cyan-600 underline hover:text-cyan-500 dark:text-cyan-400">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="font-medium text-cyan-600 underline hover:text-cyan-500 dark:text-cyan-400">
            Privacy Policy
          </Link>
          .
        </LegalP>
      </div>
    </LegalPageShell>
  )
}
