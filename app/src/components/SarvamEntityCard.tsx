/**
 * SarvamEntityCard
 * Displays extracted entities from Sarvam AI with a branded badge header.
 * Shows job_title, location, company, email, phone, URL, salary, fee,
 * red flags, and the detected language.
 */

import React from "react";
import "./SarvamEntityCard.css";

// ---- Types ----------------------------------------------------------------

export interface ExtractedEntities {
  company_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
  website_url?: string | null;
  recruiter_name?: string | null;
  job_title?: string | null;
  location?: string | null;
  salary_mentioned?: number | null;
  fee_amount?: number | null;
  urgency_indicators?: boolean;
  personal_email_for_corp_contact?: boolean;
  language_detected?: string;
  red_flags?: string[];
}

interface Props {
  entities: ExtractedEntities;
  /** Whether Sarvam AI was actually used or the regex fallback ran */
  usedFallback?: boolean;
}

// ---- Helpers ---------------------------------------------------------------

const LANG_LABELS: Record<string, string> = {
  english:   "English",
  hindi:     "हिन्दी",
  hinglish:  "Hinglish",
  tamil:     "தமிழ்",
  telugu:    "తెలుగు",
  kannada:   "ಕನ್ನಡ",
  bengali:   "বাংলা",
  marathi:   "मराठी",
  gujarati:  "ગુજરાતી",
  malayalam: "മലയാളം",
  punjabi:   "ਪੰਜਾਬੀ",
  odia:      "ଓଡ଼ିଆ",
};

function formatINR(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style:    "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

// ---- Sub-components -------------------------------------------------------

function EntityRow({
  icon,
  label,
  value,
  danger,
}: {
  icon: string;
  label: string;
  value: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <div className="sarvam-entity-row">
      <span className="sarvam-entity-icon" aria-hidden="true">{icon}</span>
      <span className="sarvam-entity-label">{label}</span>
      <span className={`sarvam-entity-value${danger ? " sarvam-entity-danger" : ""}`}>
        {value}
      </span>
    </div>
  );
}

// ---- Main component -------------------------------------------------------

export const SarvamEntityCard: React.FC<Props> = ({
  entities,
  usedFallback = false,
}) => {
  const lang      = entities.language_detected ?? "english";
  const langLabel = LANG_LABELS[lang] ?? lang;
  const redFlags  = entities.red_flags ?? [];

  const hasData =
    entities.company_name  ||
    entities.email         ||
    entities.phone_number  ||
    entities.website_url   ||
    entities.job_title     ||
    entities.location      ||
    entities.salary_mentioned != null ||
    entities.fee_amount != null;

  return (
    <div className="sarvam-card" role="region" aria-label="Sarvam AI Entity Extraction">
      {/* ── Header ── */}
      <div className="sarvam-card-header">
        <div className="sarvam-badge-row">
          {/* Sarvam AI brand badge */}
          <span className="sarvam-badge" title="Powered by Sarvam AI">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"
              aria-hidden="true" style={{ marginRight: "6px" }}>
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            Sarvam AI
          </span>

          {/* Language badge */}
          <span className="sarvam-lang-badge" title={`Language: ${langLabel}`}>
            🌐 {langLabel}
          </span>

          {/* Fallback badge */}
          {usedFallback && (
            <span className="sarvam-fallback-badge" title="Real-time regex extraction (API unavailable)">
              ⚡ Regex Fallback
            </span>
          )}
        </div>

        <h3 className="sarvam-card-title">Entity Extraction</h3>
      </div>

      {/* ── Body ── */}
      <div className="sarvam-card-body">
        {!hasData ? (
          <p className="sarvam-empty">No entities detected in this text.</p>
        ) : (
          <div className="sarvam-entity-list">
            {entities.company_name   && <EntityRow icon="🏢" label="Company"   value={entities.company_name} />}
            {entities.job_title      && <EntityRow icon="💼" label="Job Title" value={entities.job_title} />}
            {entities.location       && <EntityRow icon="📍" label="Location"  value={entities.location} />}
            {entities.recruiter_name && <EntityRow icon="👤" label="Recruiter" value={entities.recruiter_name} />}

            {entities.email && (
              <EntityRow
                icon="📧"
                label="Email"
                value={<a href={`mailto:${entities.email}`} className="sarvam-link">{entities.email}</a>}
                danger={entities.personal_email_for_corp_contact}
              />
            )}

            {entities.phone_number && (
              <EntityRow
                icon="📞"
                label="Phone"
                value={<a href={`tel:${entities.phone_number}`} className="sarvam-link">{entities.phone_number}</a>}
              />
            )}

            {entities.website_url && (
              <EntityRow
                icon="🌐"
                label="Website"
                value={
                  <a
                    href={entities.website_url.startsWith("http") ? entities.website_url : `https://${entities.website_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="sarvam-link"
                  >
                    {entities.website_url}
                  </a>
                }
              />
            )}

            {entities.salary_mentioned != null && (
              <EntityRow icon="💰" label="Salary (Monthly)" value={formatINR(entities.salary_mentioned)} />
            )}

            {entities.fee_amount != null && (
              <EntityRow
                icon="⚠️"
                label="Fee Requested"
                value={formatINR(entities.fee_amount)}
                danger
              />
            )}
          </div>
        )}

        {/* ── Red flags ── */}
        {redFlags.length > 0 && (
          <div className="sarvam-red-flags">
            <h4 className="sarvam-red-flags-title">🚩 Red Flags Detected</h4>
            <ul className="sarvam-red-flags-list">
              {redFlags.map((flag, i) => (
                <li key={i} className="sarvam-red-flag-item">{flag}</li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Urgency warning ── */}
        {entities.urgency_indicators && (
          <div className="sarvam-urgency-banner" role="alert">
            ⏰ <strong>Urgency language detected</strong> — Scammers often pressure victims
            to act immediately. Take your time.
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="sarvam-card-footer">
        <span className="sarvam-powered-by">
          Powered by&nbsp;
          <a
            href="https://www.sarvam.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="sarvam-link"
          >
            Sarvam AI
          </a>
          &nbsp;— Indian Language Intelligence
        </span>
      </div>
    </div>
  );
};

export default SarvamEntityCard;
