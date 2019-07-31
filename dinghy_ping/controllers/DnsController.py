from kubernetes.client.rest import ApiException
from dinghy_ping.services.DnsService import DnsService
import logging

api = None

class DnsController:
  def __init__(self, api):
    self.dns_service = DnsService()
    global api
    api = api

  @api.route("/form-input-dns-info")
  async def form_input_dns_info(self, req, resp):
      """Form input endpoint for dns info"""
      domain = req.params['domain']
      
      if 'nameserver' in req.params.keys():
          nameserver = req.params['nameserver']
      else:
          nameserver = None 
      
      dns_info_A = self.dns_service._gather_dns_A_info(domain, nameserver)
      dns_info_NS = self.dns_service._gather_dns_NS_info(domain, nameserver)
      dns_info_MX = self.dns_service._gather_dns_MX_info(domain, nameserver)

      resp.content = api.template(
              'dns_info.html',
              domain = domain,
              dns_info_A=dns_info_A,
              dns_info_NS=dns_info_NS,
              dns_info_MX=dns_info_MX
      )
