locals {
  eks_subnets = {
    a = {
      cidr_block        = "10.42.1.0/24"
      availability_zone = "${var.aws_region}a"
    }
    b = {
      cidr_block        = "10.42.2.0/24"
      availability_zone = "${var.aws_region}b"
    }
  }
}

resource "aws_vpc" "pulsecare" {
  count = var.enable_eks ? 1 : 0

  cidr_block           = var.vpc_cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "pulsecare-dev-vpc"
  }
}

resource "aws_internet_gateway" "pulsecare" {
  count = var.enable_eks ? 1 : 0

  vpc_id = aws_vpc.pulsecare[0].id

  tags = {
    Name = "pulsecare-dev-igw"
  }
}

resource "aws_route_table" "public" {
  count = var.enable_eks ? 1 : 0

  vpc_id = aws_vpc.pulsecare[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.pulsecare[0].id
  }

  tags = {
    Name = "pulsecare-dev-public-rt"
  }
}

resource "aws_subnet" "public" {
  for_each = var.enable_eks ? local.eks_subnets : {}

  vpc_id                  = aws_vpc.pulsecare[0].id
  cidr_block              = each.value.cidr_block
  availability_zone       = each.value.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name                                      = "pulsecare-dev-public-${each.key}"
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/elb"                  = "1"
  }
}

resource "aws_route_table_association" "public" {
  for_each = var.enable_eks ? aws_subnet.public : {}

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public[0].id
}
