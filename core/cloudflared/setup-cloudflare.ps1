$envFile = ".env"

if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found."
    exit 1
}

# Check if cloudflared is installed
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Error "cloudflared is not installed or not in PATH."
    exit 1
}

# Load .env
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
    }
}

$tunnelId = $envVars['CLOUDFLARE_TUNNEL_ID']
$tunnelName = $envVars['CLOUDFLARE_TUNNEL_NAME']
$domainName = $envVars['DOMAIN_NAME']

if ([string]::IsNullOrWhiteSpace($tunnelName)) {
    Write-Error "CLOUDFLARE_TUNNEL_NAME is not defined in .env"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($domainName)) {
    Write-Error "DOMAIN_NAME is not defined in .env"
    exit 1
}

$isNewTunnel = [string]::IsNullOrWhiteSpace($tunnelId)

if ($isNewTunnel) {
    Write-Host "CLOUDFLARE_TUNNEL_ID is empty. Creating or finding tunnel '$tunnelName'..."
    
    # Try to create tunnel
    $createOutput = cloudflared tunnel create $tunnelName 2>&1 | Out-String
    
    # Extract ID from output: "Created tunnel <name> with id <id>"
    if ($createOutput -match 'with id ([a-f0-9-]+)') {
        $tunnelId = $Matches[1]
        Write-Host "Created tunnel with ID: $tunnelId"
    } elseif ($createOutput -match "already exists") {
        Write-Host "Tunnel '$tunnelName' already exists. Fetching its ID..."
        $listOutput = cloudflared tunnel list 2>&1 | Out-String
        # Pattern: <id> <name> <created> <connections>
        if ($listOutput -match "([a-f0-9-]+)\s+$tunnelName") {
            $tunnelId = $Matches[1]
            Write-Host "Found existing tunnel ID: $tunnelId"
        } else {
            Write-Error "Could not find ID for existing tunnel '$tunnelName' in list output."
            exit 1
        }
    } else {
        Write-Error "Failed to create or find tunnel: $createOutput"
        exit 1
    }
} else {
    Write-Host "CLOUDFLARE_TUNNEL_ID already exists: $tunnelId. Checking configuration..."
}

# Ensure CNAMEs (can be run multiple times safely)
Write-Host "Ensuring CNAME for $domainName..."
$dns1 = cloudflared tunnel route dns $tunnelId $domainName 2>&1
Write-Host "Ensuring CNAME for *.$domainName..."
$dns2 = cloudflared tunnel route dns $tunnelId "*.$domainName" 2>&1

# Ensure credentials file is in place
$credentialsDest = "hub/cloudflared/config/credentials.json"
if (-not (Test-Path $credentialsDest)) {
    $credentialsSource = Join-Path $env:USERPROFILE ".cloudflared\$tunnelId.json"
    if (Test-Path $credentialsSource) {
        Write-Host "Copying credentials from $credentialsSource to $credentialsDest..."
        if (-not (Test-Path "hub/cloudflared/config")) {
            New-Item -ItemType Directory -Path "hub/cloudflared/config" -Force | Out-Null
        }
        Copy-Item -Path $credentialsSource -Destination $credentialsDest -Force
    } else {
        Write-Warning "Credentials file missing at $credentialsDest and could not find source at $credentialsSource."
        Write-Host "Continuing since tunnel ID is known, but Docker container may fail to start without credentials.json."
    }
} else {
    Write-Host "Credentials file already exists at $credentialsDest."
}

# ONLY update .env after everything else is successful
if ($isNewTunnel -and $tunnelId) {
    Write-Host "Updating $envFile with CLOUDFLARE_TUNNEL_ID=$tunnelId"
    $content = Get-Content $envFile
    $newContent = $content | ForEach-Object {
        if ($_ -match '^CLOUDFLARE_TUNNEL_ID=') {
            "CLOUDFLARE_TUNNEL_ID=$tunnelId"
        } else {
            $_
        }
    }
    $newContent | Set-Content $envFile
}

Write-Host "Cloudflare setup complete."
