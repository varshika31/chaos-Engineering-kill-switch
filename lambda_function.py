import json

import boto3

INSTANCE_ID = "i-091b862d909b9fa1e"
ec2 = boto3.client("ec2")


def lambda_handler(event, context):
    if not isinstance(event, dict) or event.get("confirmation") != "TRIGGER KILL SWITCH":
        raise ValueError("The exact confirmation phrase is required.")

    response = ec2.stop_instances(InstanceIds=[INSTANCE_ID])
    stopping = response.get("StoppingInstances", [])
    state = stopping[0].get("CurrentState", {}).get("Name", "stopping") if stopping else "stopping"

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Kill Switch activated",
            "instance_id": INSTANCE_ID,
            "state": state,
        }),
    }