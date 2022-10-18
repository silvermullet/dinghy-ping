#!/bin/bash

# install grpcurl
mkdir -p /root/bin/grpcurl
wget https://github.com/fullstorydev/grpcurl/releases/download/v1.8.1/grpcurl_1.8.1_linux_x86_64.tar.gz
tar -xvf grpcurl_1.8.1_linux_x86_64.tar.gz --directory /root/bin/grpcurl
chmod +x /root/bin/grpcurl/grpcurl
