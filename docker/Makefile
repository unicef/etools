DATABASE_URL?=
DOCKER_IMAGE?=unicef/etools
TAG?=6.8
RUN_OPTIONS?=
.run:
	cd .. && docker run \
	 		--rm \
	 		--name=etools-dev \
			-e DATABASE_URL=${DATABASE_URL} \
			-e DISABLE_JWT_LOGIN=1 \
			-e DJANGO_DISABLE_EXISTING_LOGGERS=false \
			-e DJANGO_SETTINGS_MODULE=etools.config.settings.local \
			-e DEBUG=true \
			-e SECRET_KEY=123 \
			${RUN_OPTIONS} \
			${DOCKER_IMAGE}:${TAG} \
			${CMD}

shell:
	RUN_OPTIONS="-p 8000:8080 -it" \
	CMD='/bin/bash' \
		$(MAKE) .run

test:
	RUN_OPTIONS="-e DEBUG=0 \
				 -e X_FRAME_OPTIONS=DENY \
				 -e SESSION_COOKIE_SECURE=1 \
				 -e CSRF_COOKIE_SECURE=1 \
				 -e SECURE_HSTS_PRELOAD=1 \
				 -e SECURE_SSL_REDIRECT=1" \
	CMD='sh -c "django-admin check --deploy"' \
	$(MAKE) .run

build:
	cd .. && docker build \
		--squash \
		-t ${DOCKER_IMAGE}:${TAG} \
		-f docker/Dockerfile .
	docker images | grep unicef/etools

push: build
	docker push ${DOCKER_IMAGE}:${TAG}

release: push
	docker tag ${DOCKER_IMAGE}:${TAG} ${DOCKER_IMAGE}:latest
	docker push ${DOCKER_IMAGE}:latest
