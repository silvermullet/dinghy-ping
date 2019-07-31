from kubernetes.client.rest import ApiException
import logging
import asyncio
import dinghy_ping.models.data as data

api = None

class TcpController:

  def __init__(self, api, redis_host):
    self.redis_host = redis_host
    global api
    api = api

  @api.route("/form-input-tcp-connection-test")
  async def form_input_tcp_connection_test(self, req, resp):
      """Form input endpoint for tcp connection test"""
      logging.basicConfig(level=logging.DEBUG)
      tcp_endpoint = req.params['tcp-endpoint']
      tcp_port = req.params['tcp-port']
      loop = asyncio.get_running_loop()

      try:
          reader, writer = await asyncio.open_connection(host=tcp_endpoint, port=tcp_port)
          connection_info = f'Connection created to {tcp_endpoint} on port {tcp_port}' 
          d = data.DinghyData(self.redis_host,
              domain_response_code=None,
              domain_response_time_ms=None,
              request_url=f'{tcp_endpoint}:{tcp_port}'
          )
          d.save_ping()
          resp.content = api.template(
              'ping_response_tcp_conn.html',
              request=tcp_endpoint,
              port=tcp_port,
              connection_results = connection_info
          )
      except (asyncio.TimeoutError, ConnectionRefusedError):
          print("Network port not responding")
          connection_info = f'Failed to connect to {tcp_endpoint} on port {tcp_port}' 
          resp.status_code = api.status_codes.HTTP_402
          resp.content = api.template(
              'ping_response_tcp_conn.html',
              request=tcp_endpoint,
              port=tcp_port,
              connection_results = connection_info
          )
