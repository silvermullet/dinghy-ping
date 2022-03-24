resource "kubernetes_service_account" "dinghy_ping" {
  metadata {
    name = local.name
    namespace = "${var.namespace}"
  }

  automount_service_account_token = true
}

resource "kubernetes_cluster_role" "dinghy_ping_cluster_role" {
  metadata {
    name = "${local.name}-pod-reader"
  }

  rule {
    verbs      = ["get", "watch", "list", "log"]
    api_groups = [""]
    resources  = ["pods", "pods/log", "namespaces", "events"]
  }
  rule {
    verbs      = ["get", "watch", "list"]
    api_groups = ["apps", "extensions"]
    resources  = ["deployments", "replicasets"]
  }
}

resource "kubernetes_cluster_role_binding" "dinghy_ping_cluster_role_binding" {
  metadata {
    name = "${local.name}-pod-reader"
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.dinghy_ping.metadata[0].name
    namespace = "${var.namespace}"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.dinghy_ping_cluster_role.metadata[0].name
  }
}
