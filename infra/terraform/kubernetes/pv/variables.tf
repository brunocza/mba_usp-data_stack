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

# Restante das variáveis para configurar os recursos da VM
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

variable "vm_vcpus" {
  type        = number
  description = "Number of virtual CPUs for the VM"
}

variable "vm_sockets" {
  type        = number
  description = "Number of CPU sockets for the VM"
}

variable "vm_cpu_type" {
  type        = string
  description = "Type of CPU to use for the VM"
}

variable "vm_user" {
  type        = string
  description = "Default cloud-init user for the VM"
}

variable "ssh_public_keys" {
  type        = string
  description = "Base64 encoded public SSH keys for the VM"
}
