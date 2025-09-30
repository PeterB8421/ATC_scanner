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

# Install MySQL client for database connection
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev build-essential \
  && pip install mysqlclient

# Install dockerize
ENV DOCKERIZE_VERSION v0.6.1
RUN wget https://github.com/jwilder/dockerize/releases/download/${DOCKERIZE_VERSION}/dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz \
  && tar -C /usr/local/bin -xzf dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz \
  && rm dockerize-linux-amd64-${DOCKERIZE_VERSION}.tar.gz

# Upgrade pip
RUN pip install --upgrade pip

# Copy the Django project  and install dependencies
COPY requirements.txt  /app/

# run this command to install all dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project to the container
COPY . /app/

# Expose the Django port
EXPOSE 8000

# Run Django’s development server
CMD dockerize -wait tcp://$DATABASE_HOST:$DATABASE_PORT -timeout 60s -- python manage.py runserver 0.0.0.0:8000

