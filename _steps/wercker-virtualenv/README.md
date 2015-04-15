# Create a virtualenv

Create a virtual environment for python and activate it. The virtual
environment will also auto-install the python wheel package.

# Options

* `python_location` (optional) if not set, the result of `which python` is used
* `install_wheel` (optional, default=true)
* `virtualenv_location` (optional) if not specified, $HOME/venv will be used.

# Example

Simplest usage:
```yaml
build:
  steps:
    - virtualenv
```

An example that uses a non default python executable name/location:
```yaml
build:
  steps:
    - virtualenv:
        python_location=/usr/bin/python3.2
```

# License

The MIT License (MIT)

Copyright (c) 2013 wercker

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

## 1.0.0.
- switch to `which python` for finding default python location

## 0.0.5
- updated default virtualenv_location.
- python_path is now python_location

## 0.0.4
- PIP_WHEEL_DIR is now used instead of WERCKER_WHEEL_DIR

## 0.0.3
- fix for using wheels while building wheels (to prevent rebuilding existing wheels)

## 0.0.2
- WERCKER_WHEEL_DIR added (for use in the pip-install step)

## 0.0.1
- initial release
