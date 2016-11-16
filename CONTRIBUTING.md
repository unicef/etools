# eTools and GitHub Best Practices - Contributing Guide

##Pull Requests

* To be followed Strictly


Open a PR as soon as you start working on the new feature,
Refer to the issue you’re working on by tagging in a comment in the PR
Label your PR with - WIP (if work in progress) READY (if ready for merge) or BLOCKED (if you’re blocked by anything)
If ready, or blocked assign one or more of your colleagues to review the code and comments.. Include the Technical Lead

If you have a question that needs answering.. please label your pr with "question".

Update your PRs from the main branch you’re PRing into (on a daily basis if needed).
Update your branch in the end of every day even if you’re not ready.
In order to not freak other devs out.. If you’re writing some spectacularly outside-of-best-practices code just for testing or while in progress please comment that with #begin dev code -> #end dev code


KEEP YOUR PRs SLIM. If you’re changing code in 10 files, unless it’s comments or enhancements that probably means you should have split your work….


##Commiting

* guide, although we understand it's hard to keep commit messages on track, on big changes proper messaging is required.


The following guidelines should be followed when writing commit messages to ensure readability when viewing project history. The formatting can be added conventionally in git/GitHub or through the use of a CLI wizard ([Commitizen](https://github.com/commitizen/cz-cli)). To use the wizard, run `npm run commit` in your terminal after staging your changes in git.

Each commit message consists of a **header**, a **body** and a **footer**.

A typical commit message will look something like this... ![ExampleCommit](http://i.imgur.com/9SwquPt.png)
* `fix(copy): fix handling of typed subarrays` is the **header**. Each header consists of a **type**, a **scope** and a **subject**:
  * `fix` is the **type**. The type is picked from a limited set of words that categorize the change. Must be one of the following:
    * **feat**: A new feature
    * **fix**: A bug fix
    * **docs**: Documentation only changes
    * **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing
      semi-colons, etc)
    * **refactor**: A code change that neither fixes a bug nor adds a feature
    * **perf**: A code change that improves performance
    * **test**: Adding missing tests
    * **chore**: Changes to the build process or auxiliary tools and libraries such as documentation
      generation
  * `(copy)` is the **scope**, an optional field that specifies where in the application the change was made.
  * `fix handling of typed subarrays` is the **subject**, a brief description of the change.
    * use present tense: "change"
    * don't capitalize the first letter
    * no period at the end
* ``Previously, it would return a copy of the whole original typed array, not its slice. Now, the `byteOffset` and `length` are also preserved.`` This is the **body**. The body should include the motivation for the change and contrast this with previous behavior. Once again present tense is used.
* `Fixes #14842` and `Closes #14845` are both part of the **footer**. The footer is the place to
reference any GitHub issues or pull requests that this commit fixes/closes.

Any line of the commit message (including the header) should be no longer than 100 characters.

###Reverting a Commit

If the commit reverts a previous commit, the **type** should be `revert: ` followed by the entire header of the reverted commit in quotes. So to revert the example above you would write `revert: "fix(copy): fix handling of typed subarrays"`
In the body it should say: `This reverts commit <hash>.` where the hash is the SHA of the commit being reverted.
