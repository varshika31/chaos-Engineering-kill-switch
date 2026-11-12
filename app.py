import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LAMBDA_FUNCTION = os.getenv("LAMBDA_FUNCTION", "CHAOS-KILL-SWITCH")
ASG_NAME = os.getenv("ASG_NAME", "CHAOS-HEALING-ASG")
ALARM_NAME = os.getenv("ALARM_NAME", "CHAOS-HEALING-ASG-STATUSCHECK")
STATIC_DIR = Path(__file__).resolve().parent / "static"

session = boto3.Session(region_name=AWS_REGION)
autoscaling = session.client("autoscaling")
ec2 = session.client("ec2")
cloudwatch = session.client("cloudwatch")
lambda_client = session.client("lambda")

app = FastAPI(title="Chaos Engineering Kill Switch Dashboard")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


def aws_error(exc: Exception):
    return HTTPException(status_code=502, detail=f"AWS request failed: {str(exc)}")


@app.get("/api/status")
def status() -> dict[str, Any]:
    try:
        groups = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[ASG_NAME]
        ).get("AutoScalingGroups", [])
        if not groups:
            raise HTTPException(status_code=404, detail=f"Auto Scaling Group '{ASG_NAME}' was not found.")
        group = groups[0]
        instances = []
        ids = [x["InstanceId"] for x in group.get("Instances", [])]
        ec2_by_id = {}
        if ids:
            reservations = ec2.describe_instances(InstanceIds=ids).get("Reservations", [])
            for reservation in reservations:
                for inst in reservation.get("Instances", []):
                    ec2_by_id[inst["InstanceId"]] = inst
        for item in group.get("Instances", []):
            inst = ec2_by_id.get(item["InstanceId"], {})
            instances.append({
                "id": item["InstanceId"],
                "lifecycle": item.get("LifecycleState", "Unknown"),
                "health": item.get("HealthStatus", "Unknown"),
                "state": inst.get("State", {}).get("Name", "Unknown"),
                "type": inst.get("InstanceType", "Unknown"),
                "az": inst.get("Placement", {}).get("AvailabilityZone", "Unknown"),
            })

        alarm_response = cloudwatch.describe_alarms(AlarmNames=[ALARM_NAME])
        alarms = alarm_response.get("MetricAlarms", [])
        alarm = None
        if alarms:
            a = alarms[0]
            alarm = {
                "name": a["AlarmName"],
                "state": a["StateValue"],
                "reason": a.get("StateReason", ""),
                "metric": a.get("MetricName", "Unknown"),
                "threshold": a.get("Threshold"),
                "comparison": a.get("ComparisonOperator"),
            }

        return {
            "region": AWS_REGION,
            "asg_name": ASG_NAME,
            "desired": group.get("DesiredCapacity"),
            "minimum": group.get("MinSize"),
            "maximum": group.get("MaxSize"),
            "instances": instances,
            "alarm": alarm,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise aws_error(exc)


class TriggerRequest(BaseModel):
    confirmation: str


@app.post("/api/trigger")
def trigger(payload: TriggerRequest):
    # Explicit guard: the browser must send the exact confirmation phrase.
    if payload.confirmation != "TRIGGER KILL SWITCH":
        raise HTTPException(status_code=400, detail="Confirmation phrase did not match.")
    try:
        # Invokes the existing Lambda. It does NOT terminate an instance directly here.
        # Check the Lambda code and its target before using this action.
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "source": "local-website",
                "action": "kill-switch",
                "confirmation": payload.confirmation,
            }).encode("utf-8"),
        )
        raw = response["Payload"].read().decode("utf-8", errors="replace")
        result = {
            "status_code": response.get("StatusCode"),
            "function_error": response.get("FunctionError"),
            "lambda_response": raw,
        }
        if response.get("FunctionError"):
            raise HTTPException(status_code=502, detail=f"Lambda reported an error: {raw}")
        return {"message": "Lambda invocation completed. Refresh status to verify AWS recovery.", "result": result}
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as exc:
        raise aws_error(exc)
