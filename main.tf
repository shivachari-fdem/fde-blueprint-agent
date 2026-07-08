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

# 1. Provision highly available Cloud SQL PostgreSQL Database for memory state
resource "google_sql_database_instance" "agent_memory_db" {
  name             = "fde-agent-postgres"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier = "db-f1-micro"
    availability_type = "ZONAL"
  }
}

# 2. Automatically spawn the conversation database 
resource "google_sql_database" "conversations" {
  name     = "conversations"
  instance = google_sql_database_instance.agent_memory_db.name
}

# 3. Create the user
resource "google_sql_user" "users" {
  name     = "postgres"
  instance = google_sql_database_instance.agent_memory_db.name
  password = var.db_password
}

# 4. Deploy the Cloud Run Streamlit UI linking to the SQL Instance securely
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
        name  = "DB_HOST"
        value = google_sql_database_instance.agent_memory_db.public_ip_address
      }
      env {
        name  = "DB_NAME"
        value = google_sql_database.conversations.name
      }
    }
  }
}
