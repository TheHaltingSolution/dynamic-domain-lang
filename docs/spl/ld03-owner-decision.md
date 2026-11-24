# Owner decision: reserve mixed currency for the later compiler tool

23 November 2026. **Decision recorded; native FX remains out of current work.**

The owner accepts mixed-currency contracts as the future dynamic-compiler
example, and explicitly asks to leave that feature unsupported natively for
now. Continue the other agreed feature, performance and testing goals. Revisit
mixed currency with the planned self-modifying compiler tool/skill when those
other current goals are complete, or when the owner explicitly starts that
later phase. This instruction replaces the pending necessity-only selection
question; it does not authorize adding EUR/FX during today's unit work.

The intended later workflow is to take a real-world contract, attempt a faithful
SPL equivalent, identify any missing capability, modify the compiler when
needed, and verify the extension together with existing contracts. The owner
wants the tool to drive this work, rather than implementing the mixed-currency
feature in advance and losing that demonstration opportunity.

The future implementation plan is in
[self-modifying-compiler-demo-plan.md](self-modifying-compiler-demo-plan.md).
There is no request to create that skill in the current workstream. The
conditional instruction permits revisiting it once other current goals are
verified complete; another identical currency-gate question is unnecessary.

## Claims and preserved evidence

Both RR04 and LD03 found no qualified contract-required financial residual after
faithful existing-language attempts. Record-backed FX, complete-period rational
compounding and bounded dated Quest remain valid methods. They are retained;
no working cancellation rule or representation will be removed to manufacture
an encoding failure.

The selected future claim is compiler extensibility: admit new checked domain
concepts while preserving old behavior. It is not a claim that old SPL could
never calculate the corresponding amounts. A tool must distinguish an actual
missing capability from missing facts, unresolved contract policy, a failed
first attempt, or a preferred builtin spelling. A checked native-currency
interface can be named as an extension target without mislabeling a successful
record-backed calculation as financially impossible.

## Current implementation boundary

- Keep current Money/Rate currency admission USD-only. Add no native EUR, FX
  quotes/conversion builtin, currency dictionary or currency-state migration now.
- Continue the explicit non-FX UsageMinute/UsageHour engineering slice. Its
  generic immutable feature/admission mechanism may support later extensions;
  it does not add currency semantics or implement the reserved demonstration.
- Preserve existing source/facts/state, independently derived controls and
  historical issued artifacts and pins. New releases never repin old results.
- Keep `B-C15-FX` visible as reserved/gated, rather than declaring complete C1
  native currency support. The later tool is a separately deferred work item.
- No professional approval, vendor parity or whole-compiler proof follows from
  this research/sequence decision.

## Prior reviewer recommendation

The reviewer recommendation was to demonstrate a versioned capability or a
stronger checked interface with old-language alternatives, measured effort and
unchanged-contract/state replay. That recommendation is retained in
[the integration index](rr04-ld03-integration.md). The owner now selects the
claim and defers the native implementation to the tool-driven phase.

Local sources: `SPL_RR04_Completion_Decisions.md` section1 and
`SPL_LD03_Completion_Review.md` section2 under
`C:/Projects/Film_TV_participation_dynamic_DSL/ResearchAgent/documents/`.
The decision above is the owner's later message in this session, not an inferred
waiver from those reviewers.
