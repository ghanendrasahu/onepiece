# WorldView VR - AWS infrastructure (skeleton).
#
# Phase-appropriate: this file declares the *shape* of the production
# infrastructure. Terraform is applied per-region via workspaces. Media/edge
# (CloudFront, S3), the data plane (Aurora, MSK, Elasticache, OpenSearch,
# Milvus) and the control plane (EKS) are layered in as the roadmap advances.
#
# Reference: docs/09-devops-cicd.md

terraform {
  required_version = ">= 1.8"

  backend "s3" {
    bucket         = "worldview-terraform-state"
    key            = "envs/{env}/{region}/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "worldview-tf-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "env" {
  type        = string
  description = "Environment: dev | staging | perf | prod"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "service_replicas" {
  type    = number
  default = 2
}

provider "aws" {
  region = var.region
}

locals {
  name_prefix = "worldview-${var.env}"
}

# --- Control plane network ---
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name_prefix}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.env != "prod"
  enable_dns_hostnames = true
}

# --- EKS cluster (services run on Kubernetes, see docs/09) ---
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~= 20.0"

  cluster_name    = "${local.name_prefix}-cluster"
  cluster_version = "1.31"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    services = {
      desired_size = var.service_replicas
      min_size     = var.service_replicas
      max_size     = var.service_replicas * 4
      instance_types = ["m6i.large"]
    }
    # Media transcode runs on spot with Karpenter in prod (added in a later phase).
  }
}
