import os
import json
import subprocess
from groq import Groq
from pydantic import BaseModel

class DriftReport(BaseModel):
    resource_type: str
    resource_name: str
    has_drift: bool
    diffs: list[str]
    narrative: str

client = Groq(api_key=os.environ["GROQ_API_KEY"])

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def narrate_drift(resource_type, resource_name, diffs):
    if not diffs:
        return "No drift detected. Live state matches Terraform configuration."
    prompt = f"""You are a cloud infrastructure drift analyst for DriftLens.
A drift check found differences between Terraform-declared state and live cloud state.

Resource Type: {resource_type}
Resource Name: {resource_name}
Differences found:
{json.dumps(diffs, indent=2)}

Write a plain-English narrative (3-5 sentences) explaining:
1. What drifted and how
2. The risk level (low/medium/high)
3. Whether this needs immediate attention or can wait for next reconciliation

Return ONLY the narrative text, no JSON, no markdown."""

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = response.choices[0].message.content.strip()
    if "<think>" in text:
        text = text.split("</think>")[-1].strip()
    return text

def detect_s3_drift(bucket_name, terraform_dir):
    diffs = []
    state_json = run_cmd(f"terraform -chdir={terraform_dir} show -json")
    state = json.loads(state_json)
    tf_bucket = None
    for res in state.get("values", {}).get("root_module", {}).get("resources", []):
        if res["type"] == "aws_s3_bucket" and res["name"] == "site":
            tf_bucket = res["values"]
            break
    if not tf_bucket:
        return DriftReport(resource_type="AWS S3 Bucket", resource_name=bucket_name,
                          has_drift=False, diffs=["Bucket not found in state"], narrative="Cannot compare.")

    try:
        live_tags_raw = run_cmd(f"aws s3api get-bucket-tagging --bucket {bucket_name} --output json")
        live_tags_data = json.loads(live_tags_raw)
        live_tags = {t["Key"]: t["Value"] for t in live_tags_data.get("TagSet", [])}
    except Exception:
        live_tags = {}
    tf_tags = tf_bucket.get("tags", {})
    if tf_tags != live_tags:
        diffs.append(f"Tags: Terraform={tf_tags}, Live={live_tags}")

    try:
        live_versioning = run_cmd(f"aws s3api get-bucket-versioning --bucket {bucket_name} --output json")
        live_ver = json.loads(live_versioning).get("Status", "Disabled") if live_versioning.strip() else "Disabled"
    except Exception:
        live_ver = "Disabled"
    tf_ver = "Enabled" if tf_bucket.get("versioning", [{}]) and any(
        v.get("enabled", False) for v in (tf_bucket.get("versioning") or [{}])
    ) else "Disabled"
    if tf_ver != live_ver:
        diffs.append(f"Versioning: Terraform={tf_ver}, Live={live_ver}")

    narrative = narrate_drift("AWS S3 Bucket", bucket_name, diffs)
    return DriftReport(resource_type="AWS S3 Bucket", resource_name=bucket_name,
                      has_drift=len(diffs) > 0, diffs=diffs, narrative=narrative)

def detect_storage_drift(account_name, terraform_dir):
    diffs = []
    state_json = run_cmd(f"terraform -chdir={terraform_dir} show -json")
    state = json.loads(state_json)
    tf_storage = None
    for res in state.get("values", {}).get("root_module", {}).get("resources", []):
        if res["type"] == "azurerm_storage_account" and res["name"] == "site":
            tf_storage = res["values"]
            break
    if not tf_storage:
        return DriftReport(resource_type="Azure Storage Account", resource_name=account_name,
                          has_drift=False, diffs=["Account not found in state"], narrative="Cannot compare.")

    live_json = run_cmd(f"az storage account show --name {account_name} --resource-group rg-pSiddhi3.0-2026-01-sem2-Jashwanth -o json")
    live = json.loads(live_json)

    tf_tier = tf_storage.get("account_tier", "").lower()
    live_tier = live.get("sku", {}).get("tier", "").lower()
    if tf_tier != live_tier:
        diffs.append(f"Account tier: Terraform={tf_tier}, Live={live_tier}")

    tf_repl = tf_storage.get("account_replication_type", "").upper()
    live_repl = live.get("sku", {}).get("name", "").replace("Standard_", "").replace("Premium_", "").upper()
    if tf_repl != live_repl:
        diffs.append(f"Replication: Terraform={tf_repl}, Live={live_repl}")

    tf_https = tf_storage.get("https_traffic_only_enabled", True)
    live_https = live.get("properties", {}).get("supportsHttpsTrafficOnly", True)
    if tf_https != live_https:
        diffs.append(f"HTTPS only: Terraform={tf_https}, Live={live_https}")

    tf_tags = tf_storage.get("tags", {})
    live_tags = live.get("tags", {})
    if tf_tags != live_tags:
        diffs.append(f"Tags: Terraform={tf_tags}, Live={live_tags}")

    narrative = narrate_drift("Azure Storage Account", account_name, diffs)
    return DriftReport(resource_type="Azure Storage Account", resource_name=account_name,
                      has_drift=len(diffs) > 0, diffs=diffs, narrative=narrative)

def detect_lambda_drift(function_name, terraform_dir):
    diffs = []
    state_json = run_cmd(f"terraform -chdir={terraform_dir} show -json")
    state = json.loads(state_json)
    tf_lambda = None
    for res in state.get("values", {}).get("root_module", {}).get("resources", []):
        if res["type"] == "aws_lambda_function" and res["name"] == "hello":
            tf_lambda = res["values"]
            break
    if not tf_lambda:
        return DriftReport(resource_type="AWS Lambda Function", resource_name=function_name,
                          has_drift=False, diffs=["Function not found in state"], narrative="Cannot compare.")

    live_json = run_cmd(f"aws lambda get-function-configuration --function-name {function_name} --output json")
    live = json.loads(live_json)

    tf_runtime = tf_lambda.get("runtime", "")
    live_runtime = live.get("Runtime", "")
    if tf_runtime != live_runtime:
        diffs.append(f"Runtime: Terraform={tf_runtime}, Live={live_runtime}")

    tf_handler = tf_lambda.get("handler", "")
    live_handler = live.get("Handler", "")
    if tf_handler != live_handler:
        diffs.append(f"Handler: Terraform={tf_handler}, Live={live_handler}")

    tf_memory = tf_lambda.get("memory_size", 128)
    live_memory = live.get("MemorySize", 128)
    if tf_memory != live_memory:
        diffs.append(f"Memory: Terraform={tf_memory}MB, Live={live_memory}MB")

    tf_timeout = tf_lambda.get("timeout", 3)
    live_timeout = live.get("Timeout", 3)
    if tf_timeout != live_timeout:
        diffs.append(f"Timeout: Terraform={tf_timeout}s, Live={live_timeout}s")

    narrative = narrate_drift("AWS Lambda Function", function_name, diffs)
    return DriftReport(resource_type="AWS Lambda Function", resource_name=function_name,
                      has_drift=len(diffs) > 0, diffs=diffs, narrative=narrative)

if __name__ == "__main__":
    print("=" * 60)
    print("DriftLens Drift Detector")
    print("=" * 60)

    checks = [
        ("AWS S3 Bucket", lambda: detect_s3_drift("psiddhi-jashwanth-site", "terraform/aws")),
        ("Azure Storage", lambda: detect_storage_drift("psiddhijashwanthsite", "terraform/azure")),
        ("AWS Lambda", lambda: detect_lambda_drift("psiddhi-jashwanth-hello", "terraform/aws")),
    ]

    for label, check_fn in checks:
        print(f"\n--- {label} ---")
        try:
            report = check_fn()
            print(f"Drift Detected: {report.has_drift}")
            if report.diffs:
                print(f"Differences:")
                for d in report.diffs:
                    print(f"  - {d}")
            print(f"Narrative: {report.narrative}")
        except Exception as e:
            print(f"ERROR: {e}")

    print("\n" + "=" * 60)
    print("Drift detection complete.")
