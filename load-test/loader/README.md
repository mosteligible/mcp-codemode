# k6 loader for coderunner

This folder contains the k6-based load test harness for the coderunner `POST /run` endpoint only. It does not include direct gRPC tests.

## Scripts

- `smoke.js`: low-risk validation against the `short` workload profile.
- `mixed-ramp.js`: staged ramp test for finding the latency knee and initial throughput limit.
- `mixed-soak.js`: steady-state mixed workload for checking sustainable capacity.
- `long-form.js`: 5-minute constant-VU test where each request runs for bounded 5 to 25 second CPU work.

## Request contract

The runner endpoint expects this JSON body:

```json
{
  "code": "printf 'short-ok\\n'",
  "language": "bash",
  "sessionId": "k6-mixed-soak-session-0"
}
```

The current agent executes the `code` field through `bash -c`, so the built-in workload profiles send shell commands. The medium, long, and long-form profiles use shell commands that invoke Python inside the container because the default agent image already includes Python.

The loader is now session-aware by default. It sends `sessionId` in the request body so the agent can bind each logical user session to a dedicated container.

Default session behavior by scenario:

- `smoke.js`: one session per VU
- `mixed-ramp.js`: fixed session pool shared by incoming requests
- `mixed-soak.js`: fixed session pool shared by incoming requests
- `long-form.js`: one session per VU

This is intentional:

- constant-VU tests map naturally to one session per VU
- arrival-rate tests need a stable pool of user sessions instead of creating a new session every time k6 adds worker VUs

## Default workload mix

- `short`: quick shell response
- `medium`: CPU-heavy Python loop
- `long`: long-running busy loop intended to pressure the 30-second execution timeout without crossing it by default

Default weighted mix for the mixed scenarios:

- `short`: 70
- `medium`: 20
- `long`: 10

## Usage

Run from the repository root:

```bash
k6 run load-test/loader/smoke.js
k6 run load-test/loader/mixed-ramp.js
k6 run load-test/loader/mixed-soak.js
k6 run load-test/loader/long-form.js
```

Target a remote coderunner instance:

```bash
CODERUNNER_BASE_URL=http://machine-1.local:8080 k6 run load-test/loader/mixed-ramp.js
```

## Useful environment variables

- `CODERUNNER_BASE_URL`: base URL for coderunner, default `http://localhost:8080`
- `CODERUNNER_RUN_PATH`: request path, default `/run`
- `CODERUNNER_REQUEST_TIMEOUT`: k6 request timeout, default `35s`
- `THINK_TIME_SECONDS`: optional sleep after each request, default `0`
- `SESSION_ID_ENABLED`: whether to include `sessionId` in the payload, default `true`
- `SESSION_ID_MODE`: fallback session mode for custom scripts, default `pool`
- `SESSION_POOL_SIZE`: number of logical sessions for pool-based tests, default `8`
- `SESSION_PREFIX`: prefix for generated session IDs, default `k6`
- `MEDIUM_PYTHON_ITERATIONS`: medium workload intensity, default `4000000`
- `LONG_BUSY_SECONDS`: long workload duration target, default `25`
- `LONG_FORM_MIN_SECONDS`: minimum command duration for `long-form.js`, default `5`
- `LONG_FORM_MAX_SECONDS`: maximum command duration for `long-form.js`, default `25`
- `MIX_SHORT_WEIGHT`: short profile weight, default `70`
- `MIX_MEDIUM_WEIGHT`: medium profile weight, default `20`
- `MIX_LONG_WEIGHT`: long profile weight, default `10`

Ramp scenario tuning:

- `RAMP_START_RATE`
- `RAMP_PRE_ALLOCATED_VUS`
- `RAMP_MAX_VUS`
- `RAMP_TIME_UNIT`
- `RAMP_STAGE_1_TARGET` through `RAMP_STAGE_6_TARGET`
- `RAMP_STAGE_1_DURATION` through `RAMP_STAGE_6_DURATION`

Soak scenario tuning:

- `SOAK_RATE`
- `SOAK_TIME_UNIT`
- `SOAK_DURATION`
- `SOAK_PRE_ALLOCATED_VUS`
- `SOAK_MAX_VUS`

Smoke scenario tuning:

- `SMOKE_VUS`
- `SMOKE_DURATION`

Long-form scenario tuning:

- `LONG_FORM_VUS`
- `LONG_FORM_DURATION`
- `LONG_FORM_MIN_SECONDS`
- `LONG_FORM_MAX_SECONDS`

The long-form workload uses a time-bounded compute loop instead of `sleep`, so it is better for exposing CPU bottlenecks on the agent machine.

If you want to avoid reusing session-bound containers across separate test runs before the agent's idle cleanup removes them, set a unique `SESSION_PREFIX` per run.

## Current checks

Each script validates:

- HTTP status is `200`
- response body is JSON
- response includes an `output` field
- response output includes the expected marker for the selected workload profile

The scripts also publish these k6 custom rates:

- `invalid_json_responses`
- `missing_output_responses`
- `command_error_responses`