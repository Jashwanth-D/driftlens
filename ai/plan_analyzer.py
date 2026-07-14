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
        model="llama-3.3-70b-versatile",
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

if __name__ == "__main__":
    print("=" * 60)
    print("DriftLens AI Plan Analyzer")
    print("=" * 60)

    for name, plan in [("Safe Deployment", scenario1), ("Risky Destroy+Recreate", scenario2)]:
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