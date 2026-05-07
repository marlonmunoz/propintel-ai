import { Link } from 'react-router-dom'
import LegalPageShell, { LegalH2, LegalP, LegalUl } from '../components/LegalPageShell'
import SupportLink from '../components/SupportLink'

export default function PrivacyPolicy() {
  return (
    <LegalPageShell title="Privacy Policy" lastUpdated="May 5, 2026">
      <LegalP>
        This Privacy Policy describes how PropIntel AI LLC (&ldquo;PropIntel,&rdquo; &ldquo;we,&rdquo;
        &ldquo;us&rdquo;) collects, uses, and shares information when you use our websites and services
        (the &ldquo;Service&rdquo;). By using the Service, you agree to this Policy alongside our{' '}
        <Link to="/terms" className="font-medium text-cyan-600 underline hover:text-cyan-500 dark:text-cyan-400">
          Terms of Service
        </Link>
        .
      </LegalP>
      <div>
        <LegalH2>Information we collect</LegalH2>
        <LegalUl>
          <li>
            <strong>Account data:</strong> email address, password (stored hashed by our authentication
            provider), optional display name, and preferences you provide (e.g. marketing opt-in).
          </li>
          <li>
            <strong>Usage &amp; technical data:</strong> IP address, device/browser type, approximate
            location inferred from IP, pages viewed, and diagnostic or error data if you enable
            error reporting.
          </li>
          <li>
            <strong>Property &amp; analysis inputs:</strong> information you enter for analyses (e.g.
            address search, property attributes, market price) and outputs we return to you, including
            when you save items to a portfolio.
          </li>
        </LegalUl>
      </div>
      <div>
        <LegalH2>How we use information</LegalH2>
        <LegalUl>
          <li>Provide, secure, and improve the Service.</li>
          <li>Authenticate users and enforce quotas or subscription tiers.</li>
          <li>Communicate with you about the Service (e.g. security, support, product updates if you opt in).</li>
          <li>Comply with law and protect rights, safety, and integrity of users and the Service.</li>
        </LegalUl>
      </div>
      <div>
        <LegalH2>Service providers</LegalH2>
        <LegalP>
          We use third-party infrastructure and tools that process data on our behalf, which may include
          hosting (e.g. frontend and API hosts), database and authentication (e.g. Supabase), AI model
          providers for narrative explanations (e.g. OpenAI), mapping/geocoding (e.g. Mapbox), and error
          monitoring (e.g. Sentry) if enabled. Their use of data is governed by their respective policies
          and our agreements with them.
        </LegalP>
      </div>
      <div>
        <LegalH2>Cookies &amp; local storage</LegalH2>
        <LegalP>
          We and our vendors may use cookies, local storage, or similar technologies for session
          management, preferences, security, and analytics. You can control many cookies through your
          browser settings.
        </LegalP>
      </div>
      <div>
        <LegalH2>Retention</LegalH2>
        <LegalP>
          We retain information as long as needed to operate the Service, comply with legal obligations,
          resolve disputes, and enforce agreements. Retention periods may vary by data category.
        </LegalP>
      </div>
      <div>
        <LegalH2>Security</LegalH2>
        <LegalP>
          We implement reasonable technical and organizational measures to protect information. No method
          of transmission or storage is 100% secure.
        </LegalP>
      </div>
      <div>
        <LegalH2>Your choices</LegalH2>
        <LegalUl>
          <li>Access or update certain account information through in-product settings where available.</li>
          <li>Opt out of marketing emails using the unsubscribe link or settings.</li>
          <li>
            Request deletion or export of personal information where applicable law provides such rights;
            contact us as described below.
          </li>
        </LegalUl>
      </div>
      <div>
        <LegalH2>Children</LegalH2>
        <LegalP>The Service is not directed to children under 13, and we do not knowingly collect their personal information.</LegalP>
      </div>
      <div>
        <LegalH2>Changes</LegalH2>
        <LegalP>
          We may update this Policy from time to time. We will post the updated Policy with a new
          &ldquo;Last updated&rdquo; date and, where appropriate, provide additional notice.
        </LegalP>
      </div>
      <div>
        <LegalH2>Contact</LegalH2>
        <LegalP>
          For privacy inquiries, data access, deletion, or export requests, email{' '}
          <SupportLink subject="Privacy inquiry" /> from your registered address. We will respond within
          a reasonable time, subject to applicable law.
        </LegalP>
      </div>
    </LegalPageShell>
  )
}
