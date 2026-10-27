# Catalog CI and merge protection

`.github/workflows/catalog-ci.yml` runs on pushes to `main`, pull requests
targeting `main`, and manual dispatch. The stable job name is `catalog-gate`.
It uses Windows and the reference Python version because `requirements.lock`
contains Windows-specific dependencies. Dependencies are installed from the
lock file before installing this project without dependency re-resolution.

The job validates the dataset, checks the submitted catalog in read-only mode,
verifies frozen protocol inputs, runs pytest and Ruff, and evaluates every fault
class and clean control on all ten test cases. No catalog repair runs in CI.
Every command is a separate step so a failure stops the job. The job ends by
checking that tracked files have not changed.

## Activate required checks on GitHub

1. Push the workflow to `main` and wait for a successful `Catalog CI` run.
2. In repository Settings, configure a branch rule or ruleset targeting `main`.
3. Require pull requests and the `catalog-gate` status check before merging.
4. Require the branch to be up to date, apply the rule to administrators where
   supported, and leave the bypass list empty for the demonstration.
5. Disallow force pushes and deletion of the protected branch.

Available rule settings depend on repository visibility and the GitHub plan.
Record the settings actually available and enabled. The workflow alone does not
prevent merging: required checks must be enabled at repository level.

## Demonstrate a rejected proposal

Use a dedicated demonstration branch, not `main`. Change only one derived
timeout in `catalog/test_catalog.md` to an incorrect value, commit it, push that
branch, and open a pull request. Keep the checker, dataset, rules, and workflow
unchanged. Confirm that:

- the checker step fails with an explicit mismatch;
- the `catalog-gate` job is unsuccessful;
- the pull request merge control is blocked by the required check.

Save the PR URL, commit SHA, Actions run URL, checker error, and a screenshot of
the blocked merge control as thesis evidence. Close the deliberately invalid PR
after capturing the evidence; do not merge it. A red CI run by itself proves
detection, while the blocked merge control proves enforcement.

## Current evidence status

The workflow has been implemented locally. Its first hosted execution, branch
protection, and the deliberately invalid PR demonstration still require GitHub
verification. Local checker detection results and agent repair results are
separate measurements; neither substitutes for the hosted merge-blocking proof.
