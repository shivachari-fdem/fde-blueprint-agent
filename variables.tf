variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID"
  default     = "vital-octagon-19612"
}

variable "region" {
  type        = string
  description = "The precise region to deploy infrastructure"
  default     = "us-central1"
}

variable "db_password" {
  type        = string
  description = "Secure password for Cloud SQL Database"
  sensitive   = true
}
