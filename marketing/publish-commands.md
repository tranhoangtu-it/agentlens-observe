# Package Publishing Commands — v1.0.0

All packages built and ready. Run these commands to publish.

## 1. PyPI (Python SDK)

```bash
# Login (one-time, needs API token from https://pypi.org/manage/account/token/)
# Option A: Set token as env var
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxx

# Option B: Use keyring
pip install keyring

# Publish
cd sdk
python -m twine upload dist/agentlens_observe-1.0.0*
```

**Verify:** `pip install agentlens-observe==1.0.0`

## 2. npm (TypeScript SDK)

```bash
# Login (needs npm account at https://www.npmjs.com/)
npm login

# Publish
cd sdk-ts
npm publish --access public
```

**Verify:** `npm install agentlens-observe@1.0.0`

## 3. NuGet (.NET SDK)

```bash
# Get API key from https://www.nuget.org/account/apikeys
# Publish
cd sdk-dotnet
dotnet nuget push nupkg/AgentLens.Observe.1.0.0.nupkg \
  --api-key YOUR_NUGET_API_KEY \
  --source https://api.nuget.org/v3/index.json
```

**Verify:** `dotnet add package AgentLens.Observe --version 1.0.0`

## Pre-built artifacts

| Package | File | Size |
|---------|------|------|
| PyPI | `sdk/dist/agentlens_observe-1.0.0-py3-none-any.whl` | ~15KB |
| npm | `sdk-ts/dist/` (index.js, index.cjs, index.d.ts) | ~20KB |
| NuGet | `sdk-dotnet/nupkg/AgentLens.Observe.1.0.0.nupkg` | ~25KB |
