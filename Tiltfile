print("Dinghy Ping!")
local_resource("lint", ["pipenv", "run", "flake8", "dinghy_ping"])
docker_build('dinghy-ping', '.')
k8s_yaml('deployment_configuration/local.yaml')
k8s_resource('dinghy-ping', port_forwards=8080)