# Issue #641 — post closure comment

Run after `gh auth login` (or with `GH_TOKEN` set):

```bash
gh issue comment 641 --repo DRYTRIX/TimeTracker --body-file .github/issue-641-closure-comment.md
gh issue close 641 --repo DRYTRIX/TimeTracker --reason "not planned"
```

Comment text: [.github/issue-641-closure-comment.md](issue-641-closure-comment.md)
