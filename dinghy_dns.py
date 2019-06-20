import dns.query
import dns.message
import dns.rdataclass
import dns.rdatatype
import logging


class DinghyDns:
    """The Dinghy Ping Dns info interface. Will query the localhost at 127.0.0.1"""
    def __init__(self, domain=None, rdata_type=dns.rdatatype.A, nameserver='127.0.0.1'):
        self.domain = domain
        self.rdata_type = rdata_type
        self.nameserver = nameserver

    def dns_query(self):
        qname = dns.name.from_text(self.domain)
        q = dns.message.make_query(qname, self.rdata_type)
        response = dns.query.udp(q, str(self.nameserver))
        
        return response
