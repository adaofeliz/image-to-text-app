FROM python:3.11-slim

# set workdir
WORKDIR /app

# install build dependencies and system libraries for OpenCV/PaddleOCR and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch first (from PyTorch index for better reliability)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY ./app ./app

# copy pull script
COPY pull.sh ./

# make script executable
RUN chmod +x pull.sh

ENV PYTHONUNBUFFERED=1

# expose port
EXPOSE 8000


CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]