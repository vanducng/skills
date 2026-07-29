# Observability and storage operations

Use this reference for CloudWatch logs and metrics, CloudTrail audit correlation, and S3 bucket or object verification.

## Scope

```bash
aws_profile='<aws-profile>'
aws_region='<aws-region>'

aws sts get-caller-identity \
  --profile "$aws_profile" \
  --output json
```

Use the smallest time window that contains the symptom, deployment, or suspected configuration change. Record timestamps in UTC.

## CloudWatch logs

For a known log group and short window, default to event metadata with a narrow service-side filter. This proves whether matching events exist without printing their payloads:

```bash
log_group='<log-group-name>'
filter_pattern='<narrow-request-id-resource-id-or-error-pattern>'
start_time_ms='<start-epoch-milliseconds>'
end_time_ms='<end-epoch-milliseconds>'

aws logs filter-log-events \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --log-group-name "$log_group" \
  --filter-pattern "$filter_pattern" \
  --start-time "$start_time_ms" \
  --end-time "$end_time_ms" \
  --max-items 20 \
  --query 'events[].{Timestamp:timestamp,LogStream:logStreamName,EventId:eventId}' \
  --output json
```

Use Logs Insights for aggregation or large log groups. Aggregate first without returning raw messages:

```bash
start_time='<start-epoch-seconds>'
end_time='<end-epoch-seconds>'
query_string='filter @message like /<escaped-request-id-resource-id-or-error-token>/ | stats count(*) as matches, min(@timestamp) as firstSeen, max(@timestamp) as lastSeen by @logStream | sort matches desc | limit 20'

query_id="$(aws logs start-query \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --log-group-name "$log_group" \
  --start-time "$start_time" \
  --end-time "$end_time" \
  --query-string "$query_string" \
  --query queryId \
  --output text)"

aws logs get-query-results \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --query-id "$query_id" \
  --output json
```

Poll `get-query-results` until `Status` is `Complete`. `Scheduled` and `Running` can contain partial results and are not final evidence. Reduce or partition the time range if the query times out.

Retrieve raw messages only when aggregates and metadata are insufficient. Apply an exact time window and identifier, keep the result bounded, inspect it through a redaction-safe local path, and do not print it into an agent transcript. Do not expose secrets, authorization headers, signed URLs, or customer payloads.

## CloudWatch metrics and alarms

Start from the resource's native namespace and dimensions, then align metric periods with the incident window. Inspect both the alarm and its underlying metric:

```bash
alarm_name='<alarm-name>'

aws cloudwatch describe-alarms \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --alarm-names "$alarm_name" \
  --output json

aws cloudwatch describe-alarm-history \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --alarm-name "$alarm_name" \
  --history-item-type StateUpdate \
  --output json
```

Correlate service metrics instead of reading one graph in isolation. Examples include ALB target response and unhealthy-host counts, Lambda invocations/errors/throttles/duration/concurrency, SQS queue depth and message age, EC2 status checks and disk telemetry, and API Gateway latency and 4xx/5xx counts.

## CloudTrail change correlation

Use EventName when the failed API is known, or ResourceName when tracing a resource. The lookup API accepts one lookup attribute per call, so run separate queries when both are needed.

```bash
event_name='<api-operation>'
start_time='<ISO-8601-start>'
end_time='<ISO-8601-end>'

aws cloudtrail lookup-events \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --lookup-attributes AttributeKey=EventName,AttributeValue="$event_name" \
  --start-time "$start_time" \
  --end-time "$end_time" \
  --max-results 50 \
  --output json
```

Correlate the event time, actor, source IP, request parameters, response or error, and the first application failure. CloudTrail proves AWS API activity, not every in-host, data-plane, or application event.

## S3 discovery and verification

Use `head-bucket` for Region discovery. Current AWS documentation says `get-bucket-location` is retained for compatibility and is no longer the preferred operation.

```bash
bucket='<bucket-name>'

bucket_region="$(aws s3api head-bucket \
  --profile "$aws_profile" \
  --bucket "$bucket" \
  --query BucketRegion \
  --output text)"

aws s3api get-public-access-block \
  --profile "$aws_profile" \
  --region "$bucket_region" \
  --bucket "$bucket" \
  --output json

aws s3api get-bucket-encryption \
  --profile "$aws_profile" \
  --region "$bucket_region" \
  --bucket "$bucket" \
  --output json

aws s3api get-bucket-versioning \
  --profile "$aws_profile" \
  --region "$bucket_region" \
  --bucket "$bucket" \
  --output json
```

Some optional bucket configurations return a not-found error when unset. Interpret that as absent configuration, not an unavailable bucket.

Inspect an exact object before downloading it:

```bash
object_key='<object-key>'

aws s3api head-object \
  --profile "$aws_profile" \
  --region "$bucket_region" \
  --bucket "$bucket" \
  --key "$object_key" \
  --output json
```

Prefer `head-object` to a broad listing when the key is known. For listings, use a prefix and a bounded result count. Use a temporary file and a byte range for a content smoke test when full download is unnecessary.

Presigned URLs are bearer credentials until they expire. Do not log them, commit them, paste them into reports, or include them in screenshots. Verify expiry and response metadata, and share them only through the user-approved channel.

## Mutation boundaries

- CloudWatch alarm changes, log retention changes, and query-result sharing require explicit authorization.
- S3 uploads, copies, deletes, lifecycle changes, bucket policy changes, version deletion, restore requests, and replication changes require explicit authorization.
- Before an S3 write, confirm account, bucket Region, exact key or prefix, versioning state, encryption, and rollback.
- After a write, verify object metadata or version ID and the actual consumer path. Do not rely only on command success.

## Sources

- [CloudWatch Logs start-query](https://docs.aws.amazon.com/cli/latest/reference/logs/start-query.html)
- [CloudWatch Logs get-query-results](https://docs.aws.amazon.com/cli/latest/reference/logs/get-query-results.html)
- [AWS observability skill](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-observability)
- [S3 GetBucketLocation guidance](https://docs.aws.amazon.com/cli/latest/reference/s3api/get-bucket-location.html)
- [Amazon S3 security best practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
