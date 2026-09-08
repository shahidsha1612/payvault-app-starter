variable "region" {
  description = "AWS region for the PayVault sandbox deployment."
  type        = string
  default     = "us-east-1"
}

variable "env" {
  description = "Environment suffix used to name resources (keep it short and unique)."
  type        = string
  default     = "dev"
}
