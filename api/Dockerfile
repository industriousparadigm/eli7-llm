FROM python:3.11-slim

WORKDIR /app

# git: the curator shells out to it to version Diana's memory repo.
# safe.directory '*': the container runs as root over a host-owned bind mount,
# which git otherwise refuses with "dubious ownership".
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]