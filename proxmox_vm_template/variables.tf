variable "pm_api_url" {
  type        = string
  description = "API URL for the Proxmox server"
}

variable "pm_api_token_id" {
  type        = string
  description = "Token ID for API authentication"
}

variable "pm_api_token_secret" {
  type        = string
  description = "Token secret for API authentication"
}

variable "pm_tls_insecure" {
  type        = bool
  description = "Disable TLS verification for the Proxmox API connection"
  default     = false
}

variable "pm_parallel" {
  type        = number
  description = "Maximum number of parallel connections to the Proxmox server"
  default     = 4
}

variable "pm_timeout" {
  type        = number
  description = "Timeout for Proxmox API calls in seconds"
  default     = 300
}

variable "pm_host" {
  type        = string
  description = "Host target node for the VM"
}

variable "vm_ubuntu_tmpl_name" {
  type        = string
  description = "Name of the Ubuntu template to clone for the VM"
}

variable "vm_onboot" {
  type        = bool
  description = "Whether the VM should start at boot"
}

variable "vm_count" {
  type        = number
  description = "Number of VM instances to create"
  default     = 1
}

variable "vm_qemu_os" {
  type        = string
  description = "QEMU OS identifier"
  default     = "l26"
}

variable "vm_agent" {
  type        = number
  description = "Cloud-init agent flag"
  default     = 1
}

variable "vm_os_type" {
  type        = string
  description = "OS type for the VM"
  default     = "cloud-init"
}

variable "vm_cores" {
  type        = number
  description = "Number of cores per socket for the VM"
}

variable "vm_vcpus" {
  type        = number
  description = "Total number of virtual CPUs for the VM"
}

variable "vm_sockets" {
  type        = number
  description = "Number of CPU sockets for the VM"
}

variable "vm_cpu_type" {
  type        = string
  description = "Type of CPU to use for the VM"
}

variable "vm_memory" {
  type        = number
  description = "Memory allocated to the VM (in MB)"
}

variable "vm_bootdisk" {
  type        = string
  description = "Boot disk identifier"
  default     = "virtio0"
}

variable "vm_scsihw" {
  type        = string
  description = "SCSI hardware type"
  default     = "virtio-scsi-single"
}

variable "vm_hotplug" {
  type        = string
  description = "Components that support hotplug"
  default     = "network,disk,usb,memory,cpu"
}

variable "vm_numa" {
  type        = bool
  description = "Enable NUMA"
  default     = true
}

variable "vm_automatic_reboot" {
  type        = bool
  description = "Automatic reboot flag"
  default     = false
}

variable "vm_description" {
  type        = string
  description = "Description for the VM"
  default     = "This VM is managed by Terraform, cloned from a Cloud-init Ubuntu image, configured with an internal network and supports CPU hotplug/hot unplug and memory hotplug capabilities."
}

variable "vm_tags" {
  type        = string
  description = "Tags for the VM"
  default     = "Persistent_Volume"
}

variable "vm_cloudinit_cdrom_storage" {
  type        = string
  description = "Cloud-init CDROM storage"
  default     = "local-lvm"
}

variable "vm_disk_size" {
  type        = number
  description = "Disk size in GB"
  default     = 100
}

variable "vm_disk_storage" {
  type        = string
  description = "Storage location for the disk"
  default     = "local-lvm"
}

variable "vm_network_model" {
  type        = string
  description = "Network model"
  default     = "virtio"
}

variable "vm_network_bridge" {
  type        = string
  description = "Network bridge"
  default     = "vmbr0"
}

variable "vm_ip_base" {
  type        = string
  description = "Base IP address for the VM"
  default     = "192.168.18.7"
}

variable "vm_gateway" {
  type        = string
  description = "Gateway for the VM"
  default     = "192.168.18.1"
}

variable "vm_user" {
  type        = string
  description = "Default cloud-init user for the VM"
}

variable "ssh_public_keys" {
  type        = string
  description = "Base64 encoded public SSH keys for the VM"
}
