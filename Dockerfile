FROM python:alpine
RUN apk add --no-cache git
RUN git config --global user.email "ci@example.com" && \
    git config --global user.name "CI Bot"

COPY agent_core/ agent_core/
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "agent_core.main"]