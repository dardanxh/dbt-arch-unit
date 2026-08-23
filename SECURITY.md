# Security Policy

## Supported Versions

dbt-arch-unit is pre-1.0. Security fixes are applied to the latest released
version on the `main` branch.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Reporting a Vulnerability

Please **do not** open a public issue for security problems.

Instead, report privately using one of:

- GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
  (the **"Report a vulnerability"** button under the repository's *Security* tab), or
- email **dardanxhymshiti@gmail.com** with details and reproduction steps.

You can expect an initial acknowledgement within a few days. Once the issue is
confirmed and fixed, we will publish a release and credit the reporter (unless
you prefer to remain anonymous).

## Scope

dbt-arch-unit reads local files (`manifest.json`, `.sql`/`.yml`) and writes
reports. It executes no dbt SQL and makes no network calls. Reports of unsafe
file handling, path traversal, or unexpected code execution are in scope.
