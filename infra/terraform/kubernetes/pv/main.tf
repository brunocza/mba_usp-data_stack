provider "proxmox" {
  pm_api_url          = var.pm_api_url
  pm_api_token_id     = var.pm_api_token_id
  pm_api_token_secret = var.pm_api_token_secret
  pm_tls_insecure     = var.pm_tls_insecure
  pm_parallel         = var.pm_parallel
  pm_timeout          = var.pm_timeout
}

terraform {
  required_version = ">=1.3.3"

  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "3.0.1-rc1"
    }
  }
}



resource "proxmox_vm_qemu" "kube-storage" {
  count = 1

  target_node  = var.pm_host
  clone            = var.vm_ubuntu_tmpl_name
  qemu_os          = "l26"
  name = "kube-storage-0${count.index + 1}"
  agent = 1
  onboot           = var.vm_onboot
  os_type          = "cloud-init"
  cores = 2 ###
  vcpus            = var.vm_vcpus
  sockets          = var.vm_sockets
  cpu              = var.vm_cpu_type

  memory = 3072
  bootdisk         = "virtio0"
  scsihw           = "virtio-scsi-single"
  hotplug          = "network,disk,usb,memory,cpu"
  numa             = true
  automatic_reboot = false
  desc             = "This VM is managed by Terraform, cloned from an Cloud-init Ubuntu image, configured with an internal network and supports CPU hotplug/hot unplug and memory hotplug capabilities."
  tags             = "Pesistent_Volume"
  cloudinit_cdrom_storage    = "toshiba"



  disks {
    virtio {
      virtio0  {
        disk {
          size    = 400
          storage = "toshiba"
        }
      }
    }
  }

  network {
    model  = "virtio"
    bridge = "vmbr0"
  }


  ipconfig0 = "ip=192.168.18.7${count.index + 1}/24,gw=192.168.18.1"
  


  ciuser  = var.vm_user
  sshkeys = base64decode(var.ssh_public_keys)

  lifecycle {
    ignore_changes = [
      "storage"
    ]
  }
}
