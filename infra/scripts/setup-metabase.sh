#!/bin/bash
docker volume create metabase-data

docker pull metabase/metabase

mkdir -p ~/metabase-data

docker run -d -p 80:3000 \
  -v ~/metabase-data:/metabase-data \
  -e "MB_DB_FILE=/metabase-data/metabase.db" \
  --name metabase metabase/metabase

cat <<EOF > /etc/systemd/system/metabase.service
[Unit]
Description=Metabase service
After=docker.service
Requires=docker.service
[Service]
Restart=always
ExecStart=/usr/bin/docker start -a metabase [-a attach policy]
ExecStop=/usr/bin/docker stop metabase
User=ec2-user
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable metabase.service
systemctl start metabase.service