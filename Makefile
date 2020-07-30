BUILDDIR=build

help:
	@echo '                                                               '
	@echo 'Usage:                                                         '
	@echo '   make clean                       remove the generated files '
	@echo '   make fullclean                   clean + remove tox, cache  '
	@echo '   make test                        run tests                  '
	@echo '   make link                        run lint checks            '
	@echo '   make build_docker                build docker image         '
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
	flake8 src/; exit 0;
	isort src/ --check-only -rc; exit 0;


test:
	coverage run manage.py test --keepdb

build_docker:
	docker build -t unicef/etools-base:local -f Dockerfile-base .
	docker build -t unicef/etools:local --build-arg BASE_TAG=local .
