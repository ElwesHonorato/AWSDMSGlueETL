#!/bin/bash

# Script: create_deployment_package.sh
# Author: [Elwes Nunes]
# Description: This script creates a deployment package for AWS Lambda functions.
#              It installs specified Python libraries into a directory named 'package',
#              then zips all contents of the 'package' directory along with your Lambda
#              function code into a single ZIP file.

# # Prerequisites:
#       - Python installed
#       - pip installed
#       - Bash shell environment

# Usage: 
#       1. Copy 'create_lambda_deployment_package.sh' to the AWS Lambda path in your develpment environment.
#       2. Make the script executable if it's not already:
#           ```bash
#                 chmod +x create_lambda_deployment_package.sh
#           ```
#        3. Replace <requirements_file> with the path to your 'requirements.txt' file.


poetry export -f requirements.txt --output requirements.txt --without-hashes

rm -r package
# Create a directory named 'package'
mkdir package

# Check if requirements.txt exists
if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found."
    exit 1
fi

# Define package folder path
package_folder="package"

# Install Python libraries in the package folder
pip install -r requirements.txt --target "$package_folder"

# Zip the package folder
zip -r deployment_package.zip "$package_folder"
zip -ur deployment_package.zip LambdaFunction.py

rm -rf "$package_folder"
echo "Deployment package created successfully."
