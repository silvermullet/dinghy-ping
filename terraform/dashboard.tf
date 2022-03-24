locals {
    unique_name = replace("Dinghy-ping ${var.cluster_fqdn}%{ if terraform.workspace != "default" }-${terraform.workspace}%{ endif }", "_", "-")
}


resource "datadog_dashboard" "dinghy_ping_dashboard" {
  title         = local.unique_name
  description   = "Dinghy-Ping dashboard"
  layout_type   = "ordered"
  is_read_only  = false


// add widgets below

  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_home_page_load_time.timer.avg{*}"
        display_type = "line"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "Home Page Load Time"
      show_legend = false
    }
  }
  widget {
    query_value_definition {
      request {
        q = "sum:dinghy_ping_events_home_page_load_time.timer.count{*}.as_count()"
        aggregator = "sum"
      }

      title = "Total Landing Page Loads"
    }     
  } 
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_display_pod_logs.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "Pod Log Requests"
      show_legend = false
    }      
  }
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_render_deployment_details.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "Deployment Details Requests"
      show_legend = false
    }      
  } 
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_render_dns_response.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "DNS Resolution Request"
      show_legend = false
    }      
  }   
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_render_pod_description.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }
      
      title = "Pod Description Requests"
      show_legend = false
    }      
  }
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_render_pod_details.timer.count{*}.as_count()"
        display_type = "bars" 
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "Pod Details Requests"
      show_legend = false
      
    }     
  }
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_render_tcp_response.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "TCP Connection Requests"
      show_legend = false
    }      
  } 
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_events_web_socket_duration.timer.count{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "WebSocket Connection Requests"
      show_legend = false
    }      
  }   
  widget {
    timeseries_definition {
      request {
        q = "avg:dinghy_ping_http_connection_check.increment{*}.as_count()"
        display_type = "bars"
        style {
          palette = "dog_classic"
          line_type = "solid"
          line_width = "normal"
        }
      }

      title = "HTTP Connection Requests"
      show_legend = false
    }      
  }  
  template_variable {
    name   = "env"
    prefix = "env"
    default = "*"
  }
}

output "dashboard_url" {
  value = datadog_dashboard.dinghy_ping_dashboard.url
}
