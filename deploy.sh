#!/bin/bash

AWS_REGION="us-east-1"
LAMBDA_FUNCTION_NAME="course-grab"

echo "zipping files..."


cd venv/lib/python3.11/site-packages
zip -r -q ../../../../lambda_code.zip .
cd ../../../../
zip -q lambda_code.zip lambda_function.py

echo "deploying to AWS Lambda..."

# Deploy the Lambda function
aws lambda update-function-code \
  --region $AWS_REGION \
  --function-name $LAMBDA_FUNCTION_NAME \
  --zip-file fileb://lambda_code.zip \


# Clean up the temporary zip file
echo "Cleaning up..."
rm lambda_code.zip

echo "Done!"
