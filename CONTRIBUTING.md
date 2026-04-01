# Contributing Guide — Project Sandy

## Branching Strategy

### Protected Branches

| Branch | Purpose | Direct Push Allowed? |
|--------|---------|----------------------|
| `main` | Stable, production-ready code | **No — never push directly** |
| `dev` | Active development & integration testing | **No — merge via PR only** |

### Workflow

1. **Create a feature branch** from `dev`:

   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```

2. **Do your work** on the feature branch. Commit early and often.

3. **Push your branch** and open a Pull Request targeting `dev`:

   ```bash
   git push -u origin feature/your-feature-name
   ```

4. **Request a review** — at least one team member should approve the PR before merging.

5. **Merge into `dev`** once approved. Delete the feature branch after merge.

6. **`main` is off-limits** — only the team lead merges `dev` into `main` for stable releases.

### Branch Naming Conventions

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New functionality | `feature/enrollment-api` |
| `fix/` | Bug fixes | `fix/attendance-timestamp` |
| `hotfix/` | Urgent production fixes | `hotfix/auth-bypass` |
| `chore/` | Maintenance, config, docs | `chore/update-dependencies` |

## Commit Messages

- Keep the subject line under 72 characters.
- Use present tense ("Add feature" not "Added feature").
- Reference related issues when applicable (e.g. `Fix #12`).

## Code Reviews

- Every PR needs at least **one approval** before merging.
- Review for correctness, readability, and consistency with existing code.
- Keep feedback constructive and specific.

## Important Rules

- **Never push directly to `main` or `dev`.**
- **Never force-push** to shared branches.
- **Always pull the latest `dev`** before creating a new branch.
- **Delete your feature branch** after it has been merged.
