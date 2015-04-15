# install-packages

Installs packages specified with the `packages` option. It leverages caching to decrease build time.

# What's new

- Assume Yes to all queries and do not prompt

# Options

* `packages`: (required) The name(s) of the packages to install. Separate packages using a space.

# Example

Installs three packages `git`, `subversion` and `apache`:

    - install-packages:
        packages: git subversion apache

You can also specify version:

    - install-packages:
        packages: apache2=2.2.20-1ubuntu1

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

## 0.0.4

- Assume Yes to all queries and do not prompt

## 0.0.3

- Update readme
- Fixed readme

## 0.0.2

- Initial release
