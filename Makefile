BUILDDIR=build

help:
	@echo '                                                               '
	@echo 'Usage:                                                         '
	@echo '   make clean                       remove the generated files '
	@echo '   make fullclean                   clean + remove tox, cache  '
	@echo '   make test                        run tests                  '
	@echo '   make link                        run lint checks            '
	@echo '                                                               '


clean:
	@rm -rf ${BUILDDIR} .pytest_cache src/unicef_attachments.egg-info dist *.xml .cache *.egg-info .coverage .pytest MEDIA_ROOT MANIFEST .cache *.egg build STATIC
	@find . -name __pycache__  -prune | xargs rm -rf
	@find . -name "*.py?" -o -name "*.orig" -o -name "*.min.min.js" -o -name "*.min.min.css" -prune | xargs rm -rf
	@rm -f coverage.xml flake.out pep8.out pytest.xml


fullclean:
	rm -fr .tox
	rm -f *.sqlite
	make clean


lint:
	flake8 src/ tests/; exit 0;
	isort src/ --check-only -rc; exit 0;


test:
	coverage run manage.py test --keepdb
