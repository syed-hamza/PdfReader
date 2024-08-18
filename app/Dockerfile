FROM python:3.10


RUN curl https://ollama.ai/install.sh | sh


WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg

# Set the working directory in the container

RUN pip install --upgrade pip
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1
RUN pip install --upgrade-strategy eager optimum[amd]



# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install -r requirements.txt


COPY . /app
EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the application
CMD ["flask", "run"]
