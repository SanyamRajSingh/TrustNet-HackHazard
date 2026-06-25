"""
TrustNet Trust Engine
5-category weighted scoring + confidence calculation + verdict determination.
"""

from typing import Any, Dict, List, Optional

import structlog

from config import settings

logger = structlog.get_logger()

VERDICT_CONFIG = {
    "HIGH_RISK": {
        "label": "DO NOT RESPOND",
        "color": "#DC2626",
        "bg_color": "#FEF2F2",
        "description": "This offer shows strong scam indicators. Do not engage or pay.",
    },
    "SUSPICIOUS": {
        "label": "PROCEED WITH EXTREME CAUTION",
        "color": "#D97706",
        "bg_color": "#FFFBEB",
        "description": "Multiple warning signs detected. Verify independently before proceeding.",
    },
    "UNVERIFIED": {
        "label": "INSUFFICIENT VERIFICATION",
        "color": "#CA8A04",
        "bg_color": "#FEFCE8",
        "description": "Not enough data to verify. Research the company independently.",
    },
    "LIKELY_LEGITIMATE": {
        "label": "LIKELY SAFE — VERIFY FURTHER",
        "color": "#2563EB",
        "bg_color": "#EFF6FF",
        "description": "Signals look positive, but always verify independently.",
    },
    "VERIFIED": {
        "label": "SIGNALS PASS — VERIFY INDEPENDENTLY",
        "color": "#16A34A",
        "bg_color": "#F0FDF4",
        "description": "Company checks out. Still verify offer details independently.",
    },
    "INSUFFICIENT_DATA": {
        "label": "NOT ENOUGH DATA TO SCORE",
        "color": "#64748B",
        "bg_color": "#F8FAFC",
        "description": "Could not gather enough information. Try with more details.",
    },
}


class TrustEngine:
    """
    Core trust scoring engine.
    Combines 5 category scores into weighted trust score with confidence.
    """

    def __init__(self):
        self.weights = {
            "identity_company": settings.WEIGHT_IDENTITY,
            "domain_infrastructure": settings.WEIGHT_DOMAIN,
            "communication_channel": settings.WEIGHT_COMMUNICATION,
            "content_red_flags": settings.WEIGHT_CONTENT,
            "community_intelligence": settings.WEIGHT_COMMUNITY,
        }
        self.confidence_points = {
            "company_found": settings.CONFIDENCE_COMPANY_FOUND,
            "whois_data": settings.CONFIDENCE_WHOIS,
            "dns_records": settings.CONFIDENCE_DNS,
            "sarvam_extraction": settings.CONFIDENCE_SARVAM,
            "community_reports": settings.CONFIDENCE_COMMUNITY,
            "phone_verified": settings.CONFIDENCE_PHONE,
            "email_auth": settings.CONFIDENCE_EMAIL_AUTH,
        }

    def calculate(
        self,
        category_results: Dict[str, Any],
        data_availability: Dict[str, bool],
    ) -> Dict[str, Any]:
        """
        Main calculation method.
        
        Args:
            category_results: Dict with scores for each of 5 categories
            data_availability: Dict indicating which data points were available
        
        Returns:
            Complete trust analysis result
        """
        # 1. Calculate confidence score
        confidence_score = self._calculate_confidence(data_availability)

        # 2. Calculate category scores
        identity_score = category_results.get("identity_company", {}).get("score", 0)
        domain_score = category_results.get("domain_infrastructure", {}).get("score", 0)
        comm_score = category_results.get("communication_channel", {}).get("score", 0)
        content_score = category_results.get("content_red_flags", {}).get("score", 0)
        community_score = category_results.get("community_intelligence", {}).get("score", 0)

        # 3. Apply confidence multiplier
        max_possible = sum(self.confidence_points.values())
        available = sum(
            v for k, v in self.confidence_points.items() if data_availability.get(k, False)
        )
        confidence_multiplier = max(0.5, available / max_possible) if max_possible > 0 else 0.5

        # 4. Weighted trust score
        raw_score = (
            identity_score * self.weights["identity_company"] +
            domain_score * self.weights["domain_infrastructure"] +
            comm_score * self.weights["communication_channel"] +
            content_score * self.weights["content_red_flags"] +
            community_score * self.weights["community_intelligence"]
        )
        trust_score = int(raw_score * confidence_multiplier)
        trust_score = max(0, min(100, trust_score))

        # 5. Determine verdict
        verdict = self._determine_verdict(trust_score, confidence_score)

        # 6. Build category breakdown
        category_breakdown = {
            "identity_company": {
                "score": identity_score,
                "weight": self.weights["identity_company"],
                "weighted_score": round(identity_score * self.weights["identity_company"], 2),
                "evidence": category_results.get("identity_company", {}).get("evidence", []),
            },
            "domain_infrastructure": {
                "score": domain_score,
                "weight": self.weights["domain_infrastructure"],
                "weighted_score": round(domain_score * self.weights["domain_infrastructure"], 2),
                "evidence": category_results.get("domain_infrastructure", {}).get("evidence", []),
            },
            "communication_channel": {
                "score": comm_score,
                "weight": self.weights["communication_channel"],
                "weighted_score": round(comm_score * self.weights["communication_channel"], 2),
                "evidence": category_results.get("communication_channel", {}).get("evidence", []),
            },
            "content_red_flags": {
                "score": content_score,
                "weight": self.weights["content_red_flags"],
                "weighted_score": round(content_score * self.weights["content_red_flags"], 2),
                "evidence": category_results.get("content_red_flags", {}).get("evidence", []),
            },
            "community_intelligence": {
                "score": community_score,
                "weight": self.weights["community_intelligence"],
                "weighted_score": round(community_score * self.weights["community_intelligence"], 2),
                "evidence": category_results.get("community_intelligence", {}).get("evidence", []),
            },
        }

        # 7. Compile evidence list
        evidence = self._compile_evidence(category_results)

        verdict_config = VERDICT_CONFIG.get(verdict, VERDICT_CONFIG["INSUFFICIENT_DATA"])

        result = {
            "trust_score": trust_score,
            "confidence_score": confidence_score,
            "confidence_multiplier": round(confidence_multiplier, 2),
            "verdict": verdict,
            "verdict_label": verdict_config["label"],
            "verdict_color": verdict_config["color"],
            "verdict_bg_color": verdict_config["bg_color"],
            "verdict_description": verdict_config["description"],
            "category_scores": category_breakdown,
            "evidence": evidence,
        }

        logger.info("trust_engine.calculated",
                    trust_score=trust_score,
                    confidence=confidence_score,
                    verdict=verdict)

        return result

    def _calculate_confidence(self, data_availability: Dict[str, bool]) -> int:
        """Calculate confidence score based on available data sources."""
        confidence = 0
        for key, points in self.confidence_points.items():
            if data_availability.get(key, False):
                confidence += points
        return min(100, confidence)

    def _determine_verdict(self, trust_score: int, confidence_score: int) -> str:
        """
        Determine verdict from trust score and confidence.
        
        Thresholds:
        - < 25 + any confidence: HIGH_RISK
        - 25-44 + confidence >= 25%: SUSPICIOUS
        - 45-64 + confidence >= 25%: UNVERIFIED
        - 65-79 + confidence >= 50%: LIKELY_LEGITIMATE
        - >= 80 + confidence >= 60%: VERIFIED
        - Any + confidence < 25%: INSUFFICIENT_DATA
        """
        if confidence_score < settings.CONFIDENCE_THRESHOLD:
            return "INSUFFICIENT_DATA"
        
        if trust_score < settings.THRESHOLD_HIGH_RISK:
            return "HIGH_RISK"
        elif trust_score < settings.THRESHOLD_SUSPICIOUS:
            return "SUSPICIOUS"
        elif trust_score < settings.THRESHOLD_UNVERIFIED:
            return "UNVERIFIED"
        elif trust_score < settings.THRESHOLD_LIKELY_LEGITIMATE:
            if confidence_score >= 50:
                return "LIKELY_LEGITIMATE"
            return "UNVERIFIED"
        else:
            if confidence_score >= 60:
                return "VERIFIED"
            return "LIKELY_LEGITIMATE"

    def _compile_evidence(self, category_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Compile all evidence from category results into flat list."""
        evidence = []
        for category, data in category_results.items():
            for item in data.get("evidence", []):
                evidence.append({
                    "category": category.replace("_", " ").title(),
                    "finding": item.get("finding", ""),
                    "severity": item.get("severity", "info"),
                    "details": item.get("details", ""),
                })
        return sorted(evidence, key=lambda x: ["critical", "warning", "info", "positive"].index(x["severity"]) if x["severity"] in ["critical", "warning", "info", "positive"] else 2)


class CategoryScorer:
    """Individual category scoring functions."""

    @staticmethod
    def score_identity_company(mca_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score Identity & Company Verification category.
        MCA registration, company age, CIN validity.
        """
        score = 0
        evidence = []

        if not mca_result.get("found"):
            score = 20
            evidence.append({
                "finding": "Company not found in MCA records",
                "severity": "warning",
                "details": "The company name could not be verified against Ministry of Corporate Affairs database",
            })
        else:
            score = 50  # Base for found company
            evidence.append({
                "finding": f"Company found: {mca_result.get('company_name', '')}",
                "severity": "positive",
                "details": f"CIN: {mca_result.get('cin', 'N/A')}",
            })

            # Status
            status = mca_result.get("status", "").lower()
            if status == "active":
                score += 25
                evidence.append({
                    "finding": "Company status is Active",
                    "severity": "positive",
                })
            elif status in ["dormant", "under process"]:
                score += 5
                evidence.append({
                    "finding": f"Company status: {status.title()}",
                    "severity": "warning",
                })
            elif status in ["strike off", "dissolved"]:
                score -= 30
                evidence.append({
                    "finding": f"Company is {status}",
                    "severity": "critical",
                    "details": "This company is no longer active",
                })

            # Age
            age = mca_result.get("age_years")
            if age:
                if age > 20:
                    score += 25
                    evidence.append({
                        "finding": f"Established company ({age} years)",
                        "severity": "positive",
                    })
                elif age > 10:
                    score += 15
                    evidence.append({
                        "finding": f"Company operating for {age} years",
                        "severity": "positive",
                    })
                elif age > 2:
                    score += 5
                    evidence.append({
                        "finding": f"Relatively new company ({age} years)",
                        "severity": "info",
                    })
                else:
                    evidence.append({
                        "finding": f"Very new company ({age} years)",
                        "severity": "warning",
                    })

        return {"score": min(100, max(0, score)), "evidence": evidence}

    @staticmethod
    def score_domain_infrastructure(
        whois_data: Dict[str, Any],
        safe_browsing: Dict[str, Any],
        phishtank: Dict[str, Any],
        urlhaus: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Score Domain & Infrastructure Intelligence category.
        WHOIS age, blacklist status, DNS integrity.
        """
        score = 50
        evidence = []

        # WHOIS data
        if whois_data.get("found"):
            age_days = whois_data.get("age_days")
            if age_days is not None:
                if age_days < 30:
                    score = 5
                    evidence.append({
                        "finding": f"Domain registered only {age_days} days ago",
                        "severity": "critical",
                        "details": "Very new domains are commonly used for scams",
                    })
                elif age_days < 90:
                    score = 20
                    evidence.append({
                        "finding": f"Domain is {age_days} days old",
                        "severity": "warning",
                        "details": "Recently registered domain",
                    })
                elif age_days < 365:
                    score = 45
                    evidence.append({
                        "finding": f"Domain less than 1 year old ({age_days} days)",
                        "severity": "info",
                    })
                elif age_days < 3 * 365:
                    score = 60
                    evidence.append({
                        "finding": f"Domain established ({age_days // 365} years)",
                        "severity": "positive",
                    })
                else:
                    score = 90
                    evidence.append({
                        "finding": f"Well-established domain ({age_days // 365}+ years)",
                        "severity": "positive",
                    })

            # Privacy protection
            if whois_data.get("has_privacy_protection"):
                evidence.append({
                    "finding": "Domain uses privacy protection",
                    "severity": "info",
                    "details": "WHOIS data is hidden",
                })
        else:
            score = 30
            evidence.append({
                "finding": "Could not retrieve domain information",
                "severity": "warning",
            })

        # Blacklist checks
        if safe_browsing.get("flagged"):
            score = 0
            evidence.append({
                "finding": "Domain flagged by Google Safe Browsing",
                "severity": "critical",
                "details": f"Threat types: {', '.join(safe_browsing.get('threat_types', []))}",
            })

        if phishtank.get("flagged"):
            score = 0
            evidence.append({
                "finding": "Domain listed in PhishTank database",
                "severity": "critical",
            })

        if urlhaus.get("flagged"):
            score = 0
            evidence.append({
                "finding": "Domain flagged by URLhaus (malware)",
                "severity": "critical",
            })

        if not any([safe_browsing.get("flagged"), phishtank.get("flagged"), urlhaus.get("flagged")]):
            evidence.append({
                "finding": "No blacklist records found",
                "severity": "positive",
            })

        return {"score": min(100, max(0, score)), "evidence": evidence}

    @staticmethod
    def score_communication_channel(
        dns_result: Dict[str, Any],
        email: Optional[str],
    ) -> Dict[str, Any]:
        """
        Score Communication Channel Integrity category.
        Email auth (SPF/DKIM/DMARC), disposable email detection.
        """
        score = 40
        evidence = []

        # Check for personal email
        if email:
            domain = email.split("@")[-1].lower() if "@" in email else ""
            personal_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"]
            if domain in personal_domains:
                score -= 20
                evidence.append({
                    "finding": f"Personal email ({domain}) used for corporate contact",
                    "severity": "warning",
                    "details": "Legitimate companies use their own domain email",
                })
            else:
                score += 15
                evidence.append({
                    "finding": f"Corporate email domain: {domain}",
                    "severity": "positive",
                })

            # DNS auth checks
            if dns_result and dns_result.get("checked"):
                if dns_result.get("spf"):
                    score += 10
                    evidence.append({
                        "finding": "SPF record found",
                        "severity": "positive",
                    })
                else:
                    evidence.append({
                        "finding": "No SPF record",
                        "severity": "warning",
                    })

                if dns_result.get("dkim"):
                    score += 10
                    evidence.append({
                        "finding": "DKIM record found",
                        "severity": "positive",
                    })
                else:
                    evidence.append({
                        "finding": "No DKIM record",
                        "severity": "info",
                    })

                if dns_result.get("dmarc"):
                    score += 15
                    evidence.append({
                        "finding": "DMARC record found",
                        "severity": "positive",
                    })
                else:
                    evidence.append({
                        "finding": "No DMARC record",
                        "severity": "warning",
                    })

                if dns_result.get("overall_auth_pass"):
                    score += 10
                    evidence.append({
                        "finding": "Email authentication checks passed",
                        "severity": "positive",
                    })
            else:
                evidence.append({
                    "finding": "Could not verify email authentication",
                    "severity": "info",
                })
        else:
            evidence.append({
                "finding": "No email to verify",
                "severity": "info",
            })

        return {"score": min(100, max(0, score)), "evidence": evidence}

    @staticmethod
    def score_content_red_flags(
        entities: Dict[str, Any],
        input_text: str,
    ) -> Dict[str, Any]:
        """
        Score Content Analysis & Red Flags category.
        Fee requests, urgency language, salary realism.
        """
        score = 60
        evidence = []

        # Fee detection
        fee = entities.get("fee_amount")
        if fee and fee > 0:
            score -= 40
            evidence.append({
                "finding": f"Registration fee requested: Rs. {fee:,}",
                "severity": "critical",
                "details": "Legitimate employers never charge registration fees",
            })
        else:
            evidence.append({
                "finding": "No fee requested",
                "severity": "positive",
            })

        # Urgency indicators
        if entities.get("urgency_indicators"):
            score -= 20
            evidence.append({
                "finding": "Urgency language detected ('24 hours', 'immediate', etc.)",
                "severity": "warning",
                "details": "Scammers use urgency to pressure victims",
            })

        # Personal email for corporate
        if entities.get("personal_email_for_corp_contact"):
            score -= 15
            evidence.append({
                "finding": "Personal email used for corporate communication",
                "severity": "warning",
            })

        # Red flags from extraction
        red_flags = entities.get("red_flags", [])
        for flag in red_flags:
            if "fee" in flag.lower():
                score -= 10
            evidence.append({
                "finding": flag,
                "severity": "warning",
            })

        # Salary check (unrealistic salary is a flag)
        salary = entities.get("salary_mentioned")
        if salary:
            if salary > 200000:  # > 2L/month is suspicious for entry level
                score -= 10
                evidence.append({
                    "finding": f"Unusually high salary: Rs. {salary:,}/month",
                    "severity": "warning",
                    "details": "Entry-level salaries above 2L/month are rare",
                })
            else:
                evidence.append({
                    "finding": f"Salary mentioned: Rs. {salary:,}/month",
                    "severity": "info",
                })

        return {"score": min(100, max(0, score)), "evidence": evidence}

    @staticmethod
    def score_community_intelligence(
        ring_connections: Dict[str, Any],
        community_reports: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Score Community Intelligence category.
        Graph connections, community reports, ring membership.
        """
        score = 50
        evidence = []

        # Ring connections
        flagged_count = ring_connections.get("flagged_count", 0)
        rings = ring_connections.get("rings", [])

        if rings:
            score -= min(50, flagged_count * 10)
            evidence.append({
                "finding": f"Connected to known scam ring(s): {', '.join(rings)}",
                "severity": "critical",
                "details": f"Found {flagged_count} flagged connections",
            })
        else:
            evidence.append({
                "finding": "No known scam ring connections",
                "severity": "positive",
            })

        # Community reports
        if community_reports:
            scam_reports = [r for r in community_reports if r.get("report_type") == "SCAM"]
            if scam_reports:
                score -= min(40, len(scam_reports) * 10)
                evidence.append({
                    "finding": f"{len(scam_reports)} scam report(s) from community",
                    "severity": "warning",
                })

            legit_reports = [r for r in community_reports if r.get("report_type") == "LEGITIMATE"]
            if legit_reports:
                score += min(20, len(legit_reports) * 5)
                evidence.append({
                    "finding": f"{len(legit_reports)} legitimacy report(s) from community",
                    "severity": "positive",
                })
        else:
            evidence.append({
                "finding": "No community reports yet",
                "severity": "info",
            })

        return {"score": min(100, max(0, score)), "evidence": evidence}