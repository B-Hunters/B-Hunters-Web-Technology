FROM python:3.10-slim
RUN apt update && apt install -y git && apt clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir b-hunters==1.1.7 git+https://github.com/gokulapap/wappalyzer-cli.git
WORKDIR /app/service
COPY webtech /app/service/webtech
CMD [ "python", "-m", "webtech" ]