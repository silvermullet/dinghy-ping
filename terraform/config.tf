#  backend specific configs
terraform {
  backend "s3" {
  }
}

provider "kubernetes" {}


