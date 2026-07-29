# Daily AWS operations

Use this reference for cross-service inspection, incident response, cleanup, deployment verification, and live resource mapping. Load the narrower service references named below before executing their procedures.

## Route the operation

| Need | Read |
|---|---|
| Trace a hostname through DNS, load balancing, targets, instances, and volumes | [compute-networking.md](compute-networking.md) |
| Inspect or promote Lambda, map API Gateway, trace Function URLs, inspect SQS/DLQs | [serverless.md](serverless.md) |
| Query logs and metrics, correlate CloudTrail, inspect S3 buckets and objects | [observability-storage.md](observability-storage.md) |
| Reset an IAM console password and store it in gopass | [reset-password.md](reset-password.md) |

## Establish scope

Set explicit scope once and reuse it in every service command:

```bash
aws_profile='<aws-profile>'
aws_region='<aws-region>'

aws sts get-caller-identity \
  --profile "$aws_profile" \
  --output json

aws configure list --profile "$aws_profile"
```

Record the account, caller ARN, profile, Region, exact resource, observed symptom, and UTC time window. Stop if the identity or account does not match the intended target.

## Build the evidence graph

For an endpoint or application failure, trace dependencies in this order:

1. Reproduce the public symptom with the exact hostname, path, method, headers, and redirect behavior.
2. Resolve DNS and inspect the authoritative Route 53 record.
3. Follow the alias or target into ALB/ELBv2 or API Gateway.
4. Inspect listeners, rules, routes, integrations, stages, and target health.
5. Resolve the target to Lambda, EC2, ECS, SQS, S3, or another downstream service.
6. Query CloudWatch only for the narrow failure window and relevant resource.
7. Correlate CloudTrail configuration or IAM changes near the first failure.
8. Compare live AWS state with the repository, IaC state, deployment artifact, or expected configuration.
9. Form a root-cause hypothesis only after at least two independent evidence sources agree.

Do not assume the visible service owns the failure. A `500` behind an ALB can originate on the host, a `404` can prove an API Gateway route is absent, and a clean Lambda invocation does not prove an application response field is correct.

## Mutation gate

Before any write:

1. State the account, Region, resource ARN or ID, API action, expected effect, rollback, and verification.
2. Re-read the resource and capture concurrency guards such as Lambda `RevisionId` when supported.
3. Obtain explicit user authorization for production writes, deletion, credential changes, traffic changes, queue redrive or purge, host commands, and volume changes.
4. Prefer the owning IaC or deployment workflow. If retention or drift leaves live resources behind, verify the leftovers before direct CLI cleanup.
5. After the write, wait for the service state, re-read it, inspect logs or metrics, and probe the real endpoint or data path.

## Completion evidence

A successful CLI exit is not sufficient. Match proof to the task:

- Endpoint change: control-plane state plus an over-the-wire request.
- Lambda promotion: update waiter, configuration state, deployed artifact comparison, and runtime evidence.
- Infrastructure retirement: absent route/resource, absent dependent alarms or policies, and expected live response.
- Host recovery: instance and target health, filesystem or service state, and public endpoint recovery.
- S3 workflow: bucket Region, object metadata, and a bounded object-response check.
- IAM repair: the formerly denied operation plus CloudTrail or application evidence.

## Sources

- [AWS Agent Toolkit skills](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/skills.html)
- [AWS Agent Toolkit for AWS](https://github.com/aws/agent-toolkit-for-aws)
- [AWS Cloud operational investigations](https://docs.aws.amazon.com/devopsagent/latest/userguide/about-aws-devops-agent-devops-agent-skills.html)
