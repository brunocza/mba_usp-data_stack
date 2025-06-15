provider "proxmox" {
  pm_api_url          = var.pm_api_url
  pm_api_token_id     = var.pm_api_token_id
  pm_api_token_secret = var.pm_api_token_secret
  pm_tls_insecure     = var.pm_tls_insecure
  pm_parallel         = var.pm_parallel
  pm_timeout          = var.pm_timeout
}

terraform {
  required_version = ">= 1.3.3"

  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "3.0.1-rc1"
    }
  }
}

resource "proxmox_vm_qemu" "K3S-TCC" {
  count       = var.vm_count
  target_node = var.pm_host
  clone       = var.vm_ubuntu_tmpl_name
  qemu_os     = var.vm_qemu_os
  name        = "K3S-TCC"
  agent       = var.vm_agent
  onboot      = var.vm_onboot
  os_type     = var.vm_os_type

  cores   = var.vm_cores
  vcpus   = var.vm_vcpus
  sockets = var.vm_sockets
  cpu     = var.vm_cpu_type

  memory      = var.vm_memory
  bootdisk    = var.vm_bootdisk
  scsihw      = var.vm_scsihw
  hotplug     = var.vm_hotplug
  numa        = var.vm_numa
  automatic_reboot = var.vm_automatic_reboot
  desc        = var.vm_description
  tags        = var.vm_tags
  cloudinit_cdrom_storage = var.vm_cloudinit_cdrom_storage

  disks {
    virtio {
      virtio0 {
        disk {
          size    = var.vm_disk_size
          storage = var.vm_disk_storage
        }
      }
    }
  }

  network {
    model  = var.vm_network_model
    bridge = var.vm_network_bridge
  }

  # Configuração de rede (IP fixo)
  ipconfig0 = "ip=${var.vm_ip_base}/24,gw=${var.vm_gateway}"
  
  ciuser  = var.vm_user
  sshkeys = base64decode(var.ssh_public_keys)

  # Conexão para provisionamento via SSH
  connection {
    type        = "ssh"
    host        = var.vm_ip_base
    user        = var.vm_user
    private_key = file("~/proxmox-kubernetes/ssh-keys/id_rsa")  # Ajuste o caminho se necessário
  }

  # Provisioner para instalar Docker e Docker Compose,
  # habilitar o serviço e adicionar o usuário ao grupo docker.
  # OBS.: Não executa 'apt-get update'.
  provisioner "remote-exec" {
    inline = [
      "sudo apt-get update",
      "sudo apt-get install -y docker.io docker-compose",
      "sudo systemctl enable docker",
      "sudo systemctl start docker",
      "sudo usermod -aG docker ubuntu"
    ]
  }

  lifecycle {
    ignore_changes = [
      # storage
    ]
  }
}
