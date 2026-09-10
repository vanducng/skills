# gog account: example

Copy to `$HOME/.config/vd/gog-accounts/<account>.<user|sa>.md`.
`<account>` is `cnb`, `dpl`, or `abs`. Kind file is `user` (person) or `sa`.
Keep the local copy outside Git.

## Identity

- Account: `cnb`        # skill `--account`
- User: `person`        # skill `--user` person|sa
- Alias: `cnb`          # value passed to `gog --account` (person = account, sa = account-sa)
- Email: `user@example.com`
- Domain: `example.com`
- Timezone: `Asia/Ho_Chi_Minh`

## Auth

- Method: `oauth`       # oauth (person, refresh token) | sa
- GOG_HOME: `$HOME/.config/vd/gog`
- Client: `cnb`         # gog --client; omit for default
- Key:                  # sa only: path to JSON, mode 0600
- Act as: `key`         # sa only: key = as-itself; or a user email if DWD is on

## Defaults

- Use for: which requests route here
- Notes: consent-screen status (must be In production for person users), org app-access policy
