---
name: aws
description: Operate AWS accounts and services with the AWS CLI using identity-first, read-before-write, evidence-backed workflows. Use for AWS CLI inspection, incident diagnosis, deployment verification, and explicitly authorized changes across IAM, STS, Organizations, CloudTrail, CloudWatch, S3, Lambda, API Gateway, SQS, Route 53, ALB/ELBv2, EC2, EBS, SSM, ECS, and related services, including reset-password or --reset-password when an IAM console password must be reset and stored with gopass.
license: MIT
metadata:
  author: vanducng
  version: "0.1.0"
---

# AWS

Use the installed `aws` CLI for AWS inspection, diagnosis, and explicitly authorized changes.

## Route the request

- For `reset-password` or `--reset-password`, read [references/reset-password.md](references/reset-password.md) completely and use the `vd:gopass` skill.
- For public endpoint tracing, incidents, cleanup, or cross-service verification, read [references/daily-operations.md](references/daily-operations.md), then load the service references it selects.
- For Lambda, API Gateway, Function URLs, SQS, DLQs, serverless promotion, or retirement, read [references/serverless.md](references/serverless.md).
- For Route 53, ALB/ELBv2, target groups, EC2, EBS, or SSM, read [references/compute-networking.md](references/compute-networking.md).
- For CloudWatch, CloudTrail, S3, log analysis, audit correlation, or object verification, read [references/observability-storage.md](references/observability-storage.md).
- For other requests, follow the general workflow below and load current service-specific official documentation when command behavior is unclear or likely to have changed.

## General workflow

1. Confirm the active identity before interpreting or changing anything:

   ```bash
   aws sts get-caller-identity --output json
   aws configure list
   ```

2. Resolve the intended account, profile, region, service, and exact resource. Use `--profile` and `--region` explicitly when local defaults do not prove the intended scope.
3. Inspect current state with `list-*`, `get-*`, `describe-*`, CloudTrail, or the relevant service API before forming a diagnosis.
4. For authorization failures, trace the failed CloudTrail event and evaluate every applicable policy layer. Do not infer the denying layer from attached policies alone.
5. Keep investigations read-only unless the user requested a change. Before a write, restate the exact account, resource, action, and expected effect when any are ambiguous.
6. Perform the smallest authorized AWS API change. Do not broaden a repair into unrelated IAM, Organizations, networking, or production mutations.
7. Verify with fresh service state and, when useful, the resulting CloudTrail event. Do not treat a successful CLI exit as the only proof.

## CLI conventions

- Prefer `--output json` plus `--query` or `jq` so evidence is reviewable.
- Add `--no-cli-pager` for non-interactive commands when pager configuration could block execution.
- Treat IAM, STS, and Organizations as global services, but specify the recording region when querying CloudTrail.
- Use `aws <service> <operation> help` before guessing an unfamiliar parameter.
- Prefer AWS CLI waiters or refreshed service state over arbitrary sleeps after asynchronous changes.
- Do not freeze service quotas, pricing, runtime matrices, or Region availability into reports; verify them from current official sources.
- Never print credentials, password values, session tokens, secret payloads, or decrypted gopass content.
- Keep secret values out of command arguments. Pipe them into supported `file:///dev/stdin` parameters or use another consumer-owned stdin mechanism.
- Use the `vd:gopass` skill whenever AWS work needs a stored credential, token, or password.

## Authorization diagnosis

Start with the caller and the failed event:

```bash
cloudtrail_region='<cloudtrail-region>'
api_operation='<api-operation>'

aws sts get-caller-identity --output json
aws cloudtrail lookup-events \
  --region "$cloudtrail_region" \
  --lookup-attributes AttributeKey=EventName,AttributeValue="$api_operation" \
  --max-results 20 \
  --output json
```

Then inspect only the policy sources relevant to that principal: direct and group policies, permissions boundary, session policy context, and Organizations policies. Use `iam simulate-principal-policy` as supporting evidence, not as proof of effective access because it does not model every policy type or request context.

## Safety boundaries

- Require explicit authorization for credential rotation, IAM writes, resource deletion, production changes, and Organizations changes.
- Never test access by making a potentially successful destructive request. Use simulators, dry runs, validation APIs, or deliberately non-mutating reads.
- Resolve exact resource identifiers before writes. Avoid wildcards when the user named one resource.
- If an AWS write succeeds but a dependent local step fails, report the partial state and recover it before claiming completion.
