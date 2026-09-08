# =============================================================================
# PayVault — payment intake + ledger  (INTENTIONALLY NON-COMPLIANT STARTER)
# -----------------------------------------------------------------------------
# This is a WORKING but deliberately flawed workload. Do NOT "fix" this file by
# rewriting the app. Your capstone is to ADD a governance baseline (new .tf),
# policy-as-code, a CI gate, an OSCAL component, and an evidence chain so that
# the flaws documented in GAPS.md are detected and remediated.
#
# Every flaw below is tagged with its gap id (PV-0x). Leave the tags in place.
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  name = "payvault-${var.env}"
}

# -----------------------------------------------------------------------------
# Ledger table.
# PV-01: cardholder PAN is written here in cleartext (see handler.py).
# PV-03: no server-side encryption / no customer-managed KMS key.
# -----------------------------------------------------------------------------
resource "aws_dynamodb_table" "ledger" {
  name         = "${local.name}-ledger"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "txn_id"

  attribute {
    name = "txn_id"
    type = "S"
  }

  # PV-03: encryption-at-rest is intentionally left at the AWS-owned default —
  # no customer-managed key, no key rotation, no BYOK.
}

# -----------------------------------------------------------------------------
# Receipts bucket.
# PV-04: bucket is world-readable — no public access block, public-read ACL.
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "receipts" {
  bucket        = "${local.name}-receipts"
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "receipts" {
  bucket = aws_s3_bucket.receipts.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "receipts" {
  depends_on = [aws_s3_bucket_ownership_controls.receipts]
  bucket     = aws_s3_bucket.receipts.id
  acl        = "public-read" # PV-04: receipts (with PAN in them) are public.
}

# PV-04: NOTE — there is deliberately no aws_s3_bucket_public_access_block here.
# PV-03: NOTE — there is deliberately no SSE configuration on this bucket.

# -----------------------------------------------------------------------------
# Lambda execution role.
# PV-06: attaches an inline policy allowing "*" on "*" (god-mode).
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda" {
  name = "${local.name}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_admin" {
  name = "${local.name}-lambda-admin"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "*" # PV-06: wildcard action.
      Resource = "*" # PV-06: wildcard resource.
    }]
  })
}

# -----------------------------------------------------------------------------
# The charge handler.
# PV-02 / PV-08: full PAN + CVV are logged and CVV is persisted (see handler).
# PV-09: secrets passed as plaintext environment variables.
# -----------------------------------------------------------------------------
data "archive_file" "handler" {
  type        = "zip"
  source_file = "${path.module}/lambda/handler.py"
  output_path = "${path.module}/build/handler.zip"
}

resource "aws_lambda_function" "charge" {
  function_name    = "${local.name}-charge"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.handler.output_path
  source_code_hash = data.archive_file.handler.output_base64sha256
  timeout          = 15

  environment {
    variables = {
      LEDGER_TABLE   = aws_dynamodb_table.ledger.name
      RECEIPTS_BUCKET = aws_s3_bucket.receipts.bucket
      # PV-09: hardcoded plaintext secrets in the function configuration.
      # (Obvious placeholders — the flaw is that a real secret would live here.)
      PROCESSOR_API_KEY = "REPLACE_ME_processor_api_key_stored_in_plaintext"
      HMAC_SIGNING_KEY  = "REPLACE_ME_hmac_signing_key_stored_in_plaintext"
    }
  }
}

# -----------------------------------------------------------------------------
# HTTP API.
# PV-05: no authorizer, no WAF, no TLS floor / throttling — wide open.
# PV-07: no access logging configured on the stage.
# -----------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "charge" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.charge.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "charge" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /charge"
  target    = "integrations/${aws_apigatewayv2_integration.charge.id}"
  # PV-05: authorization_type defaults to NONE.
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
  # PV-07: no access_log_settings block — requests are not audit-logged.
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGWInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.charge.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

# PV-07 / PV-10: NOTE — no aws_cloudtrail, no evidence vault, no Object Lock,
# no KMS key rotation anywhere in the starter. Add them in your baseline.
