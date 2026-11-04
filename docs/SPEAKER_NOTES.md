# Speaker notes — Editing Neural Networks with Language Models

Davut Emre (detasar) · 4 November 2026. English narrative: 35 minutes; Q&A: 5 minutes.

All 22 scene scripts below match the interactive Presenter panel. Timings include
deliberate pauses to read figures and bounded demos. Each demo has a static PDF
backup. Do not make model calls during the talk. Use arrows, scene menu, Pause,
Motion off, or `?renderer=2d`. Orbit/zoom explain geometry; never imply measured
activations. Presenter opens the timer; Reset returns to the cover.

## 01 · Editing Neural Networks with Language Models

0:00–1:54 · 1.89 minutes · scene `#cover`

**Claim:** Independent and cooperative weight editing on Adult and SmolLM2.

Open with the question: can a language model propose a small, legal weight change that improves a held-out decision rule? The study follows a scalar intervention through development selection into frozen final predictions. Adult provides a visible small network; SmolLM2 tests the same editing idea at a larger scale. This is an exploratory single-session study by Davut Emre (detasar), November 2026.

**Delivery pace:** Establish the question, allow the audience to read, and connect the claim to the preceding result.

**Demo / static backup:** Show the cover; use the frozen cover PDF if rendering is unavailable.

**Transition:** Begin at a single connection.

## 02 · A weight is a contribution

1:54–2:50 · 0.95 minutes · scene `#weight`

**Claim:** Changing a scalar changes a computation; improvement must still be measured.

Read a connection as a learned contribution to the next hidden unit. The animated flow is explanatory; no hidden activation logs were retained. We can show exact stored weights and exact changed scalars, then test consequences using paired final probabilities. A visually prominent edit is not evidence of a useful edit.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Change the method and inspect a real before/after scalar; backup: static inspector.

**Transition:** Zoom out to the two test beds.

## 03 · Two scales, one question

2:50–3:47 · 0.95 minutes · scene `#map`

**Claim:** A small classifier makes the intervention legible. A language model tests selection at scale.

Adult is a 104-input binary classifier with two hidden layers. Its damaged origin constrains edits to surviving second-layer connections. SmolLM2 is an intact base language model with edits restricted to down projection tensors. These are different targets and different endpoints. Inspired by Takehi, Teoh, Zhang and Khattab, Sparks of Weight-Space Programming (2 November 2026); this is an independent test on different targets, not a replication of their numerical gains.

**Delivery pace:** Establish the question, allow the audience to read, and connect the claim to the preceding result.

**Demo / static backup:** Point to the two architectures; backup: study map page.

**Transition:** First, make Adult completely visible.

## 04 · The whole Adult network

3:47–5:41 · 1.89 minutes · scene `#adult`

**Claim:** 104 inputs → 32 ReLU → 16 ReLU → 1 sigmoid probability.

Every one of the 153 nodes is drawn. First-layer edges are sampled to keep the drawing readable; the fc2 domain is complete. Cyan marks surviving connections and amber marks the selected patch support. The probability is produced by a sigmoid after the final linear layer. Original feature records are not distributed.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch Sol to Astra and joint. Watch real fc2 support and the inspector. Backup: network PNG.

**Transition:** Now separate removed edges from legal edits.

## 05 · The mask stays closed

5:41–6:37 · 0.95 minutes · scene `#mask`

**Claim:** Removed connections remain zero; edits can only change surviving fc2 entries.

The calibration procedure permanently zeroed fc2 columns. Dashed red edges show the actual permanent mask. The seed101 damage criterion was insufficient; the held-out clean balanced accuracy is below damaged. We therefore interpret an error-balance tradeoff rather than a restored balanced-accuracy fraction. The intact reference is still useful for accuracy and calibration.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Toggle methods; masked entries never become amber. Backup: frozen mask scene.

**Transition:** Define what a legal patch can do.

## 06 · A bounded intervention

6:37–7:34 · 0.95 minutes · scene `#legal`

**Claim:** Each candidate is a complete patch relative to one immutable origin.

There is no gradient update in the repair stage. An editor submits a structured action; the controller validates its tensor, support, post-cast counts and norm before evaluation. Each legal candidate starts from the same damaged weights. The forward pass is the ordinary network computation after that edit.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Select a changed edge in the scalar selector. Backup: inspector values in PDF.

**Transition:** Inspect a scalar rather than an illustration.

## 07 · Before. After. Exactly.

7:34–9:28 · 1.89 minutes · scene `#inspector`

**Claim:** The visual support and the scalar inspector refer to the same executed patch.

The before and after numbers come directly from the exported Adult graph. They reflect actual float32 application. The inspector does not substitute the requested decimal delta for the executed scalar difference. This is a narrow intervention with a measurable support and L2 norm, not a new trained model.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Cycle the real changed scalar list; backup: the frozen first changed scalar.

**Transition:** Compare independent proposals.

## 08 · Two branches from one origin

9:28–10:24 · 0.95 minutes · scene `#solo`

**Claim:** Sol and Astra never receive one another’s source attempts.

The solo source searches are independent at origin. Neither patch is applied on top of the other. Their endpoints can be compared because they share the origin and held-out examples. The original Adult solo allowance is ten candidates each; the joint allowance is five and has extra development history. That compares endpoints, not equal-compute cooperative synergy.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Trace both branches visually; backup: independent branch diagram.

**Transition:** Follow the actual controller loop.

## 09 · Propose → validate → measure

10:24–11:21 · 0.95 minutes · scene `#loop`

**Claim:** Development feedback guides edits. Final feedback never chooses the patch.

The exact prompts and schemas are linked in the appendix. Editors may inspect permitted statistics, propose bounded JSON operations, and receive development feedback. Invalid actions have no score. The selection rule includes the unchanged candidate zero. The final panel is assessed after patches are frozen. Prompts and configuration hashes make the interface auditable.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Open exact v2 prompt link; backup: linked local text and schema.

**Transition:** The winning point is a selection rule, not a smooth learning curve.

## 10 · Selection is part of the result

11:21–13:15 · 1.89 minutes · scene `#selection`

**Claim:** A higher primary development score wins; equal scores prefer the smaller edit.

Each dot is a real development measurement at its actual candidate index. There is no interpolated score between dots. Adult selects by balanced accuracy, then L2, changed scalar count and earliest index. The outlined point is the frozen selection. Development is a separate panel from final evaluation. Hover or focus a point to view its patch, not a fabricated intermediate state.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch methods and candidates; backup: frozen selected-point chart.

**Transition:** What changes when development experience is shared?

## 11 · Share experience, keep the origin

13:15–15:08 · 1.89 minutes · scene `#joint`

**Claim:** The joint search receives development history, not a serial sum of solo edits.

The joint session can inspect the source development history. It still submits complete candidates relative to the immutable origin, under the same legal intervention domain. It cannot see final outcomes. This is feedback-informed cooperation with an unequal original allowance, so the endpoint comparison cannot isolate a general synergy effect.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Trace the dashed history arrows. Backup: joint branch diagram.

**Transition:** Measure its held-out consequence.

## 12 · A small shift in balanced accuracy

15:08–17:02 · 1.89 minutes · scene `#results`

**Claim:** Sol and joint move the primary metric upward; Astra is effectively flat.

Read the common horizontal axis in percentage points, not relative percent. Each interval is a paired 95 percent class-stratified bootstrap interval using two thousand draws and seed101. These intervals describe examples within this session, not variability across editor sessions. The clean reference lies below damaged on this metric.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch comparison reference to random or grid. Backup: forest plot PDF.

**Transition:** A gain in balanced accuracy can still lose correct decisions.

## 13 · Who changes sides?

17:02–19:52 · 2.84 minutes · scene `#decisions`

**Claim:** Positive-class rescues come with negative-class regressions.

The horizontal axis is baseline probability and the vertical axis is edited probability. Dashed lines mark the same half-probability threshold. Amber is income above 50K; cyan is the negative class. Every decision flip is included along with a deterministic sample of unchanged rows. Balanced accuracy weights the two classes equally; ordinary accuracy weights every example equally. Class counts therefore explain the apparent disagreement without claiming a mechanism.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch method and read the class rescue/regression counts; backup: probability plot.

**Transition:** Use the intact and non-editor controls to interpret this tradeoff.

## 14 · Better balance is not recovery

19:52–21:45 · 1.89 minutes · scene `#controls`

**Claim:** Clean has lower BA, but better accuracy, ranking and probability quality.

Compare all five metrics. Clean improves ordinary accuracy, ROC-AUC, log-loss and Brier relative to damaged while balanced accuracy is lower. Sol and joint exceed random and grid on balanced accuracy; those paired comparisons are in the controls selector and appendix. Do not define a conventional recovery ratio when the clean-minus-damaged denominator is unsuitable. The single-seed endpoint evidence supports a tradeoff in decision balance.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Read the metric directions and compare controls. Backup: table page.

**Transition:** Scale the same idea to a language model.

## 15 · From 153 nodes to 24 blocks

21:45–23:39 · 1.89 minutes · scene `#blocks`

**Claim:** The architecture is schematic; intervention indices and measured operations are exact.

This is the 24-block SmolLM2 base model. Each block contains a gated MLP. The editor cannot rewrite arbitrary parameters: the allowed tensors are down projection weights. The diagram is schematic rather than a drawing of every parameter. Selecting a nonzero development candidate highlights the actual touched block.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Choose a nonzero candidate and watch the touched block. Backup: schematic PDF.

**Transition:** Open the gated MLP.

## 16 · Edit a channel contribution

23:39–25:32 · 1.89 minutes · scene `#mlp`

**Claim:** 2048 → 8192 → 2048, with selected columns scaled or sparse scalars changed.

The gate and up branches form intermediate channels, and the down projection maps their contributions back into the residual dimension. Column scaling changes selected intermediate-channel contributions. The displayed bins aggregate 128 channels each; exact columns, factors and tensor names appear below. Counts and norms are measured after dtype application. Nonselected LM raw scalar samples were not retained, so they are not invented here.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch candidate and method; inspect the exact operation list. Backup: MLP and operation text.

**Transition:** Now ask which measured candidate survives selection.

## 17 · A real search can select no change

25:32–27:26 · 1.89 minutes · scene `#lm-development`

**Claim:** Nonempty candidates were measured. The unchanged origin still wins.

The completed v2 source searches each measured five nonempty candidates. Joint has five attempts: its first was invalid with no score, valid indices are zero, two, three, four and five, and the final candidate is a no-op. Development normalized accuracy does not improve enough to displace zero under the lexicographic rule. All methods freeze candidate zero. v2 corrects the historical prompt dtype wording to float32; it uses the previously exposed panels and is not an independent replication.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Switch all three methods and select a nonzero dot. Backup: measured DEV chart.

**Transition:** Read the new frozen final measurements.

## 18 · One state. Two benchmarks.

27:26–29:19 · 1.89 minutes · scene `#lm-final`

**Claim:** Four labels share one executed weight identity and one measured endpoint.

ARC-Easy has 512 final examples and PIQA has 256. Normalized accuracy divides continuation log likelihood by choice text character length, not token count; raw accuracy uses the unnormalized likelihood. These are actual new v2 outputs. The four selected states are identical and final predictions are reused with identity checks, so four labels do not provide four independent observations. The zero differences and zero-width paired intervals reflect the identical state.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Read normalized and raw accuracy separately. Backup: final endpoint slide.

**Transition:** Account for the actual work.

## 19 · Count work, not labels

29:19–30:16 · 0.95 minutes · scene `#work`

**Claim:** Target forwards, editor calls and reused predictions are different quantities.

The table records native counts and seconds. LM target forwards are per-choice requests; Adult calls are batched CPU forwards. They are not directly interchangeable units. Development includes real nonempty interventions even though the final selected state is unchanged. Reuse is exact-state reuse with matching origin, task panel, scorer, device and dtype. It avoids multiplying identical predictions into independent evidence.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Read work rows without summing incompatible forward units. Backup: work table.

**Transition:** What does this establish?

## 20 · Intervention, decision, selection

30:16–32:10 · 1.89 minutes · scene `#meaning`

**Claim:** Adult changes decisions. LM selection rejects change. Both are results.

The study connects three layers: an actual bounded weight intervention, paired changes in decisions, and the policy used to select candidates. Adult shows a small primary-metric improvement with an accuracy and probability-quality tradeoff. SmolLM2 v2 shows that eligible nonempty edits need not beat the unchanged candidate. This one exploratory session does not establish general editor ability or equal-compute synergy.

**Delivery pace:** Establish the question, allow the audience to read, and connect the claim to the preceding result.

**Demo / static backup:** Return to the Adult inspector or final endpoints if asked; backup: takeaways page.

**Transition:** Make the path from data to figure inspectable.

## 21 · The figure is a view of the data

32:10–33:06 · 0.95 minutes · scene `#reproduce`

**Claim:** Saved numeric evidence rebuilds the metrics and visuals without a model call.

The manifest binds numeric inputs and prompts. The portable analysis recomputes saved predictions; the visual build reads the same manifest. Building this publication snapshot did not call models. The original v2 measurement did complete. Exact native execution has separate explicit commands and environment requirements, described in the reproduction guide. Offline launch requires only Python and a local browser, not an install or API.

**Delivery pace:** Explain the axes or topology first. Read the exact selected state, then trace the intervention or comparison. Leave time for the audience to inspect before moving on.

**Demo / static backup:** Open the local manifest and reproduction guide; backup: printed links and hash.

**Transition:** Finish with the two distinct outcomes.

## 22 · Small edits. Measured consequences.

33:06–35:00 · 1.89 minutes · scene `#takeaways`

**Claim:** Improving the chosen metric and choosing an edit are separate questions.

Leave the audience with two observations: Adult changes the balance of errors, and SmolLM2 v2 selects no change. The unchanged candidate is scientifically meaningful. Discuss why balanced accuracy can rise while total correct decisions fall, what equal-compute and multi-session follow-ups would test, and why exact-state reuse is not replication. Reserve five minutes for questions after the thirty-five-minute narrative.

**Delivery pace:** Establish the question, allow the audience to read, and connect the claim to the preceding result.

**Demo / static backup:** Use appendix for formulas, full metrics, prompts and versions. Backup: PDF appendix.

**Transition:** Questions: intervention constraints, selection, or interpretation?

## Q&A · 35:00–40:00

Use the technical appendix for forward-pass and scoring equations, metrics,
bootstrap design, complete comparisons, prompts and version history. Likely
questions: why BA and accuracy disagree; why the clean BA denominator is
unsuitable; why candidate zero wins ties; whether shared history isolates synergy;
and why one reused LM state is not four replications. Explain the single-session
and unequal-allowance design once, with the exact paired contrasts.

If WebGL fails, use the semantic SVG mode. If the browser fails, use the frozen
PDF deck, which contains all main scenes and appendix. The offline ZIP includes
both PDFs and its Python localhost launcher. No network is needed.
