FROM python:3.11-slim

WORKDIR /app

# System deps for audio processing (pydub/ffmpeg, soundfile)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch first, then the rest
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data at build time
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('stopwords')"

COPY . .

# HF Spaces exposes port 7860 by default
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
