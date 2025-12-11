# Use the official Python runtime image
FROM python:3.13

# Create the app directory
RUN mkdir /app

# Set the working directory inside the container
WORKDIR /app

# Set environment variables
# Prevents Python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
#Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1


RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libfftw3-dev \
    pkg-config \
    sox \
    && rm -rf /var/lib/apt/lists/*

# Clone and build csdr from source
RUN git clone https://github.com/simonyiszk/csdr.git /tmp/csdr && \
    cd /tmp/csdr && \
    sed -i 's/^PARAMS_NEON.*/PARAMS_NEON = -O3 -ffast-math/' Makefile && \
    make && \
    make install && \
    rm -rf /tmp/csdr

# Upgrade pip
RUN pip install --upgrade pip

# Copy the Django project  and install dependencies
COPY requirements.txt  /app/

# Install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project to the container
COPY . /app/

# Expose the Django port
EXPOSE 10000

# Run Django’s development server
CMD python manage.py runserver 0.0.0.0:10000
