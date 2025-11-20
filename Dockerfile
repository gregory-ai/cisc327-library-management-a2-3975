
FROM python:3.9-slim-buster
 
# set working directory
WORKDIR /app
 
# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# copy application code
COPY . .
 
# expose the port the app runs on
EXPOSE 5000
 
# run the application
CMD ["python", "app.py"]

