output "api_endpoint" {
  description = "Invoke URL for the PayVault charge API."
  value       = aws_apigatewayv2_api.http.api_endpoint
}

output "ledger_table" {
  description = "DynamoDB ledger table name."
  value       = aws_dynamodb_table.ledger.name
}

output "receipts_bucket" {
  description = "S3 bucket where receipts are written."
  value       = aws_s3_bucket.receipts.bucket
}
