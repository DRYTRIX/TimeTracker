# Quick Start: Windows Code Signing

## Problem

When users download your Windows executable, they see:
> **Windows protected your PC**
> 
> Microsoft Defender SmartScreen prevented an unrecognized app from starting. Running this app might put your PC at risk.

## Solution

Sign your Windows executable with a code signing certificate.

## Quick Options

### Option 1: Buy a Certificate (Recommended for Production)

**Cost:** $150-600/year  
**Result:** Shows your company name, trusted by Windows

1. **Purchase a certificate:**
   - [Sectigo](https://sectigo.com/ssl-certificates-tls/code-signing) (~$200/year)
   - [DigiCert](https://www.digicert.com/code-signing/) (~$400/year)
   - [K Software](https://www.ksoftware.net/) (~$150/year - cheapest)

2. **Complete verification:**
   - Provide business details
   - Verify your identity
   - Download certificate (`.pfx` file)

3. **For Local Builds:**
   ```powershell
   # Windows PowerShell
   $env:CSC_LINK_FILE = "path/to/certificate.pfx"
   $env:CSC_KEY_PASSWORD = "YourCertificatePassword"
   npm run build:win
   ```

4. **For GitHub Actions (CI/CD):**
   - Go to: Repository → Settings → Secrets and variables → Actions
   - Add secret: `WINDOWS_CODE_SIGN_CERT` (Base64-encoded certificate)
   - Add secret: `WINDOWS_CODE_SIGN_PASSWORD` (Certificate password)
   - Builds will automatically sign executables

**To encode certificate for GitHub Secret:**
```powershell
# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx")) | Out-File -Encoding ASCII cert.txt
# Copy content of cert.txt to GitHub Secret
```

### Option 2: Self-Signed Certificate (Free, Testing Only)

**Cost:** Free  
**Result:** Still shows warning, but file is signed

```powershell
# Create self-signed certificate (Windows PowerShell)
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=TimeTracker" -CertStoreLocation Cert:\CurrentUser\My -HashAlgorithm SHA256
$pwd = ConvertTo-SecureString -String "YourPassword123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "codesign.pfx" -Password $pwd

# Use for signing
$env:CSC_LINK_FILE = "codesign.pfx"
$env:CSC_KEY_PASSWORD = "YourPassword123!"
npm run build:win
```

**Note:** Self-signed certificates still show warnings to users. Only use for testing.

### Option 3: Wait for Reputation (Open Source, No Budget)

**Cost:** Free  
**Result:** After 10,000+ downloads, Windows may stop showing warnings

- Don't sign initially
- As downloads increase, Windows Defender SmartScreen builds reputation
- Takes time and many downloads
- Still shows "Unknown Publisher" initially

## Verification

After building, verify the executable is signed:

```powershell
Get-AuthenticodeSignature "dist/TimeTracker-4.10.1-x64.exe"
```

Should show:
```
Status: Valid
SignerCertificate: [Your Certificate Info]
```

## Next Steps

1. **Choose an option** (Commercial/self-signed/none)
2. **Get certificate** (if using commercial/self-signed)
3. **Configure signing** (local builds or CI/CD)
4. **Test signing** (verify executable is signed)
5. **Build and distribute** (signed executables)

For detailed instructions, see [Windows Code Signing Guide](WINDOWS_CODE_SIGNING.md).
