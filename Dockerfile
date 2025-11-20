
FROM python:3.9-slim-buster
 
# set working directory
WORKDIR /app
 
# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# copy application code
COPY . .

# make Python recognize /app as a module directory
ENV PYTHONPATH=/app
 
# expose the port the app runs on
EXPOSE 5000
 
# use flask CLI so host works correctly
ENV FLASK_APP=app.py
CMD ["flask", "run", "--host=0.0.0.0"]

