FROM speech_to_text:base

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
