# Serverless operations

Use this reference for Lambda, Function URLs, API Gateway, SQS, DLQs, promotion, retirement, and post-change verification.

## Scope

```bash
aws_profile='<aws-profile>'
aws_region='<aws-region>'
function_name='<lambda-function-name>'

aws sts get-caller-identity \
  --profile "$aws_profile" \
  --output json
```

## Inspect Lambda ownership and configuration

```bash
aws lambda get-function-configuration \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --query '{FunctionName:FunctionName,FunctionArn:FunctionArn,Runtime:Runtime,Handler:Handler,Role:Role,PackageType:PackageType,Architectures:Architectures,Layers:Layers[].Arn,MemorySize:MemorySize,Timeout:Timeout,State:State,LastUpdateStatus:LastUpdateStatus,Version:Version,RevisionId:RevisionId,CodeSha256:CodeSha256}' \
  --output json

aws lambda get-function \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --query '{RepositoryType:Code.RepositoryType,ImageUri:Code.ImageUri,ResolvedImageUri:Code.ResolvedImageUri}' \
  --output json

aws lambda list-aliases \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --output json

aws lambda list-event-source-mappings \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --output json
```

The unfiltered configuration contains environment values, and `get-function` returns a short-lived deployment-package URL. Never print either response unfiltered. When a ZIP comparison is authorized, capture `Code.Location` into a shell variable, download into a permission-restricted temporary directory, unset the URL, and keep command tracing disabled.

For a Function URL, check the unqualified function and every relevant alias:

```bash
aws lambda get-function-url-config \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --output json

qualifier='<lambda-alias>'

aws lambda get-function-url-config \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --qualifier "$qualifier" \
  --output json
```

If the URL ID is known but the function is not, scan configured profiles, Regions, functions, and aliases only within the user-approved scope. Surface access errors instead of discarding them, because a silent failure makes an incomplete scan look authoritative.

## Trace API Gateway

First identify whether the API is REST API v1 or HTTP/WebSocket API v2. Do not mix their command families.

For API Gateway v2:

```bash
api_id='<api-id>'

aws apigatewayv2 get-api \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --api-id "$api_id" \
  --output json

aws apigatewayv2 get-routes \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --api-id "$api_id" \
  --output json

aws apigatewayv2 get-integrations \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --api-id "$api_id" \
  --output json

aws apigatewayv2 get-stages \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --api-id "$api_id" \
  --output json
```

For REST API v1:

```bash
rest_api_id='<rest-api-id>'

aws apigateway get-rest-api \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --rest-api-id "$rest_api_id" \
  --output json

aws apigateway get-resources \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --rest-api-id "$rest_api_id" \
  --embed methods \
  --output json

aws apigateway get-stages \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --rest-api-id "$rest_api_id" \
  --output json
```

Compare the deployed route method/path, target integration, stage, authorizer, and repository route declaration. An OpenAPI document or framework state does not prove that the live route is deployed. Verify with an over-the-wire request using the exact method.

## Inspect SQS and DLQs safely

```bash
queue_url='<queue-url>'

aws sqs get-queue-attributes \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --queue-url "$queue_url" \
  --attribute-names All \
  --output json

aws sqs list-queue-tags \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --queue-url "$queue_url" \
  --output json

aws sqs list-dead-letter-source-queues \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --queue-url "$queue_url" \
  --output json
```

Do not classify `receive-message` as a harmless read. Receiving a message makes it temporarily invisible to other consumers. Require explicit authorization and a recovery plan before receiving, redriving, purging, or deleting production messages or queues.

For Lambda consumers, correlate queue depth, age of oldest message, DLQ arrival, event-source mapping state, batch size, maximum concurrency, Lambda errors, throttles, and concurrent executions. Do not infer consumer health from queue depth alone.

## Promote Lambda code

Before promotion:

1. Inspect recent repository changes and the owning deployment workflow.
2. Read `PackageType`. For `Zip`, download `Code.Location` into a temporary directory. For `Image`, compare the live image URI and resolved digest with the intended ECR artifact.
3. Compare live code or image, handler name, runtime, architecture, layers, and packaging with the intended artifact.
4. Validate the local artifact with its native checker or tests.
5. Resolve whether each consumer invokes the unqualified function, an alias, or an immutable numbered version. Stop if the live-vs-local diff contains anything outside the approved change.

Use Lambda's dry run and revision guard before the authorized write. Set the matching artifact input from the observed `PackageType`:

```bash
read -r package_type revision_id <<<"$(aws lambda get-function-configuration \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --query '[PackageType,RevisionId]' \
  --output text)"

case "$package_type" in
  Zip)
    package_path='<deployment-zip-path>'
    code_args=(--zip-file "fileb://$package_path")
    ;;
  Image)
    image_uri='<ecr-image-uri-with-digest>'
    code_args=(--image-uri "$image_uri")
    ;;
  *)
    exit 1
    ;;
esac

aws lambda update-function-code \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  "${code_args[@]}" \
  --revision-id "$revision_id" \
  --dry-run \
  --query '{FunctionName:FunctionName,PackageType:PackageType,LastUpdateStatus:LastUpdateStatus,RevisionId:RevisionId,CodeSha256:CodeSha256}' \
  --output json
```

After explicit authorization, repeat without `--dry-run`, then wait and re-read:

```bash
aws lambda update-function-code \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  "${code_args[@]}" \
  --revision-id "$revision_id" \
  --query '{FunctionName:FunctionName,PackageType:PackageType,LastUpdateStatus:LastUpdateStatus,RevisionId:RevisionId,CodeSha256:CodeSha256}' \
  --output json

aws lambda wait function-updated-v2 \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name"

aws lambda get-function-configuration \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --query '{State:State,LastUpdateStatus:LastUpdateStatus,Reason:LastUpdateStatusReason,CodeSha256:CodeSha256,RevisionId:RevisionId}' \
  --output json
```

If a consumer invokes an alias, publishing code to `$LATEST` does not move that consumer. Read its existing routing config, then explicitly choose full cutover or a weighted canary. After explicit authorization for the version and alias writes, publish the verified code and update the alias with both function and alias revision guards. This example performs a full cutover by clearing additional version weights:

```bash
alias_name='<lambda-alias>'

aws lambda get-alias \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --name "$alias_name" \
  --query '{FunctionVersion:FunctionVersion,RoutingConfig:RoutingConfig,RevisionId:RevisionId}' \
  --output json

deployed_revision="$(aws lambda get-function-configuration \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --query RevisionId \
  --output text)"

alias_revision="$(aws lambda get-alias \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --name "$alias_name" \
  --query RevisionId \
  --output text)"

published_version="$(aws lambda publish-version \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --revision-id "$deployed_revision" \
  --query Version \
  --output text)"

aws lambda update-alias \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --name "$alias_name" \
  --function-version "$published_version" \
  --revision-id "$alias_revision" \
  --routing-config 'AdditionalVersionWeights={}' \
  --query '{FunctionVersion:FunctionVersion,RoutingConfig:RoutingConfig,RevisionId:RevisionId}' \
  --output json

aws lambda get-alias \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --function-name "$function_name" \
  --name "$alias_name" \
  --query '{FunctionVersion:FunctionVersion,RoutingConfig:RoutingConfig,RevisionId:RevisionId}' \
  --output json
```

For a canary, pass the reviewed `AdditionalVersionWeights` instead and verify both versions and weights. Do not try to change an immutable numbered-version consumer in place; update its owning integration or deployment configuration. Re-download the ZIP or verify the resolved image digest when artifact parity matters. Then read [observability-storage.md](observability-storage.md) for the post-deploy window. CloudWatch can prove invocation health, errors, timeouts, cold starts, resource use, and the executed version when present in platform logs, but verify application response fields from the authoritative endpoint or data store.

## Retire serverless resources

- Prefer the owning IaC or framework destroy path so state remains coherent.
- Treat retain-on-delete settings as a warning that the framework can remove state without deleting live resources.
- Re-read routes, integrations, Lambda permissions, event-source mappings, queues, DLQs, IAM roles, SSM pointers, alarms, and dashboards after cleanup.
- Verify the endpoint returns the intended response and the retired path no longer emits logs or consumes messages.
- Require explicit authorization before deleting any route, integration, permission, function, queue, alarm, or role.

## Sources

- [AWS Lambda UpdateFunctionCode](https://docs.aws.amazon.com/cli/latest/reference/lambda/update-function-code.html)
- [AWS Lambda waiters](https://docs.aws.amazon.com/cli/latest/reference/lambda/wait/)
- [AWS Lambda weighted alias routing](https://docs.aws.amazon.com/lambda/latest/dg/configuring-alias-routing.html)
- [API Gateway v2 get-routes](https://docs.aws.amazon.com/cli/latest/reference/apigatewayv2/get-routes.html)
- [Amazon SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [AWS serverless skill](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-serverless)
