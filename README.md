\# DriftLens



Multi-cloud deployment orchestration platform with AI-powered plan review and drift detection.



\## What It Does



\- Manages infrastructure on AWS and Azure using Terraform

\- AI (Gemini) analyzes Terraform plans and returns structured decisions (PROCEED / HOLD / BLOCK)

\- GitHub Actions runs Terraform plan automatically on every push



\## Cloud Resources Managed (5 total)



\### Azure (3 resources)

\- Storage Account (static website hosting)

\- CDN Profile + Endpoint

\- Function App (serverless)



\### AWS (2 resources)

\- S3 Bucket (static website hosting)

\- CloudFront Distribution (CDN)



\## AI Plan Analyzer



Sends Terraform plan output to Gemini and returns a structured decision using Pydantic:



\- \*\*decision\*\*: PROCEED, HOLD, or BLOCK

\- \*\*risk\_level\*\*: LOW, MEDIUM, or HIGH

\- \*\*summary\*\*: one-line explanation

\- \*\*reasons\*\*: list of supporting reasons



Two scenarios tested:

1\. Safe deployment (add-only) → PROCEED

2\. Risky destroy+recreate → BLOCK



\## CI/CD



GitHub Actions workflow runs `terraform plan` on every push to `main`.



\## Project Structure

