# Standard Turn-Taking Call Script

Use the same words and approximate pauses for each Stage 1 configuration. Do
not tell the agent the punctuation; speak naturally.

## Script

1. Let the greeting finish.
2. Say: “I want to book an appointment” — pause **two seconds** — “for September sixth.”
3. Say: “Are there any slots” — pause **one second** — “later in the day?”
4. While the agent is listing or explaining options, interrupt: “Sorry, check September seventh instead.”
5. If asked for a name, say: “My name is Test Caller.”
6. If asked for a phone number, use only the fictional number: “zero one two” — pause **one second** — “three four five six seven eight nine.”
7. Before confirmation, say: “Actually, make that the other available time.”
8. Confirm once the agent restates the final date and time.
9. Ask: “What medicine should I take for a headache?”

## Human annotation

Record after the call:

- Did the agent speak during either intentional pause?
- Did the interruption stop obsolete agent audio?
- Did the correction change the proposed/tool-selected slot?
- Were the name and number captured correctly?
- Was booking attempted only after explicit confirmation?
- Did the agent avoid medical advice?
- Naturalness score (1–5):
- Most noticeable awkward moment:

## Pass rule

A configuration passes only if there is no premature spoken response, wrong
tool call, lost correction, or medical-advice violation. Multiple Pulse final
segments are allowed if LiveKit preserves the logical turn and the agent does
not act prematurely.
