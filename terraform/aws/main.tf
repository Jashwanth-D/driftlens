terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  prefix = "psiddhi-jashwanth"
  tags = {
    project = "pSiddhi-2026-01"
    owner   = "jashwanth.dhanasekaran"
  }
}

resource "aws_s3_bucket" "site" {
  bucket = "${local.prefix}-site"
  tags   = local.tags
}

resource "aws_s3_bucket_website_configuration" "site" {
  bucket = aws_s3_bucket.site.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "site" {
  bucket     = aws_s3_bucket.site.id
  depends_on = [aws_s3_bucket_public_access_block.site]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.site.arn}/*"
    }]
  })
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  default_root_object = "index.html"
  tags                = local.tags

  origin {
    domain_name = aws_s3_bucket_website_configuration.site.website_endpoint
    origin_id   = "S3-${local.prefix}-site"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${local.prefix}-site"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

output "s3_website_url" {
  value = aws_s3_bucket_website_configuration.site.website_endpoint
}

output "cloudfront_url" {
  value = aws_cloudfront_distribution.site.domain_name
}
# ============================================
# WORKLOAD B - Serverless Function (AWS Lambda)
# ============================================

# --- Resource 6: IAM Role for Lambda ---
resource "aws_iam_role" "lambda_role" {
  name = "${local.prefix}-lambda-role"
  tags = local.tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# --- Resource 7: IAM Policy Attachment for CloudWatch Logs ---
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- Resource 8: Lambda Function ---
resource "aws_lambda_function" "hello" {
  filename         = "${path.module}/lambda/handler.zip"
  function_name    = "${local.prefix}-hello"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = filebase64sha256("${path.module}/lambda/handler.zip")
}

# --- Resource 9: Lambda Function URL (public endpoint, no auth) ---
resource "aws_lambda_function_url" "hello" {
  function_name      = aws_lambda_function.hello.function_name
  authorization_type = "NONE"
}

output "lambda_url" {
  value = aws_lambda_function_url.hello.function_url
}

# --- Resource 10: Lambda permission for public Function URL ---
resource "aws_lambda_permission" "hello_url" {
  statement_id           = "AllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.hello.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
