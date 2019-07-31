import dinghy_ping.models.dinghy_dns as dinghy_dns
import dns.rdatatype

class DnsService:
  # def __init__(self):

  def _gather_dns_A_info(self, domain, nameserver):
      dns_info_A = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.A, nameserver=nameserver)
      return dns_info_A.dns_query()


  def _gather_dns_NS_info(self, domain, nameserver):
      dns_info_NS = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.NS, nameserver=nameserver)
      return dns_info_NS.dns_query()


  def _gather_dns_MX_info(self, domain, nameserver):
      dns_info_MX = dinghy_dns.DinghyDns(domain, rdata_type=dns.rdatatype.MX, nameserver=nameserver)
      return dns_info_MX.dns_query()
    