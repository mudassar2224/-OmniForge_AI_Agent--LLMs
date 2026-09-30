---
name: debugging
description: Diagnose and fix code errors with bounded repair attempts
---

# Debugging Skill

When this skill is activated, systematically diagnose failure conditions and apply surgical code fixes:

1. **Traceback & Error Triage**: Carefully parse exception types, error messages, and call stack frames to isolate the exact fault site.
2. **Root Cause Hypothesis**: Distinguish between syntax errors, type mismatches, missing modules, missing attributes, or subtle algorithmic flaws.
3. **Isolated Minimal Reproduction**: Write a minimal self-contained script or test case that reliably reproduces the defect in isolation.
4. **Bounded Iteration Limit**: Enforce a strict ceiling of 3 to 5 automated repair cycles to avoid non-terminating trial-and-error loops.
5. **Surgical Precision**: Apply minimally invasive modifications targeted specifically at the defect, preserving existing design patterns and comments.
6. **Post-Fix Regression Check**: Re-run the reproduction script and broader test suite to confirm the issue is resolved without introducing regressions.
