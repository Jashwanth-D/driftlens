import os
import json
from groq import Groq
from pydantic import BaseModel
from typing import Literal

class AiDecision(BaseModel):
    decision: Literal["PROCEED", "HOLD", "BLOCK"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    summary: str
    reasons: list[str]

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def analyze_plan(scenario_name: str, plan_text: str) -> AiDecision:
    prompt = f"""You are a cloud infrastructure AI reviewer for DriftLens.
Analyze this Terraform plan and return a JSON decision.

Scenario: {scenario_name}

Terraform Plan:
{plan_text}

Return ONLY valid JSON with these fields:
- decision: "PROCEED" or "HOLD" or "BLOCK"
- risk_level: "LOW" or "MEDIUM" or "HIGH"
- summary: one sentence summary
- reasons: list of 2-3 short reasons

Example:
{{"decision": "PROCEED", "risk_level": "LOW", "summary": "Safe to deploy.", "reasons": ["No destructive changes", "Resources properly tagged"]}}
"""
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    text = response.choices[0].message.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    data = json.loads(text)
    return AiDecision(**data)

scenario1 = """
Plan: 5 to add, 0 to change, 0 to destroy.

  + aws_s3_bucket.site (bucket = "psiddhi-jashwanth-site", tags = {project = "pSiddhi-2026-01", owner = "jashwanth.dhanasekaran"})
  + aws_s3_bucket_website_configuration.site
  + aws_s3_bucket_public_access_block.site
  + aws_s3_bucket_policy.site (public read)
  + aws_cloudfront_distribution.site (enabled = true)
"""

scenario2 = """
Plan: 1 to add, 0 to change, 3 to destroy.

  - aws_s3_bucket_policy.site (DESTROY)
  - aws_s3_bucket.site (DESTROY — contains 150 objects)
  - aws_cloudfront_distribution.site (DESTROY)
  + aws_s3_bucket.site (new bucket name, no tags, no versioning)
"""


scenario3 = """
Plan: 2 to add, 0 to change, 2 to destroy.

  - azurerm_storage_blob.index (DESTROY - moving content to AWS)
  - azurerm_storage_account.site (DESTROY - decommissioning Azure static site)
  + aws_s3_bucket.migrated_site (bucket = "psiddhi-jashwanth-migrated", tags = {project = "pSiddhi-2026-01"})
  + aws_s3_bucket_website_configuration.migrated_site (index_document = "index.html")

Context: Cross-cloud migration - moving static website from Azure Storage to AWS S3.
Tradeoffs: Azure CDN latency in India (~15ms) vs CloudFront global (~50ms from India).
Cost: Azure Storage ~$0.02/GB vs S3 ~$0.023/GB. Negligible at demo scale.
"""

scenario4 = """
Plan: 0 to add, 1 to change, 0 to destroy.

  ~ aws_cloudfront_distribution.site
    - default_root_object = "index.html" -> null (REMOVING default root)
    ~ origin.custom_origin_config.origin_protocol_policy: "http-only" -> "https-only"
    ~ viewer_certificate.minimum_protocol_version: "TLSv1.2" -> "TLSv1" (DOWNGRADE)
    ~ default_cache_behavior.min_ttl: 0 -> 86400 (forcing 24h cache)

Context: In-place CDN configuration change with downtime risk.
Risk: Removing default_root_object breaks all bare-domain requests (404).
Risk: TLS downgrade from 1.2 to 1.0 introduces known vulnerabilities.
Risk: 24h forced cache means fixes take a full day to propagate.
"""

if __name__ == "__main__":
    print("=" * 60)
    print("DriftLens AI Plan Analyzer")
    print("=" * 60)

    for name, plan in [("Safe Deployment", scenario1), ("Risky Destroy+Recreate", scenario2), ("Cross-Cloud Migration", scenario3), ("CDN Config Change with Downtime Risk", scenario4)]:
        print(f"\n--- Scenario: {name} ---")
        try:
            result = analyze_plan(name, plan)
            print(f"Decision : {result.decision}")
            print(f"Risk     : {result.risk_level}")
            print(f"Summary  : {result.summary}")
            print(f"Reasons  :")
            for r in result.reasons:
                print(f"  - {r}")
        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("Analysis complete.")