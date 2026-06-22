resource "aws_eks_access_entry" "app_deploy_codebuild" {
  cluster_name  = var.eks_cluster_name
  principal_arn = aws_iam_role.app_deploy_codebuild.arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "app_deploy_codebuild_admin" {
  cluster_name  = var.eks_cluster_name
  principal_arn = aws_iam_role.app_deploy_codebuild.arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }

  depends_on = [
    aws_eks_access_entry.app_deploy_codebuild
  ]
}
