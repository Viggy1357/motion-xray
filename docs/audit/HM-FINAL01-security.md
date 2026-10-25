# HM-FINAL01 — dependency audit and PostCSS remediation

25 October 2026. Nebius drafted the package change; coordinator reviewed the exact
diff and regenerated the lock using pinned pnpm9.12.1 inside Docker.

## Finding and fix

The initial production audit found four advisories in Next15.5.28's transitive
PostCSS8.4.31: two high and two moderate. The direct build dependency8.4.47 was
also older than the patched releases. Project CSS is authored locally; no demonstrated
user-CSS exploit path or incident is claimed.

- Pin direct PostCSS to8.5.23 and add `pnpm.overrides.postcss=8.5.23` so Next and
  the build tooling resolve the same patched version. Next/React versions unchanged.
- Native lock regeneration, not hand-written hashes. Only PostCSS resolution and
  associated peer/snapshot references change. No vulnerability suppression.
- [Upstream advisory](https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp)
  lists8.5.23 as patched; [release notes](https://github.com/postcss/postcss/releases/tag/8.5.23)
  describe the source-map security fix. Earlier advisories found:
  GHSA-qx2v-qp2m-jg93, GHSA-6g55-p6wh-862q, GHSA-r28c-9q8g-f849.

## Gates

- `pnpm audit --prod --json` after lock regeneration: exit0, zero advisories across
  56 production dependencies. This is registry coverage at this time, not proof of
  absence of every vulnerability.
- `scripts/test.sh web`: exit0, frozen install, type generation/check, production
  compilation and framework lint/type validity pass.
- `scripts/check-browser.sh`:108/108 pass on the patched build at360/375/1365.
- Existing local web dependency volume updated with frozen lock inside its Docker
  container; no host Node runtime installed and no API/worker configuration changed.

## Remaining build-tool advisory

The all-dependency audit reports one moderate advisory in
`postcss-selector-parser@6.1.5`, GHSA-rj75-hqrm-r3gf, patched in>=7.1.6. It comes
through Tailwind/postcss-nested build tooling. It is absent from the production-only
audit. The issue is CPU exhaustion on adversarial selector input; this application
does not accept user CSS/selectors. Keep builds restricted to trusted project CSS.

A major selector-parser override across Tailwind's6.x requirements is deferred
rather than asserted compatible. This remaining finding is documented, not ignored
or reported as zero in the all-dependency audit. Revisit the build-tool chain after
the submission freeze, or before introducing untrusted CSS/build inputs.

GitHub Dependabot alerts query returned403: alerts disabled. No permissions, alert
settings or security controls were changed. Python dependencies were exercised by
offline checks, not independently re-audited against a fresh vulnerability database.

Raw audit/log files are ignored under `artifacts/development/final01-*`. No credentials
or private media in this evidence. Source-review adjudication is separate in
`HM-FINAL01-source-review.md`.
