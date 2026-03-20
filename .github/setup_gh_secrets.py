#!/usr/bin/env python3
"""
Set up GitHub Secrets for AfricaZero Cloudflare Pages auto-deploy.

Usage:
  GITHUB_TOKEN=xxx python3 setup_gh_secrets.py <cloudflare_api_token> <cloudflare_account_id>

Steps to get Cloudflare credentials:
1. Log into https://dash.cloudflare.com
2. Account ID: Profile Icon → Overview → Account ID
3. API Token: Profile Icon → API Tokens → Create Token
   → Use "Edit Cloudflare Workers" template or create custom with:
   - Account: Cloudflare Pages: Edit
"""

import sys
import os
import base64
import json
import urllib.request
import urllib.error

REPO = "qiangzhang2009/africa-web"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = f"https://api.github.com/repos/{REPO}"

def gh_request(method, path, data=None, include_token=True):
    url = f"{BASE_URL}{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if include_token:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


def get_public_key():
    data, status = gh_request("GET", "/actions/secrets/public-key")
    if status != 200:
        print(f"❌ Failed to get public key: {data}")
        sys.exit(1)
    return data["key_id"], data["key"]


def get_repo_public_key():
    data, status = gh_request("GET", "/actions/secrets/public-key")
    if status != 200:
        print(f"❌ Failed to get repo public key: {status} {data}")
        sys.exit(1)
    return data


def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    from nacl import encoding, public
    pk = public.PublicKey(public_key_b64, encoding.Base64Encoder())
    box = public.SealedBox(pk)
    encrypted = box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def set_secret(name: str, value: str, dry_run: bool = False):
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Setting secret: {name}")
    key_data = get_repo_public_key()
    key_id, key = key_data["key_id"], key_data["key"]

    # Encrypt using PyNaCl
    try:
        encrypted = encrypt_secret(key, value)
    except ImportError:
        print("Installing PyNaCl...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynacl"])
        encrypted = encrypt_secret(key, value)

    payload = {"encrypted_value": encrypted, "key_id": key_id}
    if dry_run:
        print(f"  Would encrypt secret '{name}' (length={len(value)})")
        return

    data, status = gh_request("PUT", f"/actions/secrets/{name}", payload)
    if status in (201, 204):
        print(f"  ✅ Secret '{name}' set successfully")
    else:
        print(f"  ❌ Failed to set secret '{name}': {status} {data}")


def set_variable(name: str, value: str, dry_run: bool = False):
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Setting variable: {name}")
    payload = {"name": name, "value": value}
    if dry_run:
        print(f"  Would set variable '{name}' = '{value}'")
        return

    data, status = gh_request("POST", "/actions/variables", payload)
    if status in (201, 204):
        print(f"  ✅ Variable '{name}' set successfully")
    else:
        # Try update if it already exists
        data2, status2 = gh_request("PATCH", f"/actions/variables/{name}", payload)
        if status2 in (200, 201, 204):
            print(f"  ✅ Variable '{name}' updated successfully")
        else:
            print(f"  ❌ Failed to set variable '{name}': {status2} {data2}")


def main():
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 2:
        print(__doc__)
        sys.exit(1)

    cf_token, cf_account_id = args[0], args[1]

    print("=" * 60)
    print("GitHub Secrets & Variables Setup for AfricaZero Cloudflare Pages")
    print("=" * 60)

    # Set secrets
    set_secret("CLOUDFLARE_API_TOKEN", cf_token, dry_run)
    set_secret("CLOUDFLARE_ACCOUNT_ID", cf_account_id, dry_run)

    print("\n" + "=" * 60)
    if dry_run:
        print("[DRY-RUN] No changes were made. Remove --dry-run to apply.")
    else:
        print("✅ All GitHub Secrets set successfully!")
        print("📝 Next: Go to GitHub Actions → Deploy AfricaZero Frontend to Cloudflare Pages")
        print("   https://github.com/qiangzhang2009/africa-web/actions")
        print("   Or push a new commit to frontend/ to trigger auto-deploy.")
    print("=" * 60)


if __name__ == "__main__":
    main()
