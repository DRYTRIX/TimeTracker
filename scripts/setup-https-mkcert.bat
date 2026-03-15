@echo off
REM Setup HTTPS for TimeTracker using mkcert
REM Works with localhost and IP addresses - NO certificate warnings!

echo ==========================================
echo TimeTracker HTTPS Setup with mkcert
echo ==========================================
echo.

REM Check if mkcert is installed
where mkcert >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] mkcert is not installed!
    echo.
    echo Install mkcert:
    echo   Using Chocolatey: choco install mkcert
    echo   Using Scoop:      scoop install mkcert
    echo.
    pause
    exit /b 1
)

echo [OK] mkcert found
echo.

REM Install local CA
echo Installing local Certificate Authority...
mkcert -install
echo [OK] Local CA installed
echo.

REM Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.100

echo Detected local IP: %LOCAL_IP%
echo.

REM Create directories
if not exist nginx\ssl mkdir nginx\ssl
if not exist nginx\conf.d mkdir nginx\conf.d

REM Generate certificates
echo Generating certificates...
mkcert -key-file nginx\ssl\key.pem -cert-file nginx\ssl\cert.pem localhost 127.0.0.1 ::1 %LOCAL_IP% *.local

echo [OK] Certificates generated
echo.

REM Create nginx config
(
echo server {
echo     listen 80;
echo     server_name _;
echo     return 301 https://$host$request_uri;
echo }
echo.
echo server {
echo     listen 443 ssl http2;
echo     server_name _;
echo.
echo     ssl_certificate /etc/nginx/ssl/cert.pem;
echo     ssl_certificate_key /etc/nginx/ssl/key.pem;
echo.
echo     ssl_protocols TLSv1.2 TLSv1.3;
echo     ssl_ciphers HIGH:!aNULL:!MD5;
echo     ssl_prefer_server_ciphers on;
echo.
echo     add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
echo     add_header X-Frame-Options "DENY" always;
echo     add_header X-Content-Type-Options "nosniff" always;
echo.
echo     location / {
echo         proxy_pass http://app:8080;
echo         proxy_set_header Host $host;
echo         proxy_set_header X-Real-IP $remote_addr;
echo         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
echo         proxy_set_header X-Forwarded-Proto $scheme;
echo         
echo         proxy_http_version 1.1;
echo         proxy_set_header Upgrade $http_upgrade;
echo         proxy_set_header Connection "upgrade";
echo     }
echo }
) > nginx\conf.d\https.conf

echo [OK] nginx config created
echo.

REM Create docker-compose override
(
echo services:
echo   nginx:
echo     image: nginx:alpine
echo     container_name: timetracker-nginx
echo     ports:
echo       - "80:80"
echo       - "443:443"
echo     volumes:
echo       - ./nginx/conf.d:/etc/nginx/conf.d:ro
echo       - ./nginx/ssl:/etc/nginx/ssl:ro
echo     depends_on:
echo       - app
echo     restart: unless-stopped
echo.
echo   app:
echo     ports: []
echo     environment:
echo       - WTF_CSRF_SSL_STRICT=true
echo       - SESSION_COOKIE_SECURE=true
echo       - CSRF_COOKIE_SECURE=true
) > docker-compose.https.yml

echo [OK] docker-compose.https.yml created
echo.

REM Update .env if exists
if exist .env (
    copy .env .env.backup >nul
    powershell -Command "$content = Get-Content .env; if ($content -match '^WTF_CSRF_SSL_STRICT=') { $content = $content -replace '^WTF_CSRF_SSL_STRICT=.*', 'WTF_CSRF_SSL_STRICT=true' } else { $content += 'WTF_CSRF_SSL_STRICT=true' }; if ($content -match '^SESSION_COOKIE_SECURE=') { $content = $content -replace '^SESSION_COOKIE_SECURE=.*', 'SESSION_COOKIE_SECURE=true' } else { $content += 'SESSION_COOKIE_SECURE=true' }; if ($content -match '^CSRF_COOKIE_SECURE=') { $content = $content -replace '^CSRF_COOKIE_SECURE=.*', 'CSRF_COOKIE_SECURE=true' } else { $content += 'CSRF_COOKIE_SECURE=true' }; $content | Set-Content .env"
    echo [OK] .env updated
) else (
    echo [WARNING] No .env file - create from env.example
)

echo.
echo ==========================================
echo [OK] HTTPS Setup Complete!
echo ==========================================
echo.
echo Start with HTTPS:
echo   docker-compose -f docker-compose.yml -f docker-compose.https.yml up -d
echo.
echo Access at:
echo   https://localhost
echo   https://%LOCAL_IP%
echo.
echo For other devices:
echo   1. Find CA: mkcert -CAROOT
echo   2. Copy rootCA.pem to device
echo   3. Import as trusted certificate
echo.
pause

