# AWS credential and secret operations

Use this reference for Secrets Manager value changes, application credential rotation, one-off ECS provisioning tasks, and any ECS Exec session that may touch a secret.

## Keep plaintext out of the command channel

Treat every string passed to `aws ecs execute-command --command` as auditable plaintext. AWS documents CloudTrail auditing for `ExecuteCommand` and optional capture of commands and output in CloudWatch Logs or S3. The local shell, process arguments, Session Manager, and terminal transcript add more places where a command can persist.

- Never interpolate a password, token, connection URL, secret JSON, or private key into `--command`.
- Base64 changes representation, not confidentiality.
- Do not echo a secret and plan to redact it later. Prevent the plaintext from entering the channel.
- If plaintext entered an ECS Exec command or command output, treat it as exposed and rotate it after service recovery.

## Preferred delivery order

Use the first available path:

1. Map a Secrets Manager JSON key into the task definition and let the application read it from the environment.
2. Run a dedicated one-off task whose task definition references the secret. Override only the non-secret command.
3. Let code in the trusted target generate the credential and write it directly to Secrets Manager through its task role.
4. If the new value must return to the operator, return only ciphertext encrypted to an ephemeral operator-held public key.

Do not use ECS Exec as a substitute for missing task-definition secret mappings when the durable application or provisioning path can carry the value safely.

## Encrypted return pattern

When a target must generate and apply a credential before the operator can store it:

1. Generate an ephemeral asymmetric key pair locally. Set the private-key file mode to `0600` and keep it in a temporary directory.
2. Send only the public key through ECS Exec.
3. Inside the target, generate the credential with a cryptographic RNG, apply the dependent change transactionally, encrypt the credential with the public key, and print one bounded success marker containing ciphertext only.
4. Require the remote command to exit zero and require the exact success marker. No marker means no promotion.
5. Decrypt locally, reconstruct the complete secret value while preserving every unrelated JSON key, and stream it to Secrets Manager through `file:///dev/stdin`.
6. Clear shell variables and delete the private key, ciphertext, and temporary directory.
7. Replace the consuming task and verify the real application path.

Before the remote write, prove the current principal can perform it. Database roles, KMS keys, and external APIs may reject self-rotation even when the principal owns the credential.

## Versioned two-phase cutover

Record the current version ID before changing a secret. Create a candidate version with a non-current staging label so a failed producer-side change cannot break consumers:

```bash
set -euo pipefail

secret_id='<secret-id>'
current_version="$(aws secretsmanager describe-secret \
  --secret-id "$secret_id" \
  --query 'VersionIdsToStages' \
  --output json | jq -r 'to_entries[] | select(.value | index("AWSCURRENT")) | .key')"
test -n "$current_version"

candidate_version="$(build_complete_secret_json \
  | jq -sce 'if length == 1 and (.[0] | type == "object") then .[0] else error("complete secret must be exactly one JSON object") end' \
  | aws secretsmanager put-secret-value \
      --secret-id "$secret_id" \
      --secret-string file:///dev/stdin \
      --version-stages CANDIDATE \
      --query VersionId \
      --output text)"
test -n "$candidate_version"
```

After the producer-side change and candidate validation succeed, promote the exact version:

```bash
aws secretsmanager update-secret-version-stage \
  --secret-id "$secret_id" \
  --version-stage AWSCURRENT \
  --move-to-version-id "$candidate_version" \
  --remove-from-version-id "$current_version"
```

Keep `current_version` until the replacement service is healthy. Roll back by moving `AWSCURRENT` back to it, then replace the consumer task again. If a consumer can read only `AWSCURRENT`, make that rollback command part of the written plan before promotion.

## Completion evidence

Verify all applicable layers with fresh reads:

- Secrets Manager shows the intended `AWSCURRENT` version and expected key set without printing values.
- The consuming task is replaced and its deployment is stable.
- The target reports the intended runtime identity or credential version.
- The public endpoint or real application operation succeeds.
- A bounded CloudWatch query finds no new authentication or permission failures.
- Any credential exposed during an earlier attempt has been rotated and no longer authenticates.

## Sources

- [Monitor Amazon ECS containers with ECS Exec](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html)
- [AWS CLI `put-secret-value`](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/put-secret-value.html)
- [AWS CLI `update-secret-version-stage`](https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/update-secret-version-stage.html)
