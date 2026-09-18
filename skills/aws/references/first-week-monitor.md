# First-week ECS service monitor

Read-only watch for the first seven days after a production launch. Use this after a promote, not as a substitute for the release skill.

Load [observability-storage.md](observability-storage.md) before printing log payloads. This procedure prints **counts and utilization only**.

## Scope

```bash
aws_profile='<aws-profile>'
aws_region='<aws-region>'
cluster='<ecs-cluster>'
service='<ecs-service>'
log_group='<ecs-log-group>'
# Optional. Discover from the service if omitted.
target_group_full_name='<target-group-dimension>'   # e.g. targetgroup/app/abc123
load_balancer_full_name='<load-balancer-dimension>' # e.g. app/shared-alb/def456
```

Confirm identity first (`sts get-caller-identity`). Stop if the account is not the intended launch account.

Default script: [../scripts/first-week-monitor.sh](../scripts/first-week-monitor.sh). It is read-only.

```bash
AWS_PROFILE='<aws-profile>' AWS_REGION='<aws-region>' \
  CLUSTER='<ecs-cluster>' SERVICE='<ecs-service>' LOG_GROUP='<ecs-log-group>' \
  <skill-root>/scripts/first-week-monitor.sh
```

Save day-0 output as the baseline. Re-run at least once per day for seven days, and after any traffic spike or deploy.

## Daily checklist

1. Service is `ACTIVE`, `running == desired`, `pending == 0`, PRIMARY rollout `COMPLETED`.
2. CPU and memory peak over the last 24h stay under the scale-up line (default 60% CPU or 70% memory).
3. ALB `HTTPCode_Target_5XX` is 0 (or explained). `TargetResponseTime` p95 is not climbing vs day 0.
4. Log group `ERROR` / `"level":"error"` **count** over 24h is 0 or explained. Do not dump request bodies.
5. Public `/api/ready` on the launch hostname is 200. Do not send write traffic as a health check.
6. Compare today's request count to day 0. A quiet service with low CPU is expected in week 1 if traffic is still ramping.

## Scale-up line

Recommend a larger task or a higher desired count when **any** of these hold for two consecutive daily runs:

- 24h CPU peak >= 60%, or memory peak >= 70%
- p95 target response time >= 2x day-0 p95 and 5xx is rising
- `running < desired` or tasks cycling (service events show replacements)

Do not change desired count or task size from this skill. Report the evidence and wait for an explicit scale authorization.

## What not to do

- Do not enable a staging-only agent handshake in production.
- Do not print secrets, session cookies, or customer payloads from logs.
- Do not treat a successful CLI exit as proof the app is healthy. Pair ECS state with `/api/ready` and 5xx counts.
