# Terraform configuration for Spot Instances with Node Groups
# This configuration enables cost optimization while maintaining high availability

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.this.token
}

data "aws_eks_cluster_auth" "this" {
  name = module.eks.cluster_name
}

# Spot Instance Node Groups for Market Intel Brain
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version
  vpc_id          = var.vpc_id
  subnet_ids      = var.private_subnet_ids

  # EKS Cluster Configuration
  cluster_endpoint_public_access = true
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # Spot Instance Node Groups
  node_security_group_id = var.node_security_group_id
  node_security_group_tags = {
    "kubernetes.io/cluster/${var.cluster_name}" = null
  }

  # Go Gateway Spot Instance Node Group
  node_groups = {
    go_gateway_spot = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 2
      
      instance_types = ["m5.large", "m5a.large", "m5d.large", "c5.large", "c5a.large"]
      
      capacity_type  = "SPOT"
      
      k8s_labels = {
        "app.kubernetes.io/name"     = "market-intel-brain"
        "app.kubernetes.io/component" = "go-gateway"
        "node-lifecycle"              = "spot"
        "spot-instance"              = "true"
      }
      
      additional_tags = {
        "Name"        = "${var.cluster_name}-go-gateway-spot"
        "Environment" = var.environment
        "Component"   = "go-gateway"
        "InstanceType" = "spot"
        "CostOptimized" = "true"
      }
      
      taints = {
        "spot-instance" = {
          key    = "spot-instance"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      launch_template_name   = "${var.cluster_name}-go-gateway-spot"
      launch_template_version = "$Latest"
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          volume_type = "gp3"
          volume_size = 50
          iops        = 3000
          throughput  = 125
          encrypted   = true
        }
      }
      
      user_data = base64encode(templatefile("${path.module}/user-data-spot.sh", {
        cluster_name = var.cluster_name
        component    = "go-gateway"
        shutdown_grace_period = 30
      })
    }
    
    # Rust Engine Spot Instance Node Group
    rust_engine_spot = {
      desired_capacity = 2
      max_capacity     = 8
      min_capacity     = 1
      
      instance_types = ["c5.large", "c5a.large", "c5d.large", "m5.large", "m5a.large"]
      
      capacity_type  = "SPOT"
      
      k8s_labels = {
        "app.kubernetes.io/name"     = "market-intel-brain"
        "app.kubernetes.io/component" = "rust-engine"
        "node-lifecycle"              = "spot"
        "spot-instance"              = "true"
        "compute-optimized"           = "true"
      }
      
      additional_tags = {
        "Name"        = "${var.cluster_name}-rust-engine-spot"
        "Environment" = var.environment
        "Component"   = "rust-engine"
        "InstanceType" = "spot"
        "CostOptimized" = "true"
        "ComputeOptimized" = "true"
      }
      
      taints = {
        "spot-instance" = {
          key    = "spot-instance"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
        "compute-optimized" = {
          key    = "compute-optimized"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      launch_template_name   = "${var.cluster_name}-rust-engine-spot"
      launch_template_version = "$Latest"
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          volume_type = "gp3"
          volume_size = 100
          iops        = 3000
          throughput  = 125
          encrypted   = true
        }
      }
      
      user_data = base64encode(templatefile("${path.module}/user-data-spot.sh", {
        cluster_name = var.cluster_name
        component    = "rust-engine"
        shutdown_grace_period = 30
      })
    }
    
    # Analytics Spot Instance Node Group
    analytics_spot = {
      desired_capacity = 1
      max_capacity     = 5
      min_capacity     = 0
      
      instance_types = ["m5.large", "m5a.large", "m5d.large", "r5.large", "r5a.large"]
      
      capacity_type  = "SPOT"
      
      k8s_labels = {
        "app.kubernetes.io/name"     = "market-intel-brain"
        "app.kubernetes.io/component" = "analytics"
        "node-lifecycle"              = "spot"
        "spot-instance"              = "true"
        "memory-optimized"           = "true"
      }
      
      additional_tags = {
        "Name"        = "${var.cluster_name}-analytics-spot"
        "Environment" = var.environment
        "Component"   = "analytics"
        "InstanceType" = "spot"
        "CostOptimized" = "true"
        "MemoryOptimized" = "true"
      }
      
      taints = {
        "spot-instance" = {
          key    = "spot-instance"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
        "memory-optimized" = {
          key    = "memory-optimized"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      launch_template_name   = "${var.cluster_name}-analytics-spot"
      launch_template_version = "$Latest"
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          volume_type = "gp3"
          volume_size = 80
          iops        = 3000
          throughput  = 125
          encrypted   = true
        }
      }
      
      user_data = base64encode(templatefile("${path.module}/user-data-spot.sh", {
        cluster_name = var.cluster_name
        component    = "analytics"
        shutdown_grace_period = 30
      })
    }
    
    # Vector Store Spot Instance Node Group
    vector_store_spot = {
      desired_capacity = 1
      max_capacity     = 4
      min_capacity     = 1
      
      instance_types = ["r5.large", "r5a.large", "r5d.large", "m5.large", "m5a.large"]
      
      capacity_type  = "SPOT"
      
      k8s_labels = {
        "app.kubernetes.io/name"     = "market-intel-brain"
        "app.kubernetes.io/component" = "vector-store"
        "node-lifecycle"              = "spot"
        "spot-instance"              = "true"
        "memory-optimized"           = "true"
        "vector-store"               = "true"
      }
      
      additional_tags = {
        "Name"        = "${var.cluster_name}-vector-store-spot"
        "Environment" = var.environment
        "Component"   = "vector-store"
        "InstanceType" = "spot"
        "CostOptimized" = "true"
        "MemoryOptimized" = "true"
        "VectorStore" = "true"
      }
      
      taints = {
        "spot-instance" = {
          key    = "spot-instance"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
        "memory-optimized" = {
          key    = "memory-optimized"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
        "vector-store" = {
          key    = "vector-store"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
      
      launch_template_name   = "${var.cluster_name}-vector-store-spot"
      launch_template_version = "$Latest"
      
      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          volume_type = "gp3"
          volume_size = 150
          iops        = 3000
          throughput  = 125
          encrypted   = true
        }
      }
      
      user_data = base64encode(templatefile("${path.module}/user-data-spot.sh", {
        cluster_name = var.cluster_name
        component    = "vector-store"
        shutdown_grace_period = 30
      })
    }
  }

  # Cluster access entry
  manage_aws_auth_configmap = true
  
  aws_auth_roles = [
    {
      rolearn  = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.cluster_name}-node-role"
      username = "system:node:{{EC2PrivateDNSName}}"
      groups   = ["system:nodes", "system:bootstrappers"]
    }
  ]
}

# Spot Instance Interruption Handling
resource "aws_cloudwatch_event_rule" "spot_interruption" {
  name_prefix = "${var.cluster_name}-spot-interruption-"
  description = "Capture EC2 Spot Instance Interruption Warnings"

  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Spot Instance Interruption Warning"]
  })
}

resource "aws_cloudwatch_event_target" "spot_interruption_sns" {
  rule      = aws_cloudwatch_event_rule.spot_interruption.name
  target_id = "SpotInterruptionSNS"
  arn       = aws_sns_topic.spot_interruption.arn
}

resource "aws_sns_topic" "spot_interruption" {
  name_prefix = "${var.cluster_name}-spot-interruption-"
  tags = {
    Name        = "${var.cluster_name}-spot-interruption"
    Environment = var.environment
    Component   = "spot-instances"
  }
}

# Lambda Function for Spot Instance Termination Handling
resource "aws_lambda_function" "spot_termination_handler" {
  function_name = "${var.cluster_name}-spot-termination-handler"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "python3.9"
  timeout       = 300

  environment {
    variables = {
      CLUSTER_NAME = var.cluster_name
      NAMESPACE    = "market-intel-brain"
    }
  }

  tags = {
    Name        = "${var.cluster_name}-spot-termination-handler"
    Environment = var.environment
    Component   = "spot-instances"
  }
}

# IAM Role for Lambda Function
resource "aws_iam_role" "lambda_exec" {
  name = "${var.cluster_name}-spot-termination-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  }
}

# Lambda Policy for EKS Access
resource "aws_iam_role_policy_attachment" "lambda_eks_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole"
}

# SNS Subscription for Lambda
resource "aws_sns_topic_subscription" "spot_interruption_lambda" {
  topic_arn = aws_sns_topic.spot_interruption.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.spot_termination_handler.arn
}

# Variables
variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "market-intel-brain"
}

variable "cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.28"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID for the EKS cluster"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "node_security_group_id" {
  description = "Security group ID for node groups"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# Outputs
output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Endpoint for the EKS cluster"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "Certificate authority data for the EKS cluster"
  value       = module.eks.cluster_certificate_authority_data
}

output "spot_node_groups" {
  description = "Spot instance node groups"
  value       = module.eks.node_groups
}
