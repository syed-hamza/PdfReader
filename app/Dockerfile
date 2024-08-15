# Use the official Python 3.9 image
FROM python:3.9


RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    ffmpeg

# Set the working directory in the container

RUN pip install --upgrade pip
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the required packages
RUN pip install -r requirements.txt

# Clone the git repository into app/Libraries/
RUN git clone https://github.com/OpenTalker/SadTalker Libraries/

# Copy the rest of the application code into the container
COPY . /app
EXPOSE 5000
# Run the Python application

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the application
CMD ["flask", "run"]
