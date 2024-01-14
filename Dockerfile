FROM python:3.11-alpine

WORKDIR /usr/src/app

RUN apk add --no-cache gcc musl-dev postgresql-dev

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]