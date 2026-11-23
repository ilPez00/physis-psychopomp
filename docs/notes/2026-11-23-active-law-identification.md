# Next research slice: choose an experiment that separates laws

**Status:** design proposal, not preregistered or measured. No learned arm.

## Source findings

- [Balestriero, LeCun & Varaku, *Counterfactual World Models*](https://arxiv.org/abs/2611.24778):
  retain a factual predictor and use `observed + predicted(alternative) −
  predicted(factual)` to carry a realized disturbance into an alternative action.
  The reported physical counterfactual R² ranges (38–46% vs 86–96%, four rendered
  simulators) are for correction after a factual readout. No retraining for the
  correction does not mean no factual training. Contacts, coordinate folds, and
  disturbances that scale the action are failure regimes.
- [Nuijten et al., *What Type of Inference is Active Inference?*](https://proceedings.mlr.press/v337/nuijten26a.html)
  distinguish epistemic entropy corrections from the correction needed for policy
  optimization. [Friston et al., *Active inference and artificial reasoning*](https://www.nature.com/articles/s41467-026-77209-5)
  target expected information gain about competing model structures. Start with
  exact Bayesian experiment design, not a claimed implementation of full EFE.
- [Yuan & Liu, *When Can World Models Recover Physical Laws?*](https://arxiv.org/abs/2610.06877):
  identifiability is relative to a law class, experiment catalogue and sensor;
  accurate predictions on an observationally equivalent regime cannot certify
  recovery. Distinguishability and acquisition budget are separate questions.

## First benchmark and demo boundary

Use two toy action-response laws `y = s + m·a`, `m ∈ {−1,+1}`, with reset state
`s ∈ {−3,−1,+1,+3}`. Independent uniform priors; noiseless declared readouts.
Passive records at `a=0` agree for both laws at each state, not just on average.
The one-experiment budget allows any one of these equal-cost probes:

| Probe | Readout | Predicted law information | Predicted reset-state information |
|---|---|---:|---:|
| Passive | `y` at `a=0` | 0 bits | 2 bits |
| Signed | `sign(y)` at `a=4` | 1 bit | 0 bits |
| Magnitude | `abs(y)` at `a=4` | 0 bits | 1 bit |

Compute `I(Law; readout)` and `I(ResetState; readout)` separately from finite
likelihoods. Freeze an exact response table, tolerance, and a balanced shuffled
signed-response control before implementing. Compare model-targeted selection
against a state-targeted selector, maximum readout entropy, and uniform random
selection (predicted law gain **1/3 bit**). Check acquired evidence under both
true laws; expose only the declared readout, not simulator provenance that encodes
the law ID. Removing the signed probe must make structural recovery abstain even
though more state evidence is available. Report law and state posterior changes
separately. This is a finite candidate-set benchmark, not open-ended law discovery.

The first reusable Physis output, if the benchmark earns it, is an experiment
receipt: belief target (`law` or `state`), candidate set and sensor, prior, budget,
predicted gain, and realized posterior change. No general uncertainty schema or
execution autonomy before a second discriminator.

For the demo, exercise this design with an actual Psychopomp exit event rather
than presenting a hand-written response table as an execution. Proposed fixture:
start a body in an occluder, drift it out at fixed horizontal speed, and vary
the sign of its unobserved transverse response to a controlled input. Decode
only the declared exit readout, not the event's configuration hash or truth
label. Use a magnitude-only calibration readout that contradicts the nominal
no-response model but leaves the two alternative laws equally likely; a signed
readout at a fresh reset then separates them. Freeze the sensor map and an
independent expected response table before running either law.

One local, allowlisted simulation experiment per diagnosis; no arbitrary
commands, external devices, or writes into a production ledger. Exact Bayesian
information gain is the first controller. Verify that Physis-next can store
both hypotheses and round-trip the evidence and belief revision in an isolated
store before calling the integrated demo complete. Keep suggestion, execution,
and verification distinct:

- **Suggest:** rank experiments before seeing any diagnostic outcome.
- **Execute:** run only the selected simulator action; expose the sanitized
  observation, not hidden state. Record nominal mismatch and rival posterior
  before and after.
- **Verify:** replay under both true laws; a passive or shuffled probe must
  not earn a discovery, and a missing or out-of-support diagnostic observation
  must not force a winner. A lucky correct guess or a counterfactual prediction
  is not executed evidence.

## Separate card: identify when the counterfactual is not recoverable

For binary actions, compare `Y(a) = f(a) + S` with `Y(a) = f(a) + (−1)^a S`,
where a new symmetric `S` is sampled at each reset. Every single-action marginal
is the same under both models, but the joint within-reset coupling differs.
Compare the factual-mean baseline, the factual-residual correction, and an
evaluation-only oracle holding `S` fixed. Score paired error and abstention:
the correction is exact under additive reuse and has absolute error `2|S|`
under the action-dependent sign flip. Marginally correct predictions earn no
credit for individual counterfactuals. Paired simulator truth stays with the
scorer; it must not enter planning, training, or observed history.

## Second discriminator: identity under complete turnover

Operationalize “organizing principle” as a **response to interventions**, not a
metaphysical identity test. Two discrete simulated systems have the same roles,
component types, replacement schedule, and undisturbed aggregate trajectory.
Every initial component is replaced. In one system the role-level rule restores
an imbalance by feedback; the open-loop control replays the same nominal
sequence without consulting the imbalance. Intervene with a matched one-role
perturbation, not a new component type. Score return to the declared invariant
set by a frozen horizon, sustained residence, and invariance to relabelling
component IDs. Audit turnover separately from organization.

Require three controls: passive logs tie; ID relabelling alone cannot alter
the verdict; severing feedback without changing the nominal inventory removes
recovery. If a second mechanism has the same allowed response distribution,
return an equivalence class or abstain. Success would show organizational
continuity can be discriminated under the chosen interventions, not establish
organism identity in general. This toy follows the demo; it is not part of its
first acceptance gate.
