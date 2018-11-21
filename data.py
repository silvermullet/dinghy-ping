import redis
import json


class DinghyData:
    """The Dinghy Ping Redis data interface, requires https://oss.redislabs.com/rejson/ ReJSON Redis module"""
    def __init__(self, redis_host, domain_response_code=None, domain_response_time_ms=None, request_url=None):
        self.redis_host = redis_host
        self.domain_response_code = domain_response_code 
        self.domain_response_time_ms = domain_response_time_ms
        self.request_url = request_url


    def save_ping(self):
        """Save ping time (ms) and code to request_url object"""
        r = redis.StrictRedis(host=self.redis_host)
        r.execute_command(
            'JSON.SET', 
            f'url:{self.request_url}', 
            '.', 
            json.dumps(
                {
                    "response_time_ms": self.domain_response_time_ms,
                    "response_code": self.domain_response_code
                }
            )
        )


    def get_ping(self):
        """Get ping results for request_url object""" 
        r = redis.StrictRedis(host=self.redis_host)
        try:
            results = json.loads(r.execute_command('JSON.GET', self.request_url))
        except results.ResponseError as err:
            print(f"ResponseError: {err}")
        
        return results


    def get_all_pinged_urls(self):
        """Get all ping results and return in JSON"""
        results = []
        r = redis.StrictRedis(host=self.redis_host)

        try:
            for key in r.scan_iter("url:*"):
                results.append(key.decode('utf-8').strip('url:'))
        except key.ResponseError as err:
            print(f"ResponseError: {err}")
        
        return results