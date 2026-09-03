import azure.functions as func
import json

app = func.FunctionApp()

@app.route(route="hello", auth_level=func.AuthLevel.ANONYMOUS)
def hello(req: func.HttpRequest) -> func.HttpResponse:
    body = json.dumps({
        "message": "Hello from Azure Function - DriftLens Workload B",
        "project": "pSiddhi-2026-01",
        "owner": "jashwanth.dhanasekaran"
    })
    return func.HttpResponse(body, mimetype="application/json")
