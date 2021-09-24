FROM buildpack-deps:bullseye as build-stage

RUN set -eux; \
        apt-get update; \
        apt-get install -y --no-install-recommends \
            cmake \
        ; \
        rm -rf /var/lib/apt/lists/*;

RUN set -eux; \
        git clone --single-branch --branch 1.90-h3d1 https://github.com/uhziel/cppcheck.git --depth 1; \
        cd cppcheck && mkdir buildrelease && cd buildrelease; \
        cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=ON -DHAVE_RULES=ON ..; \
        make -j8; \
        make test; \
        make install;

FROM python:3 as production-stage

COPY --from=build-stage /usr/local/bin/cppcheck /usr/local/bin/cppcheck
COPY --from=build-stage /usr/local/share/Cppcheck /usr/local/share/Cppcheck

WORKDIR /usr/src/app

RUN set -eux; \
        pip install --no-cache-dir \
            lxml \
            redis \
        ;

COPY engine.json /
COPY . ./

VOLUME /code
WORKDIR /code

CMD ["/usr/src/app/bin/codeclimate-cppcheck"]
