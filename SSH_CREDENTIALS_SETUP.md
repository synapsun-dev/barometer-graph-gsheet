# SSH & Credentials Configuration — Barometer

**Date** : 2026-06-27  
**Objective** : Ensure reliable git push/pull operations for Barometer CI/CD pipeline and local development.

## Current Status

### ✅ Working Method: HTTPS + Windows Credential Manager
- **Status** : Active and functional
- **Config** : `git config credential.helper=manager`
- **Verification** : `git push origin main` succeeds
- **Advantages** : Simple, secure (credentials stored in Windows vault), no manual key management
- **Disadvantages** : Credentials can expire or get cleared by system updates

### ⚙️ New SSH Setup (Recommended)
- **Status** : Prepared but requires GitHub action
- **Key Type** : RSA 4096-bit
- **Key Path** : `~/.ssh/id_rsa` (generated 2026-06-27 11:40)
- **SSH Config** : `~/.ssh/config` (configured with GitHub settings)
- **Status** : Waiting for public key to be added to GitHub account

---

## SSH Public Key

**⚠️ ACTION REQUIRED: Copy this key to GitHub**

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCwWIL+GMa5V2GPkrvWzv2k9R+jCn4y0+2T0EfwHV1DCQiAOXvL6kGCyUQzFzQP+nlAPe6H/WH/dkYwKViJgFjWm2Rw+j9ZltMGRRckIBmyaJW9+v8q0rVNZ6EIQErTNXEZmc+Jxy5pgbqyRdhn67lPs1CUXZxkw4JXMEt7C+dDKri5Aw6RDLSrfhgpsby4JUDbncvhz6CwG3s5HhaEOd3TNpie9QkUqhPBFajXpw8OT95DUphrdVKc1bZbE/8twylhihe3ietjpUdAdZ6A6cCeJ5i3Yl1jq2LmgSAbKhkOt/qRwnTkmaS+5DBLGKTN6sCSHeQGg11AhtDZFeCMcYuW4QEb5Us6W7fYA9Kb9nVUBLpxftul+gS+H9/2KAh9cA+z26frskrx5zFOwNljdhJaw9evGw9w4QFANWmRaK8Q5Cc1JFh4f46eVqcTxrziBi/+3vS8tm6EK1DKOzvha0NOYACjtQ2J01u/4gdftl1uALQhqmQYgMh+UbhT3/dxJZEre0C1wvpysrY/3UGdmp5GLLKfCSysFVTwlCwvv6RZmaQ1tCGZPi6QpduZXAPolPQPGoMRx0We8ZcM72TlQ/6pVaVBk6HJgoov01abcGahZ2gcuyJX6ICBM2yY6AEr4iop3pbJNlUaHrSeSKSzRIGAWkMeFrvY58Dd+/l/C7KhFw== franck.catanese@synapsun.com
```

### Steps to Add SSH Key to GitHub (via GitHub Web UI)

1. Go to **Settings** → **SSH and GPG keys** (https://github.com/settings/keys)
2. Click **New SSH key**
3. **Title** : `Barometer Local Dev (Windows)` or similar
4. **Key type** : Authentication Key
5. **Key** : Paste the entire key above (starting with `ssh-rsa` and ending with the email)
6. Click **Add SSH key**

---

## Option 1: Continue Using HTTPS + Credential Manager (Current)

### Configuration
```bash
git config credential.helper manager
git remote set-url origin https://github.com/synapsun-dev/barometer-graph-gsheet.git
```

### Test
```bash
git push origin main
# If prompted, enter GitHub username and personal access token (or password)
```

### When Credentials Expire
- Clear cached credentials: `git credential-manager delete github.com`
- Next push will prompt for credentials again

### ✅ Best For
- Simple local development
- Windows users comfortable with Credential Manager
- Frequent credential updates

---

## Option 2: Migrate to SSH (Recommended for CI/CD)

### 1. Add Public Key to GitHub
Follow the steps above ("Steps to Add SSH Key to GitHub").

### 2. Update Remote URL
```bash
cd C:\Claude\Synapsun\Barometer
git remote set-url origin git@github.com:synapsun-dev/barometer-graph-gsheet.git
```

### 3. Verify Remote Changed
```bash
git remote -v
# Should show:
# origin  git@github.com:synapsun-dev/barometer-graph-gsheet.git (fetch)
# origin  git@github.com:synapsun-dev/barometer-graph-gsheet.git (push)
```

### 4. Test SSH Connection
```bash
ssh -T git@github.com
# Expected output: Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.
```

### 5. Test git push with SSH
```bash
git push origin main
# Should succeed without prompting for credentials
```

### ✅ Best For
- Automation (CI/CD, scheduled scripts)
- Better security (key-based authentication)
- No credential expiry issues
- GitHub Actions workflows

---

## Current Configuration Files

### `~/.ssh/config`
```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_rsa
    AddKeysToAgent yes
    StrictHostKeyChecking accept-new
    IdentitiesOnly yes
```

**Permissions** : `rw-------` (600) ✅

### `~/.ssh/id_rsa` (Private Key)
**Permissions** : `rw-------` (600) ✅  
**Passphrase** : None (blank passphrase for automation compatibility)

### `~/.ssh/id_rsa.pub` (Public Key)
Contains the RSA public key above.

### `~/.ssh/known_hosts`
Auto-populated with GitHub's host key on first SSH connection.

---

## Troubleshooting

### SSH Test Fails: "Permission denied (publickey)"
**Cause** : Public key not yet added to GitHub account.  
**Fix** : Follow "Steps to Add SSH Key to GitHub" above.

### Git Still Uses HTTPS After Adding SSH Key
**Cause** : Remote URL not updated.  
**Fix** : Run `git remote set-url origin git@github.com:synapsun-dev/barometer-graph-gsheet.git`

### SSH Works but Prompts for Passphrase
**Cause** : SSH key has a passphrase.  
**Fix** : Use ssh-agent to store passphrase (automatic in Git Bash), or regenerate key with empty passphrase.

### Credential Manager Still Prompts
**Cause** : Credential cache expired or corrupted.  
**Fix** : Clear and re-authenticate:
```bash
git credential-manager delete github.com
git push origin main  # Prompts for credentials again
```

---

## Recommended Next Steps

1. **Immediate** (No Breaking Changes)
   - ✅ SSH keys generated locally
   - ✅ SSH config prepared
   - ✅ HTTPS + Credential Manager still works for local development
   - **Action** : Keep current setup, periodically verify credentials work

2. **Short Term** (Safer Automation)
   - Add public SSH key to GitHub account (web UI)
   - Update remote URL to SSH: `git remote set-url origin git@github.com:synapsun-dev/barometer-graph-gsheet.git`
   - Test: `git push origin main`
   - **Benefit** : Eliminates credential expiry issues for scheduled GitHub Actions

3. **Future** (Hardening)
   - Generate ED25519 key as secondary key for rotation
   - Document SSH key rotation policy in project
   - Consider GitHub Deploy Keys for read-only access to this repo from other services

---

## Security Notes

- ✅ Private key (`id_rsa`) is NOT shared and has secure permissions
- ✅ Public key (`id_rsa.pub`) can be freely shared and added to GitHub
- ✅ SSH key has blank passphrase for automation (suitable for local CI scripts)
- ✅ No credentials stored in git config (only remote URL)
- ⚠️ If private key is ever compromised, remove it from GitHub immediately and regenerate a new pair

---

## References

- GitHub SSH Documentation: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- Git Credential Manager: https://github.com/git-ecosystem/git-credential-manager
- SSH Best Practices: https://man.openbsd.org/ssh_config
