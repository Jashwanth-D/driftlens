import json

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Hello from AWS Lambda - DriftLens Workload B",
            "project": "pSiddhi-2026-01",
            "owner": "jashwanth.dhanasekaran"
        })
    }
