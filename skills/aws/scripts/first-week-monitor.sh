#!/usr/bin/env bash
set -euo pipefail

profile="${AWS_PROFILE:?set AWS_PROFILE}"
region="${AWS_REGION:?set AWS_REGION}"
cluster="${CLUSTER:?set CLUSTER}"
service="${SERVICE:?set SERVICE}"
log_group="${LOG_GROUP:-}"
cpu_warn="${CPU_WARN:-60}"
mem_warn="${MEM_WARN:-70}"

aws_bin=(aws --profile "$profile" --region "$region" --no-cli-pager --output json)

echo "=== first-week monitor $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
"${aws_bin[@]}" sts get-caller-identity --query '{Account:Account,Arn:Arn}' --output json

svc="$("${aws_bin[@]}" ecs describe-services --cluster "$cluster" --services "$service")"
echo "$svc" | jq --arg c "$cluster" --arg s "$service" '{
  cluster: $c,
  service: $s,
  status: .services[0].status,
  desired: .services[0].desiredCount,
  running: .services[0].runningCount,
  pending: .services[0].pendingCount,
  taskDefinition: .services[0].taskDefinition,
  rollout: .services[0].deployments[0].rolloutState,
  cpu: .services[0].taskSets[0].computedDesiredCount
}'

task_def="$(echo "$svc" | jq -r '.services[0].taskDefinition')"
td="$("${aws_bin[@]}" ecs describe-task-definition --task-definition "$task_def")"
echo "$td" | jq '{cpu: .taskDefinition.cpu, memory: .taskDefinition.memory, containers: [.taskDefinition.containerDefinitions[] | {name, cpu, memory}]}'

end="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
start_24="$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)"

metric() {
  local ns="$1" name="$2" stat="$3"
  shift 3
  "${aws_bin[@]}" cloudwatch get-metric-statistics \
    --namespace "$ns" --metric-name "$name" --statistics "$stat" \
    --start-time "$start_24" --end-time "$end" --period 3600 \
    --dimensions "$@" \
    --query "Datapoints | sort_by(@, &Timestamp) | [-1].{ts:Timestamp, val:${stat}}" \
    --output json
}

cpu_last="$(metric AWS/ECS CPUUtilization Maximum \
  Name=ClusterName,Value="$cluster" Name=ServiceName,Value="$service")"
mem_last="$(metric AWS/ECS MemoryUtilization Maximum \
  Name=ClusterName,Value="$cluster" Name=ServiceName,Value="$service")"
echo "ecs_cpu_max_last_hour: $cpu_last"
echo "ecs_mem_max_last_hour: $mem_last"

cpu_val="$(echo "$cpu_last" | jq -r '.val // 0')"
mem_val="$(echo "$mem_last" | jq -r '.val // 0')"

tg="${TARGET_GROUP_FULL_NAME:-}"
lb="${LOAD_BALANCER_FULL_NAME:-}"
if [[ -n "$tg" && -n "$lb" ]]; then
  echo "alb_request_sum_last_hour: $(metric AWS/ApplicationELB RequestCount Sum \
    Name=TargetGroup,Value="$tg" Name=LoadBalancer,Value="$lb")"
  echo "alb_5xx_sum_last_hour: $(metric AWS/ApplicationELB HTTPCode_Target_5XX_Count Sum \
    Name=TargetGroup,Value="$tg" Name=LoadBalancer,Value="$lb")"
  echo "alb_p95_last_hour: $(
    "${aws_bin[@]}" cloudwatch get-metric-statistics \
      --namespace AWS/ApplicationELB --metric-name TargetResponseTime \
      --extended-statistics p95 \
      --start-time "$start_24" --end-time "$end" --period 3600 \
      --dimensions Name=TargetGroup,Value="$tg" Name=LoadBalancer,Value="$lb" \
      --query 'Datapoints | sort_by(@, &Timestamp) | [-1].{ts:Timestamp, p95:ExtendedStatistics.p95}' \
      --output json
  )"
else
  echo "alb: set TARGET_GROUP_FULL_NAME and LOAD_BALANCER_FULL_NAME for request/5xx/p95"
fi

if [[ -n "$log_group" ]]; then
  start_ms="$(python3 -c 'import time; print(int((time.time()-86400)*1000))')"
  end_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
  err_n="$("${aws_bin[@]}" logs filter-log-events \
    --log-group-name "$log_group" \
    --start-time "$start_ms" --end-time "$end_ms" \
    --filter-pattern '?ERROR ?"level\":\"error\""' \
    --max-items 50 \
    --query 'length(events)' --output text 2>/dev/null || echo unknown)"
  echo "log_error_events_sample_24h (capped 50): $err_n"
fi

running="$(echo "$svc" | jq -r '.services[0].runningCount')"
desired="$(echo "$svc" | jq -r '.services[0].desiredCount')"
warn=0
awk -v c="$cpu_val" -v w="$cpu_warn" 'BEGIN { exit (c+0 >= w+0) ? 0 : 1 }' && echo "WARN cpu_peak ${cpu_val} >= ${cpu_warn}" && warn=1
awk -v m="$mem_val" -v w="$mem_warn" 'BEGIN { exit (m+0 >= w+0) ? 0 : 1 }' && echo "WARN mem_peak ${mem_val} >= ${mem_warn}" && warn=1
[[ "$running" == "$desired" ]] || { echo "WARN running ${running} != desired ${desired}"; warn=1; }

if [[ "$warn" -eq 1 ]]; then
  echo "result: REVIEW"
  exit 2
fi
echo "result: OK"
