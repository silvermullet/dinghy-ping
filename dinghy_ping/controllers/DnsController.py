from kubernetes.client.rest import ApiException
import dinghy_ping.models.dinghy_dns as dinghy_dns
import dns.rdatatype
import logging

api = None


def _gather_dns_A_info(domain, nameserver):
    dns_info_A = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.A, nameserver=nameserver)
    return dns_info_A.dns_query()


def _gather_dns_NS_info(domain, nameserver):
    dns_info_NS = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.NS, nameserver=nameserver)
    return dns_info_NS.dns_query()


def _gather_dns_MX_info(domain, nameserver):
    dns_info_MX = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.MX, nameserver=nameserver)
    return dns_info_MX.dns_query()

class DnsController:
  def __init__(self, api, k8s_client):
    self.k8s_client = k8s_client
    global api
    self.api = api
    api = api
# 
  @api.route("/form-input-dns-info")
  async def form_input_dns_info(self, req, resp):
      """Form input endpoint for dns info"""
      domain = req.params['domain']
      
      if 'nameserver' in req.params.keys():
          nameserver = req.params['nameserver']
      else:
          nameserver = None 
      
      dns_info_A=_gather_dns_A_info(domain, nameserver)
      dns_info_NS=_gather_dns_NS_info(domain, nameserver)
      dns_info_MX=_gather_dns_MX_info(domain, nameserver)

      resp.content = api.template(
              'dns_info.html',
              domain = domain,
              dns_info_A=dns_info_A,
              dns_info_NS=dns_info_NS,
              dns_info_MX=dns_info_MX
      )
