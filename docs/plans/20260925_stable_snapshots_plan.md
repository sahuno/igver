# igver 1.4.0 plan: stable, reproducible snapshots (run-to-run variance)

Author: Samuel Ahuno (plan drafted with Claude Code), 2026-09-25
Status: PAUSED 2026-09-26 (usage limit), WIP on branch `feat/stable-snapshots`, not released. Ground rules as in `20260925_audit_bugfix_plan.md` §0.
Decision (user asked Claude to choose the most ambitious option, 2026-09-25): **snapshot stability protocol**,
aiming at pixel-identical output across runs, not just "less variance". An upstream IGV repaint patch was
not chosen: it means building and maintaining a forked IGV in the image, and the protocol below reaches the
same goal from outside IGV.

## Root cause (probe 9, 2026-09-25; 4 IGV processes × 3 regions × 4 captures per view)
- Differences only ever appear in the **first** capture of a view (1.28 % in ruler/ideogram rows, 0.58 % in the
  divider row). The second capture, taken back-to-back, already equals the captures taken 1 s and 4 s later.
- The settled captures are **pixel-identical across all 4 processes**, for all 3 regions.
- So the variance is a repaint race: IGV snapshots before the view has finished painting. A capture that equals
  the next capture of the same view is settled, and settled captures are reproducible.

## Design
Each region block (1.3.1 shape) gains stability captures in its verification directory:
- PNG output: `snapshot` (locus, 1.3.1) · `snapshot <name>` (real) · `snapshot igver_post.png`.
  Stable ⇔ real == post (pixel-identical).
- SVG/PDF output: `snapshot` (locus) · `snapshot igver_pre.png` · `snapshot <name>.svg` · `snapshot igver_post.png`.
  Stable ⇔ pre == post (the vector snapshot was taken inside a settled window).
After each IGV pass, `run_igv` checks the rendered blocks; an unstable block's real snapshot is deleted and the
region is re-rendered in a fresh IGV process, up to 2 extra passes (on top of the existing stall retries).
Still unstable after that → the last capture is kept and igver warns, listing it (exit 0). Locus verification
(`_verify_loci`) runs after all passes and ignores `igver_*` captures. Cost: one (PNG) or two (SVG) extra
captures per region (~0.1 s each, measured in 1.3.1) plus re-renders of the rare unstable regions.
The warning includes the fraction of regions that needed a re-render, so the rate is visible to users.

## Done when
- [ ] Unit (fake IGV that can return unsettled first captures): block shapes for PNG and SVG; real==post
      accepted; unstable → re-rendered in a new process and the settled capture delivered; never stable →
      kept with warning, exit 0; SVG uses pre/post; `_verify_loci` ignores `igver_*` files; retry count bounded.
- [ ] E2E (both modes): E1e becomes **pixel-identical** to E1 (new check `identical_to`, stricter than the old
      0.5 % rule); new S1: the same 3 regions rendered in 5 separate runs are byte-identical PNGs; all 33
      existing cases still pass; S2: `-f svg` region with pre/post captures renders.
- [ ] Cost measured on 20 regions (before/after) and recorded.
- [ ] Release 1.4.0 as for 1.3.1 (full e2e both modes, CI, pull, release gate, repoint, archive, ledger).

## Design changes
(append here: date, item, what changed, why)
- 2026-09-25 · First implementation (real snapshot vs back-to-back post capture) still left S1 differing:
  a 3-px strip at y≈333 (the divider under the alignment panel) had **two stable states** (probe 12: 1 of 24
  renders in the odd state), so no pair of captures could flag it.
- 2026-09-25 · IGV 2.19.8 has **no `sleep` batch command** (the log shows `UNKOWN COMMAND: sleep 100`); the
  earlier "settle waits" only added repaints. A real wait is `setSleepInterval W` + `setSleepInterval 0`
  (IGV sleeps `sleepInterval` after every command). Probes 9–11 timing conclusions were therefore about
  repaint counts, not time; their cross-process identity results stand.
- 2026-09-25 · With real waits between the real snapshot and the post capture, the strip kept flipping for
  seconds (probe 13), causing needless re-renders (20 regions: 78 s vs 31 s). `scrollToTop`/`tweakdivider`
  do not help (probe 14). **Root cause (probe 16):** with `maxPanelHeight 2000` (no scrolling) there are 0
  changes over time and one state per region in all 16 captures; the flips come from the scroll viewport of a
  panel whose reads overflow `maxPanelHeight`, which repaints asynchronously.
- 2026-09-25 · Final block: first capture (locus) · real wait `--settle-ms` (reads load) · re-apply the display
  mode and `maxPanelHeight` · [SVG: pre capture] · real snapshot · post capture immediately · reset. A capture right
  after the re-layout sees one state (probe 12: 24/24). Re-renders use a 4× longer wait (min 1 s).
  New CLI option `--settle-ms` (default 250).
- 2026-09-26 · **Controlled probe 18 (dedicated node, 12 processes × 3 regions) overturns the capture-timing
  design.** Regions whose reads overflow `maxPanelHeight 200`: 5–6 distinct renderings per 12 and real≠post in
  8–9/12, with or without a wait; some differing renders have real==post, so "identical unless flagged" does not
  hold. Region whose reads fit: 1 rendering, 0 unstable. Uncapped (`maxPanelHeight 2000`): 1 rendering (one
  outlier, flagged). Earlier 24/24 and S1 5/5 results were luck on a busy node. Conclusion: reproducibility
  needs the overflow removed at the source. Next: read IGV's offscreen snapshot painting (MainPanel /
  DataPanelContainer) to see what paints the divider strip; candidate designs: (1) opt-in fit-to-content panel
  height (deterministic, taller images), (2) render uncapped and splice to the capped layout, (3) patch IGV.
