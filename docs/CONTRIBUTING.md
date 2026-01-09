# Contributing to Python_PlaySEM

First off, thank you for considering contributing to Python_PlaySEM! It's people like you that make open source such a great community.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/<your-github-username-or-org>/Python_PlaySEM/issues/new)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

### Fork & create a branch

If this is something you think you can fix, then [fork Python_PlaySEM](https://github.com/<your-github-username-or-org>/Python_PlaySEM/fork) and create a branch with a descriptive name.

A good branch name would be (where issue #38 is the ticket you're working on):

```sh
git checkout -b 38-add-awesome-new-feature
```

### Get the test suite running

Make sure you're running the tests before you make any changes. You can run the tests with:

```sh
pytest
```

### Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first :smile_cat:

### Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with Python_PlaySEM's master branch:

```sh
git remote add upstream git@github.com:<your-github-username-or-org>/Python_PlaySEM.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 38-add-awesome-new-feature
git rebase master
git push --set-upstream origin 38-add-awesome-new-feature
```

Finally, go to GitHub and [make a Pull Request](https://github.com/<your-github-username-or-org>/Python_PlaySEM/compare)

### Keeping your Pull Request updated

If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.

To learn more about rebasing and merging, check out this guide from Atlassian: [Merging vs. Rebasing](https://www.atlassian.com/git/tutorials/merging-vs-rebasing).

## Code of Conduct

We have a [Code of Conduct](CODE_OF_CONDUCT.md) that we expect all contributors to adhere to. Please read it before contributing.

## How to get help

If you're having trouble, you can ask for help in a [GitHub Issue](https://github.com/<your-github-username-or-org>/Python_PlaySEM/issues).

Again, thank you for contributing!
