variable "src" {
  type = object({
    backend    = string
    config_key = string

    node_group_name = string

    ami_type       = string
    capacity_type  = string
    instance_types = list(string)

    scaling_config = object(
      {
        desired_size = number
        max_size     = number
        min_size     = number
      }
    )
  })
}
