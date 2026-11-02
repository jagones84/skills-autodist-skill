## Description: <br>
Diagnose and recover broken Git state and worktree metadata with a staged, low-risk recovery flow for detached HEADs, phantom worktree locks, orphaned worktree entries, missing refs, zero hashes, and related branch or ref errors. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[delorenj](https://clawhub.ai/user/delorenj) <br>

### License/Terms of Use: <br>


## Use Case: <br>
Developers and engineers use this skill to snapshot broken Git repositories, route symptoms, generate low-risk repair plans, and verify worktree and ref health before escalating. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Repair guidance can affect refs, branches, worktrees, or .git/HEAD if applied to the wrong repository or without review. <br>
Mitigation: Confirm the target repository, back up .git, and review any command that changes Git metadata before execution. <br>
Risk: Manual cleanup or forced branch pointer changes can lose access to local-only work if reflog and worktree state are not checked first. <br>
Mitigation: Inspect reflog and worktree state, choose the smallest matching playbook, and run the verification checklist after each repair step. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/delorenj/skills/unfuck-my-git-state) <br>
- [Symptom Map](references/symptom-map.md) <br>
- [Recovery Checklist](references/recovery-checklist.md) <br>


## Skill Output: <br>
**Output Type(s):** [Text, Markdown, Shell commands, Guidance] <br>
**Output Format:** [Markdown with inline bash code blocks] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Produces staged diagnostic and recovery guidance; commands that change refs, branches, worktrees, or .git/HEAD require review before execution.] <br>

## Skill Version(s): <br>
0.2.1 (source: server release metadata) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
