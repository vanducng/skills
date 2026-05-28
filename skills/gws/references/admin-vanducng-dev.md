# Admin Runbooks - vanducng.dev

Domain-admin recipes for `vanducng.dev`. Load this reference when managing Workspace users, groups, devices, domains, or audit logs.

Required scopes:

```bash
gws auth login --account me@vanducng.dev -s admin.directory,admin.reports
```

## List Users

```bash
gws admin users list --account me@vanducng.dev --params '{"domain":"vanducng.dev","maxResults":500}' \
  | jq -r '.users[] | [.primaryEmail, .name.fullName, .suspended, .lastLoginTime] | @tsv'
```

## Create User

Read existing users first and confirm the new `primaryEmail`. Use a strong temporary password and do not print it in chat.

```bash
gws admin users insert --account me@vanducng.dev --json '{
  "primaryEmail": "newuser@vanducng.dev",
  "name": {"givenName": "First", "familyName": "Last"},
  "password": "TEMP-CHANGE-ON-FIRST-LOGIN-xxxx",
  "changePasswordAtNextLogin": true
}'
```

## Suspend Or Unsuspend

Prefer suspension over deletion. Confirm the target user and current state first.

```bash
gws admin users get --account me@vanducng.dev --params '{"userKey":"x@vanducng.dev"}'
gws admin users update --account me@vanducng.dev --params '{"userKey":"x@vanducng.dev"}' --json '{"suspended":true}'
gws admin users update --account me@vanducng.dev --params '{"userKey":"x@vanducng.dev"}' --json '{"suspended":false}'
```

## Reset Password

Use `changePasswordAtNextLogin: true`. Do not echo the password value in chat or logs.

```bash
gws admin users update --account me@vanducng.dev --params '{"userKey":"x@vanducng.dev"}' \
  --json '{"password":"NEW-TEMP-xxx","changePasswordAtNextLogin":true}'
```

## Group Management

```bash
gws admin groups list --account me@vanducng.dev --params '{"domain":"vanducng.dev"}'
gws admin groups get --account me@vanducng.dev --params '{"groupKey":"team@vanducng.dev"}'
gws admin groups insert --account me@vanducng.dev --json '{"email":"team@vanducng.dev","name":"Team","description":"..."}'
gws admin members list --account me@vanducng.dev --params '{"groupKey":"team@vanducng.dev"}'
gws admin members insert --account me@vanducng.dev --params '{"groupKey":"team@vanducng.dev"}' --json '{"email":"user@vanducng.dev","role":"MEMBER"}'
```

## Audit And Activity Reports

```bash
gws admin activities list --account me@vanducng.dev --params '{"userKey":"all","applicationName":"admin","maxResults":100}'
gws admin activities list --account me@vanducng.dev --params '{"userKey":"x@vanducng.dev","applicationName":"login","maxResults":50}'
gws admin activities list --account me@vanducng.dev --params '{"userKey":"all","applicationName":"drive","eventName":"change_user_access"}'
```

## Domain Settings

```bash
gws admin domains list --account me@vanducng.dev --params '{"customer":"my_customer"}'
gws admin domainAliases list --account me@vanducng.dev --params '{"customer":"my_customer"}'
```

## Safety Reminders

- Always run `users get`, `groups get`, or `members list` before updates.
- Never bulk-suspend without explicit per-user confirmation.
- Password resets must require password change at next login.
- User deletion is irreversible; suspend first unless the user explicitly asks to delete.
