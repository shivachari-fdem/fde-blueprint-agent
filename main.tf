terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type    = string
  default = "vital-octagon-19612"
}

variable "region" {
  type    = string
  default = "us-central1"
}

resource "google_cloud_run_v2_service" "fde_agent" {
  name     = "fde-blueprint-agent"
  location = var.region
  
  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/cloud-run-source-deploy/fde-blueprint-agent:latest"
      ports {
        container_port = 8080
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
    }
  }
}
