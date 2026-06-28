# Publishing to PyPI

Automated publishing runs on every **`v*`** git tag push or GitHub Release publish.

Workflow: [`.github/workflows/publish.yml`](workflows/publish.yml)

## One-time setup (trusted publishing — recommended)

No API token stored in GitHub secrets.

1. Log in to https://pypi.org
2. Open **toolschema** → **Publishing** → **Add a new pending publisher**
3. Choose **GitHub** and fill in:

| Field | Value |
|-------|--------|
| PyPI Project Name | `toolschema` |
| Owner | `false200` |
| Repository name | `toolschema` |
| Workflow name | `publish.yml` |
| Environment name | *(leave blank)* |

4. Save — no GitHub secrets needed

### Optional: protect releases with a GitHub environment

Add `environment: pypi` to the job in `publish.yml`, create a **pypi** environment on GitHub, and set Environment name to `pypi` on PyPI.

## Alternative: API token

If you skip trusted publishing:

1. Create a PyPI API token at https://pypi.org/manage/account/token/
2. GitHub → **Settings** → **Secrets and variables** → **Actions**
3. Add secret `PYPI_API_TOKEN`
4. Change `publish.yml` to use `password: ${{ secrets.PYPI_API_TOKEN }}` in `gh-action-pypi-publish` — or use:

```yaml
- run: uv publish
  env:
    UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

Trusted publishing is preferred (already configured in the default workflow).

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

## Note: GitHub "Packages" tab

The **Packages** section on your GitHub repo is for **GitHub Packages** (containers, npm on ghcr.io), not PyPI.

PyPI distribution lives at:

- https://pypi.org/project/toolschema/
- `pip install toolschema`

Link it in your repo **About** website field and README badges (already done).
