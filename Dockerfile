# The wappalyzer-cli tool was rewritten in Go.  The previous
# `pip install git+https://github.com/gokulapap/wappalyzer-cli.git` no
# longer works because the repository has no Python packaging, so the
# binary is built from a pinned source revision instead.
FROM golang:1.25 AS build
ARG WAPPY_COMMIT=af32159f2f8c86faa285d81e8cf11b8cc0740973
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone https://github.com/gokulapap/wappalyzer-cli.git . \
 && git checkout ${WAPPY_COMMIT} \
 && CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/wappy ./cmd/wappy

FROM python@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
COPY --from=build /out/wappy /usr/local/bin/wappy
RUN apt update && apt install -y git && apt clean && rm -rf /var/lib/apt/lists/*
# The shared class is built from this repository, not from the published
# release: a worker that calls auth_headers(task) against a release that
# does not have it fails inside the scan.  scripts/build_workers.sh passes
# the local wheel; the default is the published release.
ARG B_HUNTERS_WHEEL=b-hunters==1.5.2
RUN pip install --no-cache-dir ${B_HUNTERS_WHEEL}
WORKDIR /app/service
COPY webtech /app/service/webtech
CMD ["python3", "-m", "webtech"]
