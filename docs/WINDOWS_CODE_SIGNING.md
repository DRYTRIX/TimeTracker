# Windows Code Signing Guide

## The "Unknown Publisher" Warning

When users try to install your Windows application, they may see a security warning saying "Unknown Publisher" because the executable is not digitally signed with a code signing certificate.

## Why Code Signing Matters

- **Trust**: Users see your company/organization name instead of "Unknown Publisher"
- **Security**: Windows SmartScreen won't block your application
- **User Experience**: Users don't need to click "More info" → "Run anyway"
- **Professional**: Makes your application look more trustworthy

## Solutions

### Option 1: Commercial Code Signing Certificate (Recommended for Production)

For production releases, you should obtain a code signing certificate from a trusted Certificate Authority (CA).

#### Where to Get Certificates

**Popular Providers:**
- **Sectigo** (formerly Comodo) - ~$200-400/year
- **DigiCert** - ~$400-600/year (more expensive, very trusted)
- **GlobalSign** - ~$300-500/year
- **K Software** - ~$150-300/year (cheaper option)

**Types of Certificates:**
1. **OV (Organization Validation)** - Cheaper, requires business verification
2. **EV (Extended Validation)** - More expensive, requires extensive verification, better SmartScreen reputation

#### Requirements

- **Business Entity**: You need a registered business (LLC, Corp, etc.)
- **Identity Verification**: CA will verify your business
- **Personal Information**: Name, address, business details
- **Cost**: $150-$600 per year

#### Certificate Formats

Code signing certificates come in two formats:

1. **PFX/PKCS#12** (`.pfx` or `.p12` file) - Most common, contains both certificate and private key
2. **SPC/PVK** - Older format (separate `.spc` and `.pvk` files)

### Option 2: Self-Signed Certificate (For Testing/Development)

Self-signed certificates are free but:
- ❌ Still show "Unknown Publisher" (but different message)
- ❌ SmartScreen will still warn users
- ✅ Useful for internal/testing purposes
- ✅ Can be useful for open-source projects with no budget

### Option 3: Build Reputation Over Time (Open Source)

For open-source projects without a budget:
- Start without signing
- As your app gains users and downloads, Windows Defender SmartScreen builds reputation
- After ~10,000+ downloads, Windows may stop showing warnings
- This takes time and many downloads

## Setting Up Code Signing

### Step 1: Obtain a Certificate

**For Commercial Use:**
1. Purchase a code signing certificate from a CA
2. Complete identity verification process
3. Download the certificate file (usually `.pfx` format)

**For Testing (Self-Signed):**
```powershell
# Create a self-signed certificate (Windows)
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=TimeTracker" -CertStoreLocation Cert:\CurrentUser\My -HashAlgorithm SHA256
$pwd = ConvertTo-SecureString -String "YourPassword123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "codesign.pfx" -Password $pwd
```

### Step 2: Configure electron-builder

electron-builder uses environment variables for code signing certificates.

**Required Environment Variables:**

- `CSC_LINK` - Base64-encoded certificate (PFX file)
- `CSC_KEY_PASSWORD` - Password for the certificate
- OR
- `CSC_LINK_FILE` - Path to certificate file (for local builds)
- `CSC_KEY_PASSWORD` - Password for the certificate

### Step 3: Local Build Setup

**Option A: Using Certificate File (Local Development)**

1. Store your certificate in a secure location (e.g., `desktop/certs/codesign.pfx`)
2. Set environment variables before building:

```powershell
# Windows PowerShell
$env:CSC_LINK_FILE = "desktop/certs/codesign.pfx"
$env:CSC_KEY_PASSWORD = "YourCertificatePassword"
npm run build:win
```

```bash
# Linux/macOS
export CSC_LINK_FILE="desktop/certs/codesign.pfx"
export CSC_KEY_PASSWORD="YourCertificatePassword"
npm run build:win
```

**Option B: Using Base64-Encoded Certificate (CI/CD)**

1. Encode your certificate to Base64:

```powershell
# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("codesign.pfx"))
```

```bash
# Linux/macOS
base64 -i codesign.pfx | pbcopy
```

2. Use as environment variable:

```bash
export CSC_LINK="<base64-encoded-certificate>"
export CSC_KEY_PASSWORD="YourCertificatePassword"
```

### Step 4: CI/CD Setup (GitHub Actions)

For automated signing in GitHub Actions:

1. **Store Certificate as GitHub Secret:**
   - Go to Repository → Settings → Secrets and variables → Actions
   - Add secret: `WINDOWS_CODE_SIGN_CERT` (Base64-encoded certificate)
   - Add secret: `WINDOWS_CODE_SIGN_PASSWORD` (Certificate password)

2. **Update Workflow:**
   See `.github/workflows/build-desktop.yml` for example configuration.

### Step 5: Update package.json (Optional)

You can add signing configuration directly in `package.json`:

```json
{
  "build": {
    "win": {
      "sign": "default"  // or path to signing tool
    }
  }
}
```

However, using environment variables (as shown above) is more secure and recommended.

## Testing Code Signing

After signing, verify your executable:

```powershell
# Check if file is signed
Get-AuthenticodeSignature "dist/TimeTracker-4.10.1-x64.exe"

# Should show:
# Status: Valid
# SignerCertificate: [Your Certificate]
```

## Certificate Storage

### Security Best Practices

1. **Never commit certificates to Git**
   - Add `*.pfx`, `*.p12`, `*.spc`, `*.pvk` to `.gitignore`
   - Store certificates in secure locations (password manager, vault)

2. **Use GitHub Secrets for CI/CD**
   - Store Base64-encoded certificate as secret
   - Store password as separate secret

3. **Limit Access**
   - Only trusted team members should have certificate access
   - Use separate certificates for development vs. production

4. **Certificate Expiration**
   - Most certificates are valid for 1-3 years
   - Set reminders to renew before expiration
   - Update certificates in CI/CD before they expire

## Example: GitHub Actions Workflow

```yaml
- name: Build Windows
  working-directory: desktop
  env:
    CSC_LINK: ${{ secrets.WINDOWS_CODE_SIGN_CERT }}
    CSC_KEY_PASSWORD: ${{ secrets.WINDOWS_CODE_SIGN_PASSWORD }}
  run: npm run build:win
```

## Troubleshooting

### "Certificate not found" Error

- Check that `CSC_LINK` or `CSC_LINK_FILE` is set correctly
- Verify certificate file exists and is readable
- Ensure certificate format is correct (PFX/PKCS#12)

### "Invalid password" Error

- Verify `CSC_KEY_PASSWORD` matches certificate password
- Check for special characters in password (may need escaping)
- Ensure password is correct for the certificate file

### "Certificate expired" Error

- Check certificate expiration date
- Renew certificate if expired
- Update certificate in CI/CD secrets

### Still Shows "Unknown Publisher"

- Verify certificate was applied (check file signature)
- Wait a few minutes - certificate validation can take time
- For new certificates, SmartScreen may still warn initially
- EV certificates get better SmartScreen reputation faster

## Cost-Benefit Analysis

### Commercial Certificate
- **Cost**: $150-600/year
- **Benefit**: Immediate trust, professional appearance
- **Best for**: Commercial applications, production releases

### Self-Signed Certificate
- **Cost**: Free
- **Benefit**: Basic signing (still shows warning)
- **Best for**: Internal tools, testing, development

### No Certificate
- **Cost**: Free
- **Benefit**: None
- **Best for**: Open-source projects building reputation, early development

## Next Steps

1. **Decide on approach** (commercial vs. self-signed vs. none)
2. **Obtain certificate** (if using commercial/self-signed)
3. **Configure environment variables** (local builds)
4. **Set up GitHub Secrets** (for CI/CD)
5. **Test signing** (verify executable is signed)
6. **Update workflows** (automate signing in CI/CD)

## Additional Resources

- [electron-builder Code Signing Documentation](https://www.electron.build/code-signing)
- [Windows Code Signing Best Practices](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptographic-service-providers)
- [Certificate Authority List](https://cabforum.org/)
