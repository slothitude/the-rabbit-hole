FROM transmission-openvpn-the-guide:latest

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/entries /data/images

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 5001

CMD ["/start.sh"]
