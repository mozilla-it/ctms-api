## Git

Protected Branches:
- `main`: staging env
- `prod`: production env

### Working

**Rebase** with master often to ensure both history is preserved
and the local copy is representative of the remote.


### Commits

Should should be **short** and descriptive.
A commit should be a complete logical change or shift.
_The feature and the corresponding tests should be in the same commit._
Commit early and often.


### Pull Requests

Pull Requests should be reviewed by another developer.

There should be a passed status check from a run of the build
 on any branch merging to main or prod.

Please provide detailed description of the feature and/or logical
modifications represented in the code changes.

### Branching

_Suggested_ branching format are as follows

Feature Branch:
- fb-{feature}
- feat-{feature}
- feature-{feature}

Fix Branch:
- hf-{fix}
- hotfix-{fix}
- bug-{bug}
- issue-{issue}

Task Branch:
- {project_tag}-{task_number}
- i.e...
    - BUG-0000123
    - ESSOPS-123

Release Branch (if necessary):
- rb-{version}
- release-{version}

"Experiment" Branches:
- junk-{experiment}


Please name branches descriptively.
