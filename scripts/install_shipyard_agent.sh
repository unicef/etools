#!/bin/bash
AGENT_VERSION=${AGENT_VERSION:-v0.2.5}

# setup agent
curl --silent https://github.com/shipyard/shipyard-agent/releases/download/$AGENT_VERSION/shipyard-agent -L -o /usr/local/bin/shipyard-agent
chmod +x /usr/local/bin/shipyard-agent

KEY=$(/usr/local/bin/shipyard-agent -url $SHIPYARD_URL -register 2>&1 | tail -1 | sed 's/.*Key: //g' | tr -d ' ')

echo "Using key $KEY from Shipyard..."

# setup supervisor
apt-get install -y supervisor

cat << EOF > /etc/supervisor/conf.d/shipyard.conf
[program:shipyard-agent]
directory=/tmp
user=root
command=/usr/local/bin/shipyard-agent
    -url $SHIPYARD_URL
    -key $KEY
    autostart=true
    autorestart=true
EOF

supervisorctl update