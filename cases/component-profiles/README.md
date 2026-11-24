# Explicit dependency-profile registry

The operator selects `registry.json` through the `trusted_profiles` API argument.
It is not discovered from the untrusted component request. Its membership and
profile SHA-256 values are trust configuration, not authentication. A caller
must not treat a request-supplied registry or `reviewed: true` as authorization.

The initial C10 profile is tied to the exact `/5` source, descriptor, policy and
import closure. It selects all historical/current accounts, authorities and
original receipt references, without eligibility filters. Its namespaces
explicitly describe C10's reversible UTF-8-hex transport identities. They are
not silently equated with arbitrary canonical IDs from another module. The
canonical outer pool and history state key are also derived automatically;
all current C10 roots with that same writable state remain connected across
period changes. Distinct connected packages are held for a coordinated root.

Completeness of the selected profile, including identity compatibility with
other admitted profiles, is a trusted authoring assumption. There is no static
proof from types. New financial profiles need explicit source-owner review of
all shared pools/gates, allocation parents, correction chains and cross-contract
links, including unused original rows. Unknown profiles conservatively join
the entire batch. This registry makes no claim about unregistered modules.

Bind packages to the actual current implementation before planning. For C10,
use its builder/preparation validator before freezing the package bytes; the
generic component executor accepts prepared typed inputs and does not dispatch
case-specific preparation code. No financial calculation or state value is
supplied by this dependency profile.

The selected C10/native-independent witness passes the finite frozen44-method
cohort `component-frozen-20261124-a`, including original-fact controls, standalone
whole-outcome/raw-graph equality and actual completed Q1-to-Q2 state carry.
Those calculations remain unissued. This is finite implementation evidence under
the explicit trusted-profile assumption; it does not statically prove profile
completeness. Main promotion remains separate, and new financial profiles still
require source-owner review.
