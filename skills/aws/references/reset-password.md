# Reset an IAM console password

Use this workflow only for the `reset-password` or `--reset-password` action. Load and follow the `vd:gopass` skill as well.

This is an administrator reset with `iam:UpdateLoginProfile`. It does not require the old console password. Do not substitute `iam:ChangePassword`, which is the self-service operation and requires the correct current password.

## Required inputs

- Exact IAM username, such as `<iam-user>`
- Destination gopass entry, such as `personal/aws/console`
- Exact named AWS profile and intended account
- CloudTrail region used for IAM audit events

Use placeholders in documentation and reports. Never embed a real username, email address, account ID, or password.

## Preflight

Keep this phase read-only:

```bash
iam_user='<iam-user>'
gopass_entry='<gopass-entry>'
aws_profile='<aws-profile>'
cloudtrail_region='<cloudtrail-region>'

caller_arn="$(aws sts get-caller-identity --profile "$aws_profile" --query Arn --output text)"
account_id="$(aws sts get-caller-identity --profile "$aws_profile" --query Account --output text)"
target_arn="$(aws iam get-user --profile "$aws_profile" --user-name "$iam_user" --query User.Arn --output text)"

printf 'caller=%s\naccount=%s\ntarget=%s\n' "$caller_arn" "$account_id" "$target_arn"
aws iam get-account-password-policy --profile "$aws_profile" --output json
aws iam get-login-profile --profile "$aws_profile" --user-name "$iam_user" --output json
```

Confirm the target account and user with the requester if either is ambiguous. Obtain explicit authorization for the reset before continuing.

When the caller is an IAM user or role ARN supported by the simulator, preflight the exact action and target:

```bash
aws iam simulate-principal-policy \
  --profile "$aws_profile" \
  --policy-source-arn "$caller_arn" \
  --action-names iam:UpdateLoginProfile \
  --resource-arns "$target_arn" \
  --output json
```

The simulator is advisory. Re-check permissions boundaries, Organizations policies, and session context when the live result differs.

## Generate without storing

Generate a fresh candidate in memory. Select a length at least as large as the live account minimum, and require uppercase, lowercase, number, and symbol even when the account policy is weaker.

```bash
minimum_length="$(aws iam get-account-password-policy \
  --profile "$aws_profile" \
  --query PasswordPolicy.MinimumPasswordLength \
  --output text 2>/dev/null || printf '8')"

if [[ "$minimum_length" =~ ^[0-9]+$ ]] && (( minimum_length > 32 )); then
  password_length="$minimum_length"
else
  password_length=32
fi

candidate=''
while [[ -z "$candidate" ]]; do
  candidate="$(gopass pwgen --symbols "$password_length" | awk 'NR == 1 { value=$0 } END { print value }')"
  candidate="${candidate:0:password_length}"
  if ! [[ "$candidate" =~ [A-Z] && "$candidate" =~ [a-z] && "$candidate" =~ [0-9] && "$candidate" =~ [^[:alnum:]] ]]; then
    candidate=''
  fi
done
```

Do not print `candidate`, put it in logs, or pass it as a literal CLI argument.

## Reset and store

Stream the password through stdin so it does not appear in process arguments or a plaintext file:

```bash
printf %s "$candidate" | aws iam update-login-profile \
  --profile "$aws_profile" \
  --user-name "$iam_user" \
  --password file:///dev/stdin \
  --no-password-reset-required
```

Only after AWS succeeds, store the exact value in gopass:

```bash
if printf %s "$candidate" | gopass insert -f "$gopass_entry" &&
  test "$candidate" = "$(gopass show -o "$gopass_entry")"; then
  unset candidate
else
  printf 'gopass storage or verification failed; the candidate remains in memory\n' >&2
fi
```

If AWS succeeds but the gopass write fails, the reset is only partially complete. Preserve the in-memory candidate, repair the gopass write immediately, and do not claim completion. If the execution context can no longer preserve it, perform another authorized reset rather than printing or writing the value in plaintext.

## Verify

Verify the login profile, encrypted store, and audit event without exposing the password:

```bash
aws iam get-login-profile \
  --profile "$aws_profile" \
  --user-name "$iam_user" \
  --query 'LoginProfile.{UserName:UserName,PasswordResetRequired:PasswordResetRequired}' \
  --output json

aws cloudtrail lookup-events \
  --profile "$aws_profile" \
  --region "$cloudtrail_region" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=UpdateLoginProfile \
  --max-results 20 \
  --output json

gopass find "$gopass_entry"
```

CloudTrail ingestion can lag. A successful `UpdateLoginProfile` response plus the refreshed login profile is sufficient immediate evidence; follow the event until it appears when audit proof is required.

Tell the user to sign out and sign back in with `gopass -c <gopass-entry>`. Do not expose the password in screenshots, terminal output, reports, or chat.
