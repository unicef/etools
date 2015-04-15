# pip-install

A step to execute the [pip command](http://pip.readthedocs.org/en/latest/). Without any arguments this step will try
to install the requirements defined in `requirements.txt`. The step will fail
if the file does not exist.

If you want to install only a single package, you can just set the
`requirements_file` parameter to an empty string and specify the packages
via the `packages_list` parameter:


```
    - pip-install
        requirements_file: ""
        packages_list: "mock"
```

By default the step will try to use wheel if the enviroment variable
`PIP_USE_WHEEL` is set to true. Wheel support however may fail, since not all
packages support wheel. However it can speed up future installs/builds
significantly. The [virtual-env](https://app.wercker.com/#applications/527bb985138f8aef26000c8f/tab/details) step can easily enable wheel support on the
[wercker/python](https://app.wercker.com/#applications/51acff65c67e056078000841/tab/details)
box.


## Options
* `requirements_file` (optional, default=requirements.txt). The
`requirements.txt` file to use. Set to empty if no requirements file is used.
* `packages_list` (optional, default=""). List of packages to install (usefull
for installing packages outside of requirements.txt). The property can contain
more than one package, specified as a single string seperated by spaces.
* `pip_command` (optional, default="pip"). Can be used to switch to python 3
specific pip on Ubuntu: pip-3.2.
* `auto_run_wheel` (optional, default=true). If the `PIP_USE_WHEEL` environment
variable is set to true. The pip install step will also run `pip wheel` before
running pip install. Settings `auto_run_wheel` to false will disable this
behavior.
* `cleanup_wheel_dir` (optional, default=false). If the `$PIP_WHEEL_DIR`
environment variable is set. Settings this property to true, will clenaup the
wheel dir (before running). This may be needed after updates to the box, or
when packages are updated without changing version numbers. If the wheel dir is
specified through a pip.ini this option will fail, only `$PIP_WHEEL_DIR` is
supported.
* `extra_args` (optional, default=""). This allows you to pass any argument
to the pip install command.
* `extra_wheel_args` (optional, default=""). This allows you to pass any argument
to the pip wheel command (if enabled).
Since the default wercker python environment uses a recent version of pip and
can use wheel to speed up subsequent installs, you may want to pass extra
arguments such as: `ALLOW_EXTERNAL` and `ALLOW_UNVERIFIED` to allow installs of
external and unverified packages/sources. See the [documentation on pip wheel](http://pip.readthedocs.org/en/latest/reference/pip_wheel.html)
for more information.

## Example

Basic usage:
```
    - pip-install
```

If your requirements file is not named `requirements.txt`, but dev-requirements.txt:

```
    - pip-install:
        requirements_file: "dev-requirements.txt"
```

Only install the mock and httpretty packages
```
    - pip-install:
        requirements_file: ""
        packages_list: "mock httpretty"
```

If you want to install a package besides the ones specified in the
requirements.txt file:

```
    - pip-install:
        packages_list: "mock httpretty"
```

To disable the automatic execution of wheel, use:
```
    - pip-install:
        auto_run_wheel: false
```

To run pip install, but with a clean up of the $PIP\_WHEEL\_DIR:

```
    - pip-install:
        cleanup_wheel_dir: true
```

# License

The MIT License (MIT)

Copyright (c) 2014 wercker

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Changelog

## 0.0.6
- added: extra\_args parameter support
- added: extra\_wheel\_args parameter support
- fix: a bash error when trying to install via packages\_list and requirements\_file

## 0.0.5
- `pip_command` option added

## 0.0.4

- `cleanup_wheel_dir` support added
- `requirements_file` support added
- `packages_list` option added

## 0.0.3

- `auto_run_wheel` property added
- `pip wheel` behavior added (if `$PIP_USE_WHEEL` is set to true )

## 0.0.1
- initial release
