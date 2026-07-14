terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id                = "23724963-04db-44e4-8858-55c4bcd63dc8"
  resource_provider_registrations = "none"
}

locals {
  resource_group = "rg-pSiddhi3.0-2026-01-sem2-Jashwanth"
  location       = "centralindia"
  tags = {
    project = "pSiddhi-2026-01"
    owner   = "jashwanth.dhanasekaran"
  }
}

# --- Resource 1: Storage Account with static website ---
resource "azurerm_storage_account" "site" {
  name                     = "psiddhijashwanthsite"
  resource_group_name      = local.resource_group
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags

  static_website {
    index_document     = "index.html"
    error_404_document = "error.html"
  }
}

# --- Resource 2: Storage Container for assets ---
resource "azurerm_storage_container" "assets" {
  name                  = "assets"
  storage_account_id    = azurerm_storage_account.site.id
  container_access_type = "blob"
}

# --- Resource 3: Blob - index.html for static site ---
resource "azurerm_storage_blob" "index" {
  name                   = "index.html"
  storage_account_name   = azurerm_storage_account.site.name
  storage_container_name = "$web"
  type                   = "Block"
  content_type           = "text/html"
  source_content         = "<html><body><h1>DriftLens - Azure Static Site</h1><p>Deployed via Terraform</p></body></html>"

  depends_on = [azurerm_storage_account.site]
}

output "storage_website_url" {
  value = azurerm_storage_account.site.primary_web_endpoint
}