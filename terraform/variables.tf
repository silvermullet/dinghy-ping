# Required variable

# will be passed by pipeline
variable "app" {
  description = "The unique app name"
}

variable "team" {
}

variable "owner" {
}

variable "product" {
}

# will be passed by pipeline
variable "environment" {
  description = "The environment associated with this service, ie dev, stage, preprod, or prod"
}

variable "namespace" {
  description = "The namespace where the application lives"
}

# will be passed by pipeline
variable "cluster_fqdn" {
  description = "Cluster domain name"
}

# will be passed by pipeline
variable "config_path" {
  description = "k8s config"
}

data "aws_caller_identity" "current" {}
