FROM python:3.10-slim
WORKDIR /code
COPY ./requirements.txt .
RUN pip install --no-cache-dir uv \
    && uv pip install --system -r requirements.txt
COPY . /code/app
WORKDIR /code
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
