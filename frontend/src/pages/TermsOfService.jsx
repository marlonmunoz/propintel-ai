import { Link } from 'react-router-dom'
import LegalPageShell, { LegalH2, LegalP, LegalUl } from '../components/LegalPageShell'

export default function TermsOfService() {
  return (
    <LegalPageShell title="Terms of Service" lastUpdated="May 5, 2026">
      <LegalP>
        These Terms of Service (&ldquo;Terms&rdquo;) govern your use of the websites, applications, and
        services offered by PropIntel AI LLC (&ldquo;PropIntel,&rdquo; &ldquo;we,&rdquo; &ldquo;us&rdquo;)
        (collectively, the &ldquo;Service&rdquo;). By accessing or using the Service, you agree to these
        Terms. If you do not agree, do not use the Service.
      </LegalP>
      <div>
        <LegalH2>Not professional advice</LegalH2>
        <LegalP>
          The Service provides informational tools, estimates, and narratives derived from data models and
          artificial intelligence. Nothing on the Service is{' '}
          <strong>
            financial, investment, legal, tax, accounting, insurance, or real estate brokerage advice
          </strong>
          , and nothing constitutes an appraisal, comparative market analysis prepared by a licensed
          appraiser, or an offer to buy, sell, lease, or finance property. You should consult qualified
          professionals before making decisions.
        </LegalP>
      </div>
      <div>
        <LegalH2>No fiduciary relationship</LegalH2>
        <LegalP>
          Using the Service does not create a fiduciary, agency, broker-client, appraiser-client, or other
          professional relationship between you and PropIntel.
        </LegalP>
      </div>
      <div>
        <LegalH2>Accounts & eligibility</LegalH2>
        <LegalP>
          You must provide accurate registration information and safeguard your credentials. You are
          responsible for activity under your account. We may suspend or terminate accounts that violate
          these Terms or harm the Service or other users.
        </LegalP>
      </div>
      <div>
        <LegalH2>Acceptable use</LegalH2>
        <LegalUl>
          <li>Do not misuse, probe, or attempt to breach the Service or other users&rsquo; data.</li>
          <li>Do not use the Service in violation of law or third-party rights.</li>
          <li>Do not reverse engineer or scrape the Service except as allowed by law.</li>
        </LegalUl>
      </div>
      <div>
        <LegalH2>AI & data limitations</LegalH2>
        <LegalP>
          Outputs may be incomplete, outdated, or incorrect. Models can &ldquo;hallucinate&rdquo; or
          misinterpret inputs. See also our{' '}
          <Link to="/disclaimer" className="font-medium text-cyan-600 underline hover:text-cyan-500 dark:text-cyan-400">
            Valuation &amp; AI disclaimer
          </Link>
          .
        </LegalP>
      </div>
      <div>
        <LegalH2>Fees & changes</LegalH2>
        <LegalP>
          We may offer free and paid features. If we charge fees, we will describe them before you
          commit. We may change or discontinue features of the Service; where required, we will provide
          notice.
        </LegalP>
      </div>
      <div>
        <LegalH2>Disclaimers</LegalH2>
        <LegalP>
          THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; AND &ldquo;AS AVAILABLE,&rdquo; WITHOUT WARRANTIES
          OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR
          PURPOSE, AND NON-INFRINGEMENT, TO THE FULLEST EXTENT PERMITTED BY LAW.
        </LegalP>
      </div>
      <div>
        <LegalH2>Limitation of liability</LegalH2>
        <LegalP>
          TO THE FULLEST EXTENT PERMITTED BY LAW, PROPINTEL AND ITS AFFILIATES, OFFICERS, DIRECTORS,
          EMPLOYEES, AND AGENTS WILL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
          OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA, OR GOODWILL, ARISING FROM YOUR USE OF THE
          SERVICE. OUR AGGREGATE LIABILITY FOR ANY CLAIM RELATING TO THE SERVICE WILL NOT EXCEED THE
          GREATER OF (A) THE AMOUNT YOU PAID US FOR THE SERVICE IN THE TWELVE (12) MONTHS BEFORE THE CLAIM
          OR (B) ONE HUNDRED U.S. DOLLARS (US$100), EXCEPT WHERE PROHIBITED BY LAW.
        </LegalP>
      </div>
      <div>
        <LegalH2>Indemnity</LegalH2>
        <LegalP>
          You will defend and indemnify PropIntel against claims, damages, and expenses (including
          reasonable attorneys&rsquo; fees) arising from your misuse of the Service or violation of these
          Terms, to the extent permitted by law.
        </LegalP>
      </div>
      <div>
        <LegalH2>Governing law</LegalH2>
        <LegalP>
          These Terms are governed by the laws of the State of New York, without regard to conflict-of-law
          rules, except where superseded by mandatory consumer protections in your jurisdiction.
        </LegalP>
      </div>
      <div>
        <LegalH2>Contact</LegalH2>
        <LegalP>
          Questions about these Terms: use the contact method listed on our website or your account
          correspondence. (Update this paragraph with a legal/contact inbox before launch.)
        </LegalP>
      </div>
    </LegalPageShell>
  )
}
