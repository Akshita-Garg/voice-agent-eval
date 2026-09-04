# Evaluation Plan

## Objective

Find the lowest-latency configuration that preserves reliable turn boundaries,
successful appointment completion, accurate tool arguments, and natural speech.

## Fixed baseline

- Framework: LiveKit Agents
- STT: Pulse streaming, English, 16 kHz linear PCM
- LLM: Electron, streaming, one tool call at a time
- TTS: Lightning v3.1 Pro, `meher`, English, 24 kHz PCM
- Use case and prompt remain byte-identical across parameter runs
- Test scripts and tool backend remain fixed

## Primary metrics

- End of detected user speech to final transcript
- Final transcript to Electron first token
- Electron first token to Lightning first audio
- End of user speech to first audible agent response
- Task completion rate
- Correct tool selection and argument accuracy
- Barge-in detection and obsolete-response cancellation
- Premature endpointing and false interruption counts

## Turn-finalization configurations

Pulse transcript finalization and LiveKit turn commitment are separate decisions.
A Pulse `is_final` segment is stable text; it does not by itself authorize Electron
to respond.

1. **Native + LiveKit baseline (production candidate)**
   - Pulse `endpointing=true`, `eou_timeout_ms=100`
   - LiveKit minimum endpointing delay: `0.40` seconds
   - LiveKit maximum endpointing delay: compare `1.50` and `3.00` seconds;
     the 1.50-second run repeatedly forced incomplete thoughts through at the ceiling.
   - This follows Smallest's low-latency LiveKit default while giving LiveKit more
     room than the initial 150 ms to protect thinking pauses.
2. **Timeout-only comparison**
   - Pulse `endpointing=false`, `eou_timeout_ms=800`
   - Same LiveKit settings as the baseline
   - Tests whether predictable silence timing reduces fragmentation enough to
     justify the added latency.
3. **Hybrid force-final comparison**
   - Keep native endpointing enabled as a fallback.
   - Send Pulse `{"type":"finalize"}` when the external VAD declares speech ended;
     whichever finalization trigger fires first wins.
   - LiveKit still makes the later, separate decision to commit the complete turn.
   - The current LiveKit Smallest plugin does not expose this command publicly, so
     evaluate it through a source-controlled adapter rather than editing `.venv`.

## Parameter sweeps after the finalization comparison

Change one family at a time.

1. Electron
   - Temperature: 0.0, 0.2, 0.6
   - Maximum completion tokens: 80, 120
2. Lightning
   - Speed: 0.9, 1.0, 1.1
   - Streaming buffer flush: 0, 200, 400 ms

Do not run the full Cartesian product. Select one baseline, sweep one family,
retain the best setting, and then move to the next family.

## Scripted scenarios

1. Direct availability request with a specific date.
2. Vague request requiring one clarification.
3. Successful booking with explicit confirmation.
4. Requested slot unavailable; agent must offer alternatives.
5. User pauses mid-sentence for 400–700 ms.
6. User interrupts the agent while it lists slots.
7. User changes their mind after availability is returned.
8. User asks for medical advice; agent must refuse and remain administrative.

## Reporting rule

Every conclusion must name the tested configuration and evidence. Untested
production claims are labeled as hypotheses or next steps.

See `parameter-sweep.md` for the exact MVP matrix and stop criteria, and
`standard-call-script.md` for the repeatable spoken scenario.
