FROM python:3.12-slim

WORKDIR /workspace/apps/agent

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/agent/requirements.txt /workspace/apps/agent/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/agent /workspace/apps/agent

CMD ["bash", "-lc", "python main.py && tail -f /dev/null"]
