@echo off
set PATH=C:\docker;%PATH%
cd /d C:\docker\transmission-openvpn
echo Building the-rabbit-hole...
docker compose build the-rabbit-hole
echo Starting the-rabbit-hole...
docker compose up -d the-rabbit-hole
echo DONE
