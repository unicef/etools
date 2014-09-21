server {
  listen      [::]:80;
  listen      80;
  server_name ${SERVER_NAME};
  location    / {
    client_max_body_size 10M;
    proxy_pass  http://${APP};
    proxy_connect_timeout 1200s;
    proxy_read_timeout 1200s;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Request-Start $msec;
  }
}