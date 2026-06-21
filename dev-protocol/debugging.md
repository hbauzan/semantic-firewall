# STRUCTURED BUG DIAGNOSIS PROTOCOL

When a bug is reported or tests are failing, follow this 6-phase debugging loop. Do not skip phases unless explicitly justified.

---

## Phase 1: Build a Feedback Loop
Everything else is mechanical. If you have a tight, pass/fail signal that goes red on *this specific bug*, you will find the cause. If not, staring at code will not save you.

### 1.1. Constructing the Loop (Try in order)
1. **Failing test** at whatever seam reaches the bug (unit, integration, e2e).
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) asserting on DOM/console.
5. **Replay a captured trace**: save a network request/payload and run in isolation.
6. **Throwaway harness**: spin up a minimal subset of the system (one service, mocked dependencies).
7. **Property / fuzz loop**: run 1000 random inputs to trigger a flake.
8. **Bisection harness**: automate checking versions to `git bisect run`.
9. **Differential loop**: run same input through old vs new versions and diff.
10. **HITL bash script**: drive human-in-the-loop steps via a structured script.

### 1.2. Tighten and Verify
- **Tighten the loop**: Make it fast (seconds, not minutes), deterministic (pin time/RNG, isolate network), and sharp (assert on the symptom, not just "didn't crash").
- **Phase 1 Completion Criterion**: You must establish **one command** that runs unattended, is fast, deterministic, and **red-capable** (successfully triggers and catches this exact bug).
- **Prohibited action**: Do not jump to hypotheses or read code to build a theory before this command exists. No red-capable command, no Phase 2.

---

## Phase 2: Reproduce + Minimise
Run the feedback loop and watch it go red.
1. Confirm the loop produces the **user's exact described symptom** (not a different nearby issue).
2. Shrink the repro to the **smallest scenario that still goes red**. Cut inputs, configuration, and steps one at a time.
3. Done when every remaining element is load-bearing (removing any one element makes the loop go green).

---

## Phase 3: Hypothesise
1. Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.
2. Ensure each hypothesis is **falsifiable**: state the prediction it makes.
   > **Format**: *"If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."*
3. **Show the ranked list to the user** before testing. If the user is AFK, proceed with testing the top hypothesis.

---

## Phase 4: Instrument
1. Map each probe to a specific prediction from Phase 3. Change **one variable at a time**.
2. **Tag every debug log** with a unique prefix (e.g., `[DEBUG-a4f2]`) so they can be cleaned up in a single grep.
3. For performance regressions, establish baseline measurements (`performance.now()`, query plans) before making modifications.

---

## Phase 5: Fix + Regression Test
1. Write a regression test **before the fix** (only if a correct seam exists).
2. If no correct seam exists (e.g. tests cannot replicate the integration path), note this finding. Codebase architecture is preventing the bug from being locked down.
3. Steps: Turn minimised repro into a failing test -> Watch it fail -> Apply fix -> Watch it pass -> Re-run the Phase 1 loop against the original un-minimised repro.

---

## Phase 6: Cleanup + Post-Mortem
Before declaring a bug resolved, complete this checklist:
- [ ] Original repro no longer reproduces (re-run Phase 1 loop).
- [ ] Regression test passes (or absence of seam is documented).
- [ ] All tagged `[DEBUG-...]` instrumentation logs are removed.
- [ ] Throwaway prototypes/harnesses are deleted.
- [ ] Correct hypothesis is documented in the commit/PR message.
- [ ] **Post-Mortem**: Ask: *What would have prevented this bug?* If it requires architectural improvements (better test seams, less coupling), log a task or report it to the user.
