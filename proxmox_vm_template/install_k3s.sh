# 1) Atualizar sistema
apt update && apt -y full-upgrade

# 2) Desabilitar swap (requisito Kubernetes)
swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

# 3) Ajustar parâmetros de rede recomendados
cat <<'SYSCTL' >/etc/sysctl.d/98-k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
SYSCTL
sysctl --system

# 4) Instalar K3s (atual estável v1.32.6+k3s1)
curl -sfL https://get.k3s.io \
  | INSTALL_K3S_EXEC="--write-kubeconfig-mode 644" \
  sh -

# 5) Verificar status
systemctl status k3s --no-pager -l      # deve aparecer 'active (running)'

# 6) Validar nó e pods
k3s kubectl get nodes -o wide
k3s kubectl get pods -A

# 7) (Opcional) Usar kubectl padrão
ln -s /usr/local/bin/k3s /usr/local/bin/kubectl
