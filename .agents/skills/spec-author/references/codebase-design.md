# Codebase Design & Deep Modules Reference

This guide defines the architectural design principles and shared vocabulary for SpecDrive.
In a **Spec-as-Source** system, specifications define the observable behavior and interfaces at module seams, while AI agents synthesize deep implementations and executable tests. Adhering to deep module principles maximizes leverage for callers, locality for maintainers, and testability for agents and developers alike.

---

## 1. Core Vocabulary

Use these terms precisely; do not substitute "component," "service," "unit," or "boundary."

* **Module**: Anything with an interface and an implementation. Deliberately scale-agnostic: a function, class, package, or tier-spanning slice. (*Avoid*: unit, component, service.)
* **Interface**: Everything a caller must know to use the module correctly: the type signature, invariants, ordering constraints, error modes, required configuration, and performance characteristics. (*Avoid*: API, signature—those refer only to the type-level surface.)
* **Implementation**: What is inside a module; its body of code. Distinct from an **adapter**: an adapter describes the *role* at a seam, while implementation describes what is inside.
* **Depth**: Leverage at the interface. The amount of behavior a caller (or test) can exercise per unit of interface complexity they must learn. A module is **deep** when substantial behavior sits behind a compact interface; it is **shallow** when its interface is nearly as complex as its implementation.
* **Seam** *(Michael Feathers)*: A place where you can alter behavior without editing in that place; the *location* at which a module's interface lives. (*Avoid*: boundary—overloaded with DDD bounded contexts.)
* **Adapter**: A concrete entity that satisfies an interface at a seam. Describes *role* (what slot it fills), not substance.
* **Leverage**: What callers get from depth. More capability per unit of interface learned. One implementation pays back across $N$ call sites and $M$ tests.
* **Locality**: What maintainers get from depth. Change, bugs, knowledge, and verification concentrate in one place rather than dispersing across callers. Fix once, fixed everywhere.

---

## 2. Deep vs. Shallow Modules

### Deep Module (Target)
Small interface + rich implementation.
```text
┌─────────────────────────────────┐
│         Small Interface         │  Few methods, simple parameters
├─────────────────────────────────┤
│                                 │
│       Deep Implementation       │  Complex logic, state transitions,
│                                 │  and error handling hidden inside
└─────────────────────────────────┘
```

### Shallow Module (Anti-pattern to Avoid)
Large interface + thin implementation.
```text
┌─────────────────────────────────┐
│         Large Interface         │  Many methods, pass-through parameters
├─────────────────────────────────┤
│       Thin Implementation       │  Just forwards calls (e.g. Controller ->
│                                 │  Service -> Repository 1-to-1 wrappers)
└─────────────────────────────────┘
```

### The Deletion Test
To evaluate whether a module is earning its keep:
* Imagine deleting the module.
* If complexity **vanishes**, it was a shallow pass-through that added ceremony without value.
* If complexity **reappears across $N$ callers**, the module was providing real leverage and earning its place.

---

## 3. Designing for Testability

Good module interfaces make testing natural and robust:

1. **Accept dependencies, don't create them**:
   Pass collaborators (gateways, stores, clocks) into the module at its seam or constructor. Avoid hardcoding instantiations (`new StripeClient()`) inside the module.
2. **Return results, don't produce side effects**:
   Prefer functions and methods that accept data and return computed results or explicit decision objects over procedures that mutate external state or ambient globals.
3. **Small surface area**:
   Fewer methods mean fewer permutations to test. The interface is the test surface.

---

## 4. The 4 Dependency Categories

When assessing a module or capability, classify its dependencies into one of four categories. This governs how the module is structured across its seams and verified in tests:

| Category | Definition | Testing Strategy | Seam Treatment |
|---|---|---|---|
| **1. In-process** | Pure computation, algorithms, in-memory state. No I/O. | Test through the interface directly with real data. | Always deepenable. No adapter needed. |
| **2. Local-substitutable** | External dependencies that have high-fidelity local test stand-ins (SQLite, PGLite, in-memory filesystem). | Test with the local stand-in running in the test suite. | The seam is internal to the module; no port exposed at the module's public interface. |
| **3. Remote but owned (Ports & Adapters)** | Internal services across a network boundary (microservices, internal APIs, message queues). | Define a **port** (interface) at the seam. In production use an HTTP/gRPC/queue adapter; in tests use an in-memory fake adapter. | Explicit external seam with 2 adapters. Logic sits in one deep module. |
| **4. True external (Mock)** | Third-party services not under your control (Stripe, Twilio, OAuth providers). | Inject a port at the seam; tests use a mock/stub adapter verifying request contracts and response handling. | Explicit external seam with production and mock adapters. |

---

## 5. Seam Discipline

- **One adapter means a hypothetical seam. Two adapters means a real one.**
  Do not introduce an abstract interface or port unless at least two concrete adapters exist (typically production + test stand-in). A single-adapter seam is speculative indirection.
- **Internal seams vs. external seams.**
  A deep module can have internal seams (private helpers, private sub-adapters) used by its own internal organization. Never leak internal seams through the public module interface merely to accommodate tests.

---

## 6. Testing Strategy: Replace, Don't Layer

- **The interface is the test surface.** Callers and tests cross the exact same seam. If a test reaches past the interface to inspect private state or mock internal functions, the module is the wrong shape.
- **Tests assert on observable outcomes**, not implementation details. Tests must survive internal refactoring without breaking.
- **Replace, don't layer**: When deepening a cluster of shallow modules into a single deep module, delete obsolete unit tests on the shallow intermediate components. Write clean, behavioral tests against the deepened module's interface.

---

## 7. "Design It Twice" Workflow

When drafting or refining an architectural slice or module interface, the first idea is rarely the best. Use the **Design It Twice** pattern:

1. **Frame the problem space**:
   - Identify the caller use cases and invariants.
   - Categorize the dependencies (Categories 1–4).
   - Outline constraints and data flow.
2. **Explore 3+ contrasting designs**:
   - *Option A (Minimal Interface)*: 1–3 entry points max; maximize leverage per entry point.
   - *Option B (Maximum Flexibility)*: Configurable options, extensible for varied callers.
   - *Option C (Common-Caller Optimized)*: Makes the 80% default use case trivial, with progressive disclosure for advanced cases.
   - *Option D (Ports & Adapters)*: Explicit ports at seams for remote or external dependencies.
3. **Compare and decide**:
   - Evaluate each option by **depth** (leverage at the interface), **locality** (where change concentrates), and **seam placement**.
   - Select or synthesize a hybrid design before locking requirements in `spec/` and synchronizing code.
