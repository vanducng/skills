# Compute and networking operations

Use this reference to trace Route 53, ALB/ELBv2, target groups, EC2, EBS, and SSM. Keep discovery read-only until a specific repair is authorized.

## Scope

```bash
aws_profile='<aws-profile>'
aws_region='<aws-region>'
hostname='<hostname>'

aws sts get-caller-identity \
  --profile "$aws_profile" \
  --output json

dig +short "$hostname" A
dig +short "$hostname" CNAME
```

Use the exact hosted zone ID after confirming the authoritative zone:

```bash
hosted_zone_id='<hosted-zone-id>'

aws route53 list-resource-record-sets \
  --profile "$aws_profile" \
  --hosted-zone-id "$hosted_zone_id" \
  --output json |
  jq --arg name "${hostname%.}." '.ResourceRecordSets[] | select(.Name == $name)'
```

Route 53 is global. Do not add a Region to hosted-zone and record-set calls. Route 53 Domains operations use `us-east-1`.

## Trace an ALB

Find the load balancer whose DNS name matches the Route 53 alias, then inspect every traffic decision:

```bash
aws elbv2 describe-load-balancers \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --query 'LoadBalancers[].{Name:LoadBalancerName,Arn:LoadBalancerArn,DNS:DNSName,State:State.Code,Scheme:Scheme}' \
  --output table

load_balancer_arn='<load-balancer-arn>'

aws elbv2 describe-listeners \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --load-balancer-arn "$load_balancer_arn" \
  --output json

listener_arn='<listener-arn>'

aws elbv2 describe-rules \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --listener-arn "$listener_arn" \
  --output json
```

Check redirect actions before blaming the application. Confirm the effective host, protocol, port, path, and status code. A redirect can change how a client repeats a non-GET request.

Inspect the selected target group and preserve the health reason and description:

```bash
target_group_arn='<target-group-arn>'

aws elbv2 describe-target-groups \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --target-group-arns "$target_group_arn" \
  --output json

aws elbv2 describe-target-health \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --target-group-arn "$target_group_arn" \
  --query 'TargetHealthDescriptions[].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason,Description:TargetHealth.Description}' \
  --output table
```

Use `State`, `Reason`, and `Description` as evidence. `Target.ResponseCodeMismatch`, `Target.Timeout`, `Target.FailedHealthChecks`, `Target.NotInUse`, and `Target.InvalidState` imply different next checks.

## Inspect EC2, EBS, and SSM

```bash
instance_id='<instance-id>'

aws ec2 describe-instances \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --instance-ids "$instance_id" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,State:State.Name,PrivateIp:PrivateIpAddress,Subnet:SubnetId,Vpc:VpcId,Profile:IamInstanceProfile.Arn,Volumes:BlockDeviceMappings[].Ebs.VolumeId,Tags:Tags}' \
  --output json

aws ec2 describe-instance-status \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --instance-ids "$instance_id" \
  --include-all-instances \
  --output json

aws ssm describe-instance-information \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --filters "Key=InstanceIds,Values=$instance_id" \
  --output json
```

If SSM is unavailable, distinguish missing IAM, network path, stopped agent, and a broken host. During an outage, repeated SSM retries can waste time when disk exhaustion or failed system services prevent the agent from registering. Use an explicitly authorized EC2 Instance Connect, serial-console, or snapshot-forensic path instead.

Inspect storage without changing it:

```bash
volume_id='<volume-id>'

aws ec2 describe-volumes \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --volume-ids "$volume_id" \
  --output json

aws ec2 describe-volumes-modifications \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --volume-ids "$volume_id" \
  --output json
```

## Repair and verify

- Require explicit authorization before Route 53 changes, listener or rule changes, target registration, EC2 start/stop/reboot, remote commands, snapshots, volume modification, or filesystem repair.
- Take a recoverable snapshot before risky storage repair when the incident allows it.
- Prefer SSM Session Manager over inbound SSH for normal access. Treat EC2 Instance Connect and forensic attachment as controlled fallback paths.
- After Route 53 writes, poll `aws route53 get-change --id "$change_id" --profile "$aws_profile"` until `INSYNC`, then verify external DNS resolution.
- After load-balancer or host repair, re-read target health and probe the real hostname. Do not stop at `running` instance state.
- After EBS expansion, verify the volume modification, partition, filesystem size, free space, application service, target health, and endpoint.

## Sources

- [ELBv2 describe-target-health](https://docs.aws.amazon.com/cli/latest/reference/elbv2/describe-target-health.html)
- [Route 53 get-change](https://docs.aws.amazon.com/cli/latest/reference/route53/get-change.html)
- [Amazon EC2 security best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security.html)
- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
