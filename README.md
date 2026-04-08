# Backup API

Django REST backend for login, OTP-based password reset by email, and cloud backup of user music metadata.

## Features

- Login with email and password (JWT access + refresh token)
- Register account with email and password
- Password reset using OTP sent to email
- Backup and restore:
  - favorite songs
  - playlists
  - downloaded songs metadata (not actual audio files)

## Setup

```bash
cd backupapi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Default base URL: `http://127.0.0.1:8000`

## API Endpoints

### Auth

- `POST /api/auth/register/`
  - body: `{ "email": "...", "password": "...", "name": "..." }`
- `POST /api/auth/login/`
  - body: `{ "email": "...", "password": "..." }`
- `POST /api/auth/token/refresh/`
  - body: `{ "refresh": "..." }`

### Password reset (OTP)

- `POST /api/auth/password-reset/request-otp/`
  - body: `{ "email": "..." }`
- `POST /api/auth/password-reset/confirm-otp/`
  - body: `{ "email": "...", "otp": "123456", "password": "..." }`

This project is configured for SMTP email delivery via environment variables.

Set these before running:

- `EMAIL_BACKEND` (optional, default: `django.core.mail.backends.smtp.EmailBackend`)
- `EMAIL_HOST` (required for real email sending)
- `EMAIL_PORT` (default: `587`)
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS` (default: `true`)
- `EMAIL_USE_SSL` (default: `false`)
- `DEFAULT_FROM_EMAIL` (optional)

### Backups (JWT required)

- `GET /api/backups/me/` - Fetch current backup data
- `PUT /api/backups/me/` - Replace backup data
- `POST /api/backups/bulk-upload/` - Bulk upload favorites/playlists/downloads
  - `mode: "append"` (default) to merge
  - `mode: "replace"` to overwrite
- `POST /api/backups/bulk-restore/` - Bulk restore in one call
  - optional `include` list for selective restore
  - body:
    ```json
    {
      "favorite_songs": [],
      "playlists": [],
      "downloaded_songs": []
    }
    ```

## Backup and Restore Documentation

This backend stores **music metadata only**. It does not upload/download actual audio files.

### What is backed up

- `favorite_songs`: list of favorite song objects
- `playlists`: list of playlist objects (each may include a songs list)
- `downloaded_songs`: list of downloaded song metadata (id/title/path/etc.)

You can store extra keys inside each object; backend keeps JSON as-is.

### Data contract

`PUT /api/backups/me/` expects:

```json
{
  "favorite_songs": [],
  "playlists": [],
  "downloaded_songs": []
}
```

All three keys must be JSON arrays.

`POST /api/backups/bulk-upload/` expects:

```json
{
  "mode": "append",
  "favorite_songs": [],
  "playlists": [],
  "downloaded_songs": []
}
```

`POST /api/backups/bulk-restore/` expects (optional):

```json
{
  "include": ["favorite_songs", "playlists", "downloaded_songs"]
}
```

If `include` is omitted, all backup arrays are returned.

### Backup flow (App -> Server)

1. User logs in and gets JWT access token.
2. App collects current local metadata:
   - favorites
   - playlists
   - downloaded song metadata
3. App sends one `PUT /api/backups/me/` request with full snapshot.
4. Server overwrites previous snapshot for that user.

### Restore flow (Server -> App)

1. User logs in and gets JWT access token.
2. App calls `GET /api/backups/me/`.
3. App receives latest snapshot.
4. App merges or replaces local data as needed.
5. For `downloaded_songs`, app should re-download missing files later if local files are unavailable.

### cURL: Backup snapshot

```bash
curl -X PUT "$BASE_URL/api/backups/me/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "favorite_songs": [
      { "id": "song_1", "title": "Night Drive", "artist": "X" }
    ],
    "playlists": [
      {
        "id": "playlist_1",
        "name": "Road Trip",
        "songs": [
          { "id": "song_1", "title": "Night Drive" }
        ]
      }
    ],
    "downloaded_songs": [
      { "id": "song_1", "title": "Night Drive", "local_path": "/storage/emulated/0/Music/night_drive.m4a" }
    ]
  }'
```

### cURL: Restore snapshot

```bash
curl -X GET "$BASE_URL/api/backups/me/" \
  -H "Authorization: Bearer $ACCESS"
```

### cURL: Bulk restore (all sections)

```bash
curl -X POST "$BASE_URL/api/backups/bulk-restore/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### cURL: Bulk restore (selective sections)

```bash
curl -X POST "$BASE_URL/api/backups/bulk-restore/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "include": ["favorite_songs", "playlists"]
  }'
```

### cURL: Bulk upload (append mode)

```bash
curl -X POST "$BASE_URL/api/backups/bulk-upload/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "append",
    "favorite_songs": [
      { "id": "song_2", "title": "Starlight", "artist": "Y" }
    ],
    "playlists": [
      { "id": "playlist_2", "name": "Focus", "songs": [] }
    ],
    "downloaded_songs": [
      { "id": "song_2", "title": "Starlight", "local_path": "/storage/emulated/0/Music/starlight.m4a" }
    ]
  }'
```

### cURL: Bulk upload (replace mode)

```bash
curl -X POST "$BASE_URL/api/backups/bulk-upload/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "replace",
    "favorite_songs": [],
    "playlists": [],
    "downloaded_songs": []
  }'
```

### Expected restore response example

```json
{
  "favorite_songs": [
    { "id": "song_1", "title": "Night Drive", "artist": "X" }
  ],
  "playlists": [
    {
      "id": "playlist_1",
      "name": "Road Trip",
      "songs": [
        { "id": "song_1", "title": "Night Drive" }
      ]
    }
  ],
  "downloaded_songs": [
    { "id": "song_1", "title": "Night Drive", "local_path": "/storage/emulated/0/Music/night_drive.m4a" }
  ],
  "updated_at": "2026-04-07T12:00:00Z"
}
```

## API Testing Guide (with curl)

Open a second terminal and set environment variables:

```bash
BASE_URL="http://127.0.0.1:8000"
EMAIL="testuser@example.com"
PASSWORD="TestPass123!"
```

### 1) Register user

```bash
curl -X POST "$BASE_URL/api/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'",
    "name": "Test User"
  }'
```

Expected: `201 Created` and user info JSON.

### 2) Login and get JWT tokens

```bash
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'"
  }')

echo "$LOGIN_RESPONSE"
```

Extract tokens:

```bash
ACCESS=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["access"])' <<< "$LOGIN_RESPONSE")
REFRESH=$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["refresh"])' <<< "$LOGIN_RESPONSE")
echo "ACCESS=$ACCESS"
echo "REFRESH=$REFRESH"
```

### 3) Save backup snapshot (favorites/playlists/download metadata)

```bash
curl -X PUT "$BASE_URL/api/backups/me/" \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
    "favorite_songs": [
      { "id": "yt_1", "title": "Song One", "artist": "Artist A" }
    ],
    "playlists": [
      {
        "id": "pl_1",
        "name": "My Playlist",
        "songs": [{ "id": "yt_1", "title": "Song One" }]
      }
    ],
    "downloaded_songs": [
      { "id": "yt_1", "title": "Song One", "local_path": "/storage/emulated/0/Music/song1.m4a" }
    ]
  }'
```

Expected: `200 OK` and the updated snapshot JSON.

### 4) Fetch backup snapshot

```bash
curl -X GET "$BASE_URL/api/backups/me/" \
  -H "Authorization: Bearer $ACCESS"
```

Expected: `200 OK` with `favorite_songs`, `playlists`, and `downloaded_songs`.

### 5) Refresh access token

```bash
curl -X POST "$BASE_URL/api/auth/token/refresh/" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "'"$REFRESH"'"
  }'
```

Expected: `200 OK` with a new `access` token.

### 6) Password reset flow (OTP)

Request OTP by email:

```bash
curl -X POST "$BASE_URL/api/auth/password-reset/request-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'"
  }'
```

Expected: `200 OK`.

If SMTP is not configured correctly, the OTP endpoint returns an SMTP configuration error.

Confirm reset with OTP:

```bash
OTP="PASTE_OTP_FROM_SERVER_LOGS"
NEW_PASSWORD="NewPass123!"

curl -X POST "$BASE_URL/api/auth/password-reset/confirm-otp/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "otp": "'"$OTP"'",
    "password": "'"$NEW_PASSWORD"'"
  }'
```

Login with the new password:

```bash
curl -X POST "$BASE_URL/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'"$EMAIL"'",
    "password": "'"$NEW_PASSWORD"'"
  }'
```

## Quick Troubleshooting

- `401 Unauthorized`: Missing/expired token, login again or refresh token.
- `400 Bad Request`: Body format mismatch; ensure JSON keys match docs exactly.
- OTP not received: confirm server is running and check terminal logs for OTP output.
- `Invalid or expired OTP`: OTP is wrong, already used, or older than 10 minutes; request a new OTP.

## Production Deployment (VPS + Nginx on custom port)

This app can run with Gunicorn on localhost and be exposed by Nginx on a port other than `80`, for example `8081`.

### 1) Server setup

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx
```

### 2) App setup

```bash
cd /opt
sudo mkdir -p backupapi
sudo chown -R $USER:$USER backupapi
cd backupapi
# copy project files here
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Set `.env` values for production:
- `DJANGO_SECRET_KEY` = strong random secret
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS=103.250.133.68`
- SMTP values

Then run:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
```

### 3) Gunicorn systemd service (internal app port `9000`)

Create `/etc/systemd/system/backupapi.service`:

```ini
[Unit]
Description=Gunicorn for backupapi Django app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/backupapi
EnvironmentFile=/opt/backupapi/.env
ExecStart=/opt/backupapi/.venv/bin/gunicorn backupapi.wsgi:application --bind 127.0.0.1:9000 --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo chown -R www-data:www-data /opt/backupapi
sudo systemctl daemon-reload
sudo systemctl enable backupapi
sudo systemctl start backupapi
sudo systemctl status backupapi
```

### 4) Nginx site on custom public port (`8081`)

Create `/etc/nginx/sites-available/backupapi`:

```nginx
server {
    listen 8081;
    server_name 103.250.133.68;

    client_max_body_size 25M;

    location /static/ {
        alias /opt/backupapi/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site and reload:

```bash
sudo ln -s /etc/nginx/sites-available/backupapi /etc/nginx/sites-enabled/backupapi
sudo nginx -t
sudo systemctl reload nginx
```

### 5) Open firewall

Allow your custom port:

```bash
sudo ufw allow 8081/tcp
```

### 6) Access URL

Use:

`http://103.250.133.68:8081`

Your existing project on `103.250.133.68:80` will remain untouched.
