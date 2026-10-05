# Security Policy

The **Eagle-1-64Bit** maintainers and community take the security of this project seriously. We appreciate the responsible disclosure of any potential vulnerabilities and encourage security researchers and users to report security issues privately.

## Supported Versions

We provide security fixes and maintenance updates for the active development branch. Older tags or untracked forks are not actively maintained; please upgrade to the latest version before reporting vulnerabilities.

| Version | Supported          | Notes                                     |
| ------- | ------------------ | ----------------------------------------- |
| `main`  | :white_check_mark: | Active development branch                 |
| < 1.0.0 | :x:                | Historical versions; update to `main`     |

## Reporting a Vulnerability

**Please do not report suspected security vulnerabilities through public GitHub issues, pull requests, or public discussions.**

If you discover a potential vulnerability in Eagle-1-64Bit, report it privately using one of the following methods:

1. **GitHub Private Vulnerability Advisory (Preferred):**
   Submit a draft security advisory via [GitHub Security Advisories](https://github.com/paulp143/Eagle-1-64Bit/security/advisories/new).
2. **Direct Email:**
   Send an encrypted or standard email to [paul@schep.de](mailto:paul@schep.de) with the subject line:
   `[SECURITY] Eagle-1-64Bit Vulnerability Report`

### What Information to Include in Your Report

To help us triage and investigate the issue as quickly as possible, please include:

- **Summary:** A concise overview of the issue and the impacted component (e.g., save data serialization, input parsing, asset loading).
- **Vulnerability Type:** The class of vulnerability (e.g., arbitrary code execution, path traversal, denial-of-service, unhandled exception crash).
- **Steps to Reproduce:** Clear, step-by-step instructions or a minimal proof-of-concept (PoC) demonstrating the vulnerability.
- **Environment:** Operating system, Python version, Pygame / Pygame-ce version, and commit hash or release tag tested.
- **Impact Assessment:** An explanation of what an attacker could achieve and the conditions required to trigger the issue.
- **Proposed Fix:** Any patch, workaround, or mitigation you have developed (optional).

## Response and Coordination Process

When you report a suspected vulnerability, our maintainers follow this coordinated disclosure workflow:

1. **Initial Acknowledgment:** We aim to acknowledge receipt of your report within **48–72 hours**.
2. **Triage and Investigation:** We will evaluate the report, verify the impact, and keep you updated on progress.
3. **Patch Development:** Fixes will be prepared and validated privately (such as within a private GitHub Security Advisory workspace).
4. **Coordinated Disclosure:** Once a fix is verified and merged to `main`, we will publish a release/advisory and credit you for the responsible disclosure (unless you prefer to remain anonymous).

## Public Discussions and Sensitive Information

- **Never disclose details of an unpatched vulnerability in public issues, discussions, or commit messages.**
- When discussing normal bugs in public issues, avoid sharing sensitive personal data, authorization tokens, system credentials, or full memory dumps that might inadvertently contain private user information.
- If you are unsure whether a bug qualifies as a security vulnerability, err on the side of caution and reach out via the private reporting channels above.
