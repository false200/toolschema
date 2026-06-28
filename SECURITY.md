# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report security issues privately by opening a [GitHub Security Advisory](https://github.com/false200/toolschema/security/advisories/new) or emailing the repository owner via their GitHub profile.

Include:

- A clear description of the issue
- Steps to reproduce
- Impact assessment (if known)
- Suggested fix (if you have one)

We aim to acknowledge reports within 72 hours and will work with you on a fix and disclosure timeline.

## Scope

toolschema generates JSON Schema from Python functions and provides thin integration adapters. It does not execute untrusted code by default, but:

- `validate()` performs argument checking against generated schemas
- Deserialization of tool arguments happens in your application / agent framework
- MCP and CLI commands load user-specified Python modules — only load code you trust

Report issues in toolschema's schema generation, validation, or adapters. Framework-specific bugs in FastMCP, LangChain, etc. may need to be reported upstream as well.
