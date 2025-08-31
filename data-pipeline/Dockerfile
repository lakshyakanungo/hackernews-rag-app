# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Install the "Development Tools" group which includes gcc, make, and the 'cc' linker
# using yum, the package manager for Amazon Linux.
RUN yum groupinstall -y "Development Tools"

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the Python dependencies
RUN pip install -r requirements.txt

# Copy all your Python scripts from the 'scripts' directory into the container
# The first '.' refers to the scripts directory in your project
# The second '.' refers to the WORKDIR inside the container
COPY ./scripts/. .

# Set the CMD to your handler function
# Format: <filename>.<handler_function_name>
CMD [ "lambda_handler.handler" ]
