# Publishing to PyPI

Automated publishing runs on every **`v*`** git tag push or GitHub Release publish.

Workflow: [`.github/workflows/publish.yml`](workflows/publish.yml)

## Fastest fix: API token (works right now)

You already published v1.0.0 manually — use the same token in GitHub:

1. Log in to https://pypi.org as **OpenSourcer** (project owner)
2. **Account settings** → **API tokens** → **Add API token**
   - Scope: **Entire account** or project `toolschema`
3. GitHub → https://github.com/false200/toolschema/settings/secrets/actions
4. **New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Value: paste the token (`pypi-...`)
5. **Actions** → **Publish to PyPI** → **Run workflow**

`publish.yml` uses the secret when present; no trusted publisher setup required.

## Trusted publishing (no token in GitHub)

1. Log in to https://pypi.org as **OpenSourcer**
2. https://pypi.org/manage/project/toolschema/publishing/ → **Add a new pending publisher** → GitHub

| Field | Value |
|-------|--------|
| PyPI Project Name | `toolschema` |
| Owner | `false200` |
| Repository name | `toolschema` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

3. Save — remove `PYPI_API_TOKEN` secret if you switch to this

`publish.yml` uses `environment: pypi` with URL `https://pypi.org/p/toolschema`. After a successful CI publish, GitHub shows a green **pypi** deployment badge on the commit.

Trusted publishing is used automatically when `PYPI_API_TOKEN` is not set.

### Optional: protect releases with a GitHub environment

GitHub → **Settings** → **Environments** → **pypi** → add required reviewers or branch rules before publish runs.

## Release a new version

1. Bump version in `pyproject.toml` and `src/toolschema/__init__.py`
2. Update `CHANGELOG.md`
3. Commit and push:

```bash
git add pyproject.toml src/toolschema/__init__.py CHANGELOG.md
git commit -m "Release v1.0.1"
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

4. CI builds and publishes to PyPI automatically
5. Check https://pypi.org/project/toolschema/

## Manual publish (local)

```bash
uv build
uv publish
# set UV_PUBLISH_TOKEN first
```

## Note: GitHub "Packages" vs PyPI badge

The repo sidebar **Packages → No packages published** is **GitHub Packages** (Docker, npm on ghcr.io). PyPI will never appear there. That is normal for every Python project on PyPI, including queuebridge.

What queuebridge shows (green check + **pypi**) is a **deployment** from GitHub Actions after CI publishes with trusted publishing + `environment: pypi`. It appears on commits/tags and under **Environments**, not under Packages.

toolschema v1.0.0 was uploaded manually, so no deployment badge exists yet. After trusted publishing is configured, push a new tag (e.g. `v1.0.1`) and the badge appears on that commit.

PyPI install:

- https://pypi.org/project/toolschema/
- `pip install toolschema`
