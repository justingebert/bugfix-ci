FROM python:alpine
RUN apk add --no-cache git
RUN git config --global user.email "ci@example.com" && \
    git config --global user.name "CI Bot" && \
    git config --global --add safe.directory '/workspace'

COPY apr_core/ apr_core/
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

CMD ["python", "-m", "apr_core.main"]