@echo off
REM Start TimeTracker with automatic HTTPS
REM Automatically generates certificates and starts all services

echo ==========================================
echo TimeTracker HTTPS Startup
echo ==========================================
echo.

REM Get local IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%
if "%LOCAL_IP%"=="" set LOCAL_IP=192.168.1.100

echo [INFO] Local IP detected: %LOCAL_IP%
echo.

REM Create nginx config if it doesn't exist
if not exist nginx\conf.d\https.conf (
    echo [INFO] Creating nginx HTTPS configuration...
    if not exist nginx\conf.d mkdir nginx\conf.d
    
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
    
    echo [OK] nginx configuration created
    echo.
)

REM Update .env with HTTPS settings
if exist .env (
    echo [INFO] Updating .env with HTTPS settings...
    copy .env .env.backup >nul 2>&1
    
    powershell -Command "$content = Get-Content .env; if ($content -match '^WTF_CSRF_SSL_STRICT=') { $content = $content -replace '^WTF_CSRF_SSL_STRICT=.*', 'WTF_CSRF_SSL_STRICT=true' } else { $content += 'WTF_CSRF_SSL_STRICT=true' }; if ($content -match '^SESSION_COOKIE_SECURE=') { $content = $content -replace '^SESSION_COOKIE_SECURE=.*', 'SESSION_COOKIE_SECURE=true' } else { $content += 'SESSION_COOKIE_SECURE=true' }; if ($content -match '^CSRF_COOKIE_SECURE=') { $content = $content -replace '^CSRF_COOKIE_SECURE=.*', 'CSRF_COOKIE_SECURE=true' } else { $content += 'CSRF_COOKIE_SECURE=true' }; $content | Set-Content .env"
    
    echo [OK] .env updated
    echo.
)

REM Set environment variable for docker-compose
set HOST_IP=%LOCAL_IP%

REM Choose certificate method
echo Select certificate method:
echo   1^) Self-signed (works immediately, shows browser warning^)
echo   2^) mkcert (trusted certificates, requires mkcert installed^)
echo.
set /p CERT_METHOD="Choice [1]: "
if "%CERT_METHOD%"=="" set CERT_METHOD=1

echo.

if "%CERT_METHOD%"=="2" (
    where mkcert >nul 2>&1
    if %errorlevel% equ 0 (
        echo [INFO] Using mkcert for trusted certificates...
        docker-compose -f docker-compose.yml -f docker/docker-compose.https-mkcert.yml up -d
    ) else (
        echo [WARNING] mkcert not found. Using self-signed certificates instead.
        echo    Install mkcert: choco install mkcert
        echo.
        docker-compose -f docker-compose.yml -f docker/docker-compose.https-auto.yml up -d
    )
) else (
    echo [INFO] Using self-signed certificates...
    docker-compose -f docker-compose.yml -f docker/docker-compose.https-auto.yml up -d
)

echo.
echo ==========================================
echo [OK] TimeTracker is starting with HTTPS!
echo ==========================================
echo.
echo Access your application at:
echo   https://localhost
echo   https://%LOCAL_IP%
echo.

if "%CERT_METHOD%"=="1" (
    echo [WARNING] Browser Warning Expected:
    echo    Self-signed certificates will show a security warning.
    echo    Click 'Advanced' - 'Proceed to localhost (unsafe^)' to continue.
    echo.
    echo    For no warnings, run: setup-https-mkcert.bat
)

echo.
echo View logs:
echo   docker-compose logs -f
echo.
echo Stop services:
echo   docker-compose down
echo.
pause

