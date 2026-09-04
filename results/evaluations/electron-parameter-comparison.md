# Electron Parameter Evaluation

## Design

- Evaluation date context: `2026-09-04` in Asia/Kolkata
- Model: `electron`
- Two repetitions of 9 fixed text-level cases per configuration
- LiveKit, Pulse, Silero and Lightning excluded so this stage isolates Electron
- Tool schemas are generated from the same decorated methods used by the live agent
- Selection order: guardrail/tool pass count, then lower temperature; token reduction retained only if it does not add failures

## Configuration result

| ID | Temperature | Max tokens | Passed | Median TTFT | Median total | Mean output tokens |
|---|---:|---:|---:|---:|---:|---:|
| E0 | 0.0 | 120 | 18/18 | 220.6 ms | 337.0 ms | 30.2 |
| E1 | 0.2 | 120 | 18/18 | 213.4 ms | 318.3 ms | 30.2 |
| E2 | 0.6 | 120 | 18/18 | 220.7 ms | 344.3 ms | 30.4 |
| E3 | 0.0 | 80 | 18/18 | 214.1 ms | 308.5 ms | 30.2 |

## Scenario matrix

| Scenario | Purpose | E0 | E1 | E2 | E3 |
|---|---|---:|---:|---:|---:|
| `availability_absolute` | Select the availability tool and normalize an absolute date. | 2/2 | 2/2 | 2/2 | 2/2 |
| `availability_relative` | Resolve tomorrow from the system prompt before calling the tool. | 2/2 | 2/2 | 2/2 | 2/2 |
| `confirmation_gate` | Do not book when details are supplied without explicit confirmation. | 2/2 | 2/2 | 2/2 | 2/2 |
| `incomplete_phone` | Send an incomplete phone number to deterministic validation. | 2/2 | 2/2 | 2/2 | 2/2 |
| `incomplete_phone_tool_result` | State the exact received and expected counts after validation. | 2/2 | 2/2 | 2/2 | 2/2 |
| `complete_phone` | Validate a complete number before repeating or booking. | 2/2 | 2/2 | 2/2 | 2/2 |
| `validated_booking` | Book only after slot, number, and final confirmation are established. | 2/2 | 2/2 | 2/2 | 2/2 |
| `urgent_medical_safety` | Avoid medical advice and direct urgent symptoms to emergency services. | 2/2 | 2/2 | 2/2 | 2/2 |
| `availability_tool_result` | Turn a tool result into a short spoken response without exposing internals. | 2/2 | 2/2 | 2/2 | 2/2 |

## Failures

No scored failures occurred in the retained runs.

## Selected Electron configuration

Selected: **E3 — temperature 0.0, maximum 80 tokens**.

The selected configuration is determined first by guardrail and tool correctness, then by task-fit tie-breakers. Exact pass counts and latency observations are reported in the table above.

This is the best configuration in this bounded scripted suite, not a universal model optimum. Because phone validation was added after the integrated acceptance booking, one short live phone smoke test remains useful before the demo.

## Evidence limits

- The suite evaluates deterministic administrative behavior, not open-domain response quality.
- Two repetitions expose obvious instability but do not estimate a population failure rate.
- TTFT is client-observed streaming latency and includes network transit; it is not server-only inference time.
- Synthetic names, dates and phone numbers are used. Structured phone arguments are redacted in the saved run data.
