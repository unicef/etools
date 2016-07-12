# eTools and GitHub Best Practices - Contributing Guide

##Concepts Overview

###GitFlow

[GitFlow](https://datasift.github.io/gitflow/IntroducingGitFlow.html) is a branching model for git designed to allow teams to collaborate and continuously develop new features while keeping finished work separate.

It involves 5 major components within the eTools project:

  * Master branch
  * Develop branch
  * Feature branches
  * Staging branch
  * Hotfix branches

Feature branches are where the bulk of the work is done such as creating new features. Developers branch off of the develop branch, work on their feature(s) and submit a pull request  to merge the feature back into the develop branch when it is complete. This is also where *continuous integration* is used.

Approximately every 2 weeks (every sprint) the project is merged into the staging branch. This is where the new features and fixes are QA tested. As QA finds problems and fixes are made, this branch is frequently merged back into develop so the fixes are not lost as new development continues off of that branch. 

Every release,  the staging branch is merged into master and tagged with the release version number. The master branch is the released product; only finished and vigorously tested code is put here and made available to consumers.

Hotfix branches are used for emergency fixes for problems found after a major release to master. Hotfixes are branched directly off master; the fix is made and then merged back into master (while also being tagged) and into staging and develop (to make sure developers are working with this fix so it doesn’t pop up again in a new release).

###Continuous Integration

[Continuous integration (CI)](https://www.thoughtworks.com/continuous-integration) is a development practice requiring developers to very frequently integrate code into the develop branch.

Each integration is built and tested by an automated CI server. If there are any issues with the build, the team is notified and solves them before any new commits are made.

The idea is to avoid situations involving lots of independent code developed over a long period of time being integrated together only to find many problems that require lots of backtracking to find and fix. Continuous integration methodology means problems are often identified and solved right away since they involve code which was just recently worked on.

After a pull request has been approved and the project builds successfully, it is automatically deployed to a production environment. This is called *continuous deployment* and it allows the team quickly move towards working software and view the eTools develop stage app in an actual production environment.

##Practices and Rituals

###Commiting

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

###Tagging

[Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging) is a process that happens whenever a new release (or a hotfix) is merged with master. The release is tagged with a version number like `v1.2.0`

Tagging is also used on commits to label their association with a certain version of the application. Searching for that tag then gets a list of all the commits that were tagged as part of that version.

###Issues and Labels

The eTools team uses [Pivotal Tracker](https://www.pivotaltracker.com/) for issue tracking. It’s a way for team members to keep track of not only bugs but new feature ideas, optimizations, and more general “to-dos” and have the rest of the team discuss these issues.

Issues often have a milestone associated with them, like a project version or a specific time period to which the issue is relevant. There’s also a section for assignee's, who have been tasked with fixing that specific issue. Finally there are labels, which act as a way to organize issues, make them easily searchable, and give people a quick idea of what the issue involves.

###Issues in GitHub

Since not all developers will have access to eTools' private Pivotal Tracker dashboard, we recommend that any issues identified by developers without access to Pivotal Tracker will be raised in GitHub prior to fixing them in the code and making a Pull Request.

###Labels in GitHub

Labels in GitHub are used in a color coded system. The color is a universal identifier for the team. It could specify a platform that the issue is relevant to, a problem in production, a desire for feedback or improvements, or a new addition. The actual text on the label is more specific. A *platform* label could have the text “python”, and now someone looking at the label knows the issue resides on the Python back-end of the app. Or maybe an *addition* label will have “feature” in the text, so this issue involves a brand new feature that has yet to be added.

This diagram outlines the labeling methodology

![LabelGuide](http://i.imgur.com/dWfLNeS.png)

###Sources

https://datasift.github.io/gitflow/IntroducingGitFlow.html
https://www.thoughtworks.com/continuous-integration
https://git-scm.com/book/en/v2/Git-Basics-Tagging
https://guides.github.com/features/issues/
https://robinpowered.com/blog/best-practice-system-for-organizing-and-tagging-github-issues/
https://github.com/angular/angular.js/blob/master/CONTRIBUTING.md
