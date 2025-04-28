FROM python:alpine

COPY agent_core/ agent_core/
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-m", "agent_core.cli"]