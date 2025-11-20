# Pushing this repo to GitHub

No remote is set yet. You can create a repo and push with:

```bash
# Create repo (replace org/name; private if desired)
gh repo create <org-or-user>/<repo> --private --source . --remote origin --push

# If you prefer manual remote + push:
git remote add origin https://github.com/<org-or-user>/<repo>.git
git push -u origin master
```

If you need to re-auth gh:
```bash
gh auth login -h github.com
```
