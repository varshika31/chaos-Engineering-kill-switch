# Chaos Engineering Kill Switch Website

A local dashboard that reads live Auto Scaling Group, EC2 instance, and CloudWatch alarm data from AWS. The virtual switch invokes the existing Lambda function after a typed confirmation.

## Important safety check before clicking the switch

This is connected to real AWS resources. Invoking `chaos-kill-switch` may stop or terminate an EC2 instance. Before triggering it:
1. Open the Lambda function in AWS Console and inspect its code.
2. Confirm it targets the current ASG-managed instance dynamically or otherwise targets the intended current instance.
3. Confirm its execution role has only the required permissions.
4. Keep the ASG desired capacity/min/max as intended for your lab.
5. Do not place AWS access keys in this project or in browser JavaScript.

## 1. Prerequisites

- Python 3.10+
- AWS CLI installed and configured with credentials for the same AWS account and `us-east-1`.
- The AWS identity must have read permissions for Auto Scaling, EC2, and CloudWatch, plus `lambda:InvokeFunction` for `chaos-kill-switch`.

Check AWS CLI credentials:
```bash
aws sts get-caller-identity
aws configure get region
```
If you use a named AWS CLI profile, set it in your terminal before starting the server:
- Windows PowerShell: `$env:AWS_PROFILE="your-profile-name"`
- macOS/Linux: `export AWS_PROFILE=your-profile-name`

Never paste AWS keys into chat or commit them to this project.

## 2. Install and run on Windows (PowerShell)

Extract the ZIP, open PowerShell in the extracted `chaos_kill_switch_website` folder, then run:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r "requirements (2).txt"
aws sts get-caller-identity
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
If PowerShell blocks activation, run:
```powershell
.\.venv\Scripts\python.exe -m pip install -r "requirements (2).txt"
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000. If port 8000 is already occupied, use `--port 8001` in the server command and open http://127.0.0.1:8001 instead. The lab credential helper uses port 8001.

## 3. Required IAM permissions

The AWS identity used by your local backend needs read access to:
- `autoscaling:DescribeAutoScalingGroups`
- `ec2:DescribeInstances`
- `cloudwatch:DescribeAlarms`

And invoke permission:
- `lambda:InvokeFunction` on the Lambda function ARN.

Ask your lab administrator/instructor to grant only the required permissions if your VocLabs account denies them. Do not try to bypass lab restrictions.

## 4. Test safely

1. Start the app and check that the dashboard reads your actual ASG, instances, and alarm.
2. If status calls fail, use the displayed error to check credentials, region, names, and IAM permissions.
3. Before using the red button, inspect `chaos-kill-switch` code and ensure its target is correct. Earlier versions of this project used a hard-coded instance ID; such an ID can become stale after Auto Scaling replaces an instance.
4. The button requires typing `TRIGGER KILL SWITCH`. It sends a synchronous invocation to the existing Lambda and displays the Lambda response.
5. Refresh/observe the ASG and CloudWatch status after invocation. Auto Scaling replacement may take some time.

## Notes

- This website does not configure IoT Core and does not pretend an ESP32 is connected. It provides a website-based virtual switch that calls Lambda directly.
- The dashboard polls AWS status every 30 seconds.
- The site binds only to `127.0.0.1` by default. Do not expose it to the public internet without adding proper user authentication, HTTPS, CSRF protection, and tighter authorization.
py -m venv .venv