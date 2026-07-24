# Auth, RBAC, and S3

## Auth
- **Password:** bcrypt hash/verify (async wrappers via `asyncio.to_thread`); store on a `UserIdentity` row (provider="password") so a user can have multiple identities.
- **JWT:** HS256, `{"sub": str(user_id), "email", "role", "exp"}`, expiry from settings. `mint_token` / `decode_token` in `core/security.py`.
- **Google OAuth (optional):** `clients/google_oauth.py` - authorize_url → callback exchanges code (httpx) → fetch userinfo → enforce `GOOGLE_ALLOWED_DOMAIN` → upsert user (capture `picture` → `avatar_url`) → mint JWT → redirect to frontend with token (and/or set cookie). The redirect URI must be registered in Google console; for local E2E rely on email/password.
- **Dependency:** `get_current_user` reads `Authorization: Bearer` then cookie; `CurrentUser = Annotated[User, Depends(get_current_user)]`.

## Frontend auth
- `lib/api-client.ts`: axios instance, request interceptor attaches `Bearer` from `localStorage`; **for FormData, delete the Content-Type header** (let the browser set the multipart boundary); response interceptor on 401 clears token + dispatches an unauth event.
- `features/auth`: `auth-provider` probes `GET /auth/me` on mount (works for Bearer token AND a Google session cookie); `useLogin/useLogout/useMe/useUpdateProfile/useMyActivity`.
- Protected routes: `_protected.tsx` `beforeLoad` calls `/auth/me` else `redirect({to:'/login'})`. Admin sub-routes guard on role in `beforeLoad` else `/403`.

## RBAC - role model
Define roles in `core/permissions.py` and MIRROR them in `frontend/src/lib/permissions.ts` (the server is the real enforcer). Example from the reference build (two populations):
- **Internal (your org):** `<org>_admin` (everything), `<org>_data` (operate on all tenant data, view audit), `<org>_ae` (manage tenant orgs + their users).
- **Client (tenant):** `client_admin` (act within own company; future: manage own team).

Helpers: `is_internal(role)` (prefix check), `is_admin`, `can_view_audit` (internal-only), `can_manage_companies/users`. Backend deps: `CnbUser`/`AdminUser`/`AuditViewer` (`Annotated[User, Depends(require_*)]`).

**Tenant scoping:** clients see only their company's rows; internal roles see all. Enforce in the service `list()`/`get()`, not just the UI.

**Audit visibility:** keep the audit trail internal-only. Do NOT show it in the client UI. A client's own-activity feed (`GET /auth/me/activity`, self only) is fine for a Profile page; the cross-tenant audit log is not.

## Multi-tenant Google login (JIT + pending + admin grant)
When clients sign in with their OWN Google accounts you can't domain-allowlist. Pattern:
- Google callback = JIT: do NOT hard-reject by domain (leave `GOOGLE_ALLOWED_DOMAIN` empty). New user → create with role `pending`, `company_id=null`, `is_active=true`, capture `picture` → `avatar_url`. Existing user keeps role/company.
- Add a `pending` role with no permissions. A pending user authenticates (`/auth/me` works) but has no resource access; the frontend `_protected` `beforeLoad` redirects `role === 'pending'` to a `/pending` page ("access being set up").
- A CNB admin/AE then grants access on the Users screen: `PATCH /users/{id}` with `role` + `company_id`. Show pending users with a Pending badge; the edit dialog sets BOTH role and company.
- Register the local callback (`http://localhost:<fe-port>/api/v1/auth/google/callback`) + the prod URL in the Google client; nginx proxies `/api/` to the backend so the frontend-origin callback reaches it.

## S3 (boto3)
- `clients/s3.py`: client built from `AWS_ACCESS_KEY_ID/SECRET/REGION`. Methods: `build_key`, `upload_fileobj(fileobj,key,content_type)`, `presigned_get_url(key, expires)`, `delete_object(key)`. Singleton `get_s3()`.
- **Key scheme:** keep bucket slash-free; put the path in the prefix. A good tenant scheme: `<prefix>/<tenant_id>/<filename>` (e.g. `hire-intelligence/<universal_company_id>/<raw-filename>`). Same filename overwrites = natural "reupload".
- **Download:** return a presigned GET url (don't stream through the API). **Delete:** delete the S3 object AND the DB row (guard: admin or uploader). **Reupload:** `PUT /files/{id}` overwrites the object + updates metadata.
- Mock `get_s3` (bound where it's used, i.e. `app.services.files.get_s3`) in tests; do real S3 only for live verification.

## Audit log
A single `audit_logs` table (actor_id/email, action, resource_type/id/label, ip, created_at). A `record_audit(...)` helper called from services on login/upload/download/delete/reupload. Expose a CNB-only `GET /audit` (filters) and `GET /files/{id}/audit` (AuditViewer dep → clients 403).
