# Banking-Portal---CSC-2362

## Basic Setup from Old Repo
You don't need to use a new directory to swap to this repo, stay in your project root and run the following commands:

```
git remote set-url origin git@github.com:glorpst/Banking-Portal---CSC-2362.git
```
or
```
git remote set-url origin https://github.com/glorpst/Banking-Portal---CSC-2362.git
```
if you don't have SSH setup. Make sure that you commit your existing changes if you have any untracked work. Then run:
```
git fetch origin
git checkout dev
```
We will be committing our final changes to the dev branch, if you'd like, you can create a new branch (e.g., `feat/name-of-vuln`) beforehand to keep things neater. The main branch is currently just what was publicly available on the old repo, which I'll treat as our "vulnerable" version of the repo, while the dev branch will become our finalized "fixed" version.


### General Workflow
Every time before you start working, run this command:
```
git pull origin dev
```

Once you're ready to commit, run the following:
```
git add .
git commit -m "message"
git push origin dev
```
alternatively replace "." and "origin dev" with whatever file(s) or branch fit your scenario.
