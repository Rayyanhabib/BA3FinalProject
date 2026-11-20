# BUSA 310 Final Project: Team Guide to Git & GitHub

This repo is where our team shares code and data. This guide assumes **no technical background**. It explains what each step means, why we do it, and what you should see on screen, so you can follow along even if you've never used Git.

---

## Part 1: The Big Picture (read this first)

Think of our project like a shared Google Doc, except that instead of everyone editing the same live copy, **each person works on their own copy and then merges it into the shared one.** This stops us from accidentally overwriting each other's work.

### Key words

| Word | What it means | Everyday analogy |
|---|---|---|
| **Git** | The program on your computer that tracks changes to files. | A "track changes" system for the whole project folder. |
| **GitHub** | A website that stores our project online so everyone can reach it. | The shared drive where the team's official copy lives. |
| **Repository (repo)** | The project folder, including its full history of changes. | The project's folder plus a history book. |
| **Clone** | Download a full copy of the repo to your computer. | Making your own copy of a shared folder, once. |
| **`main` branch** | The official, "known good" version of the project. | The final copy we'd be willing to submit. |
| **Branch** | Your own side copy of the project where you can make changes safely. | A draft copy you work on before it goes into the final. |
| **Commit** | A saved snapshot of your changes, with a message describing them. | Hitting "Save" with a note saying what you did. Saved on **your computer only**. |
| **Push** | Upload your commits from your computer to GitHub. | Uploading your draft to the shared drive. |
| **Pull** | Download the latest changes from GitHub to your computer. | Refreshing to get everyone else's updates. |
| **Pull Request (PR)** | A request on GitHub saying "please review my branch and add it to `main`". | Handing your draft to a teammate for approval before it goes in the final. |
| **Merge** | Combine your branch into `main`. | Putting the approved draft into the final copy. |
| **Merge conflict** | Git can't tell how to combine two people's edits to the same part of a file. | Two people rewrote the same sentence, and someone has to choose. |

### How the pieces move

```
   GitHub (online, shared)
      ^                |
  git push          git pull
      |                v
   Your computer (your own copy)
```

- **Your computer → GitHub:** `git push`
- **GitHub → your computer:** `git pull`
- Commits stay on your computer until you push them. **A commit alone does not share your work.**

---

## Part 2: One-Time Setup (do once per computer)

### Step 1: Install Git
Download from <https://git-scm.com/downloads> and install with the default options.

*Optional but recommended for beginners:* [GitHub Desktop](https://desktop.github.com/) does everything below with buttons instead of typed commands. If you use it, the **ideas** in this guide still apply (pull, branch, commit, push, PR); the buttons are named the same.

### Step 2: Open a terminal
- **Windows:** search for **PowerShell** or **Git Bash** in the Start menu.
- **Mac:** open **Terminal**.

A terminal is a text window where you type commands and press **Enter** to run them.

### Step 3: Tell Git who you are
Run these two commands, replacing the quoted text with your own details:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@email.com"
```

**Why:** Git stamps every saved change with your name and email, so the team can see who did what. Use the **same email as your GitHub account**. You only do this once per computer.

### Step 4: Download (clone) the project
Go to the repo page on GitHub, click the green **Code** button, and copy the web address (URL). Then run:

```powershell
git clone <paste-the-url-here>
cd final-project
```

**What this does:** `git clone` downloads the whole project into a new folder. `cd final-project` ("change directory") moves your terminal **into** that folder. All later commands must be run from inside this folder.

**Tip:** if a command says `fatal: not a git repository`, you're in the wrong folder. Use `cd` to get into the project folder.

---

## Part 3: Your Normal Workflow (every time you work)

Follow these steps **in order, every time**. Skipping steps is how most mistakes happen.

### Step 1: Get the latest version of the project

```powershell
git checkout main
git pull
```

**What these do:**
- `git checkout main` switches you to the main (official) version.
- `git pull` downloads any changes teammates have added since you last checked.

**Why:** If you start working on an old copy, your changes may clash with newer ones. **Do this at the start of every work session.**

**What you'll see:** either `Already up to date.` (nothing new) or a list of files that were updated.

---

### Step 2: Create your own branch

```powershell
git checkout -b yourname-short-description
```

**Example:** `git checkout -b may-add-survey-data`

**What this does:** It creates a new branch with that name **and** switches you onto it. Anything you change from now on stays on your branch and does **not** touch `main`.

**Why:** `main` is our official version. If you edit it directly and make a mistake, everyone is affected. A branch lets you experiment safely, and nothing reaches `main` until a teammate has reviewed it.

**Naming tips:** use lowercase, no spaces (use `-`), and include your name and what you're doing. Make a **new branch for each new task**.

**What you'll see:** `Switched to a new branch 'may-add-survey-data'`

**Check anytime which branch you're on:**
```powershell
git branch
```
The current branch has a `*` next to it. **Before you start editing, make sure it is *not* `main`.**

---

### Step 3: Do your work

Open the files in whatever program you normally use (Excel, RStudio, VS Code, Python, etc.), edit, add data or write code, and **save the files normally**.

At this point Git knows the files changed, but it has not saved a snapshot yet. That's the next steps.

---

### Step 4: Look at what you changed

```powershell
git status
```

**What this does:** It lists which files you've edited, added or deleted since your last commit.

**Why:** It's a safety check. You can confirm that you changed what you meant to, and **only** that. Run it any time you're confused about where things stand.

**How to read it:**
- **"Changes not staged for commit"** (red): files you modified or deleted.
- **"Untracked files"** (red): brand-new files Git hasn't seen before.
- **"Changes to be committed"** (green): files you've already staged (Step 5) and are ready to commit.

*Optional:* `git diff` shows the exact lines that changed, line by line. Press `q` to exit it.

---

### Step 5: Save your changes (stage, then commit)

This is a **two-part save**.

**Part A: Stage** (choose what goes in the snapshot)
```powershell
git add .
```
The `.` means "everything I changed." To include only specific files, name them:
```powershell
git add data/survey_clean.csv
```

**Part B: Commit** (take the snapshot)
```powershell
git commit -m "Add cleaned survey data and summary chart"
```
The text in quotes is your **commit message**, a short description of what you did.

**Why two parts?** Staging lets you choose what goes into each snapshot. Committing then saves it.

**Writing good commit messages:**
- Good: `Clean missing values in survey data`, `Add regression analysis for Q3`
- Bad: `stuff`, `update`, `asdf`, `final final v2`

Teammates read these to understand the history, so make them clear.

**How often?** After each meaningful chunk of work (for example, finishing a cleaned dataset), not once a week. Small, frequent commits are safer and easier to undo.

**Important:** a commit is saved **only on your computer**. Your teammates can't see it yet.

---

### Step 6: Upload your work to GitHub (push)

```powershell
git push -u origin HEAD
```

**What this does:** It sends your branch and its commits to GitHub.

**About `-u origin HEAD`:** this tells Git "upload my *current* branch to GitHub and remember the link." You only need the `-u origin HEAD` version the **first time** you push a new branch. After that, `git push` alone is enough.

**What you'll see:** lines about "Writing objects", and a link such as `Create a pull request for 'may-add-survey-data' on GitHub by visiting: ...`. You can click that link.

**First time pushing?** A window may pop up asking you to sign in to GitHub. Sign in and continue.

---

### Step 7: Create a Pull Request (PR)

A PR is how you ask the team to review your work and add it to `main`.

1. Go to the repo on GitHub. You'll usually see a yellow banner with a **Compare & pull request** button. Click it. (You can also click the link printed in the terminal after your push.)
2. **Title:** a short summary, e.g. `Add cleaned survey data`.
3. **Description:** write what you changed and why, and anything reviewers should look at.
4. On the right side, under **Reviewers**, choose a teammate to review.
5. Click **Create pull request**.

**Then:**
- Your reviewer looks at the changes and either **approves** or **requests changes**.
- If they request changes: make the edits on your computer, then repeat Steps 4, 5 and 6 (`git status` → `git add .` → `git commit -m "..."` → `git push`). The PR updates automatically.
- When it's approved, click **Merge pull request** → **Confirm merge**. Your work is now part of `main`.

**Why a PR instead of pushing straight to `main`?** A second pair of eyes catches mistakes (wrong data, broken code) before they affect everyone.

*Optional command-line way (needs the GitHub CLI):* `gh pr create --fill`

---

### Step 8: Clean up after your PR is merged

```powershell
git checkout main
git pull
```

**What this does:** It switches back to `main` and downloads the latest version, which now includes your merged work and anyone else's.

**Then** go back to **Step 2** (new branch) for your next task. Start every new task from an up-to-date `main`.

---

## Part 4: The Whole Loop on One Screen

```powershell
git checkout main                       # 1. go to main
git pull                                #    download latest
git checkout -b yourname-task           # 2. make your own branch
# ...do your work and save files...     # 3. edit
git status                              # 4. check what changed
git add .                               # 5. stage your changes
git commit -m "What I did"              #    save a snapshot
git push -u origin HEAD                 # 6. upload to GitHub
# open a Pull Request on GitHub,        # 7. get a review, then merge
# get it reviewed, then merge
git checkout main                       # 8. go back to main
git pull                                #    download the merged result
```

---

## Part 5: Other Useful Commands

| Command | What it does | When to use it |
|---|---|---|
| `git branch` | Lists branches and marks your current one with `*`. | To confirm you're **not** on `main` before editing. |
| `git status` | Shows what changed and what's staged. | Any time you're unsure. |
| `git diff` | Shows exact line-by-line changes. Press `q` to exit. | Before committing, to double-check. |
| `git log --oneline -10` | Shows the last 10 commits. Press `q` to exit. | To see who changed what, and when. |
| `git pull` (while on your branch) | Downloads new commits for the branch you're on. | When a teammate has pushed to the **same** branch. |
| `git stash` | Temporarily sets aside unsaved changes. | If you need to switch branches but aren't ready to commit. |
| `git stash pop` | Brings the stashed changes back. | After you switch back. |
| `git restore filename` | **Throws away** your unsaved edits to that file. | If you made a mess and want the last committed version. **This cannot be undone.** |

---

## Part 6: Working with Data

- **File size limit:** GitHub **rejects any file over 100 MB**, and big files slow down everyone's downloads. For large datasets, share them another way (e.g. Google Drive) and write the link in the README.
- **Use CSV instead of Excel (`.xlsx`) when you can.** Git can show line-by-line changes in a CSV, but an Excel file is a single opaque blob, so two people editing one will conflict with no easy fix.
- **Keep raw data untouched.** Put cleaned or processed versions in a separate file or folder, so you can always go back to the original.
- **Never commit sensitive data:** passwords, API keys, personal or private information. Once something is pushed to GitHub, it is very hard to fully remove.
- **Don't rename or move a shared file** without telling the team, since it can confuse everyone's copies.

---

## Part 7: Avoiding Problems as a Team

- **Pull before you start. Push before you stop.**
- **Don't edit the same file at the same time** as someone else. Agree on who works on which file.
- **Tell the team what you're working on** (group chat) to avoid overlap.
- **Don't leave work only on your computer.** Push at the end of each session so it's backed up.
- **Never work directly on `main`.**

---

## Part 8: When Things Go Wrong

### "Merge conflict"
**What it means:** you and a teammate changed the same lines of the same file, and Git doesn't know which to keep.

**What to do:**
1. **Don't panic and don't delete anything.** Nothing is lost.
2. Open the file. You'll see markers like this:
   ```
   <<<<<<< HEAD
   your version of the line
   =======
   teammate's version of the line
   >>>>>>> main
   ```
3. Decide which version to keep (or combine them), and **delete the marker lines** (`<<<<<<<`, `=======`, `>>>>>>>`).
4. Save the file, then run `git add .` and `git commit -m "Resolve merge conflict"`.
5. If unsure, **ask a teammate** and fix it together. In VS Code, buttons labelled **Accept Current / Incoming / Both** make this easier.

### "fatal: not a git repository"
You're in the wrong folder. Use `cd` to move into the project folder, then try again.

### "Your branch is behind" or "failed to push some refs"
Someone else pushed changes you don't have yet. Run `git pull`, then try `git push` again.

### "I accidentally edited on `main`"
Don't commit or push. Run `git checkout -b yourname-task` right away. Your edits come with you to the new branch, and you can continue from Step 4.

### "I committed to `main` by accident"
**Don't push.** Tell the team and ask someone who knows Git to help.

### "I'm lost / not sure what state things are in"
Run `git status` and `git branch`, and send the output to a teammate. Nothing is damaged by *looking*.

### Commands you should never run unless someone experienced tells you to
- `git push --force`: can erase teammates' work on GitHub.
- `git reset --hard`: permanently deletes your uncommitted changes.

---

## Part 9: Quick Glossary of What You'll See in the Terminal

| Message | Meaning |
|---|---|
| `Already up to date.` | Nothing new to download. You're current. |
| `nothing to commit, working tree clean` | You have no unsaved changes. |
| `Switched to branch '...'` | You moved to that branch. |
| `Switched to a new branch '...'` | You created and moved to a new branch. |
| `To github.com:...` followed by `-> branch-name` | Your push worked. |
| `CONFLICT (content): Merge conflict in ...` | See "Merge conflict" above. |

---

**Still stuck?** Ask in the team chat, and include a copy of the exact message you see in the terminal. It makes it much easier for someone to help.
