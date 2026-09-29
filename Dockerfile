FROM nginx:1.27-alpine

RUN apk add --no-cache python3

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY editor.html /usr/share/nginx/html/editor.html
COPY css /usr/share/nginx/html/css
COPY js/map.js js/public.js js/editor.js /usr/share/nginx/html/js/
COPY assets/campus.jpg assets/logo-unsrat.png /usr/share/nginx/html/assets/
COPY data/buildings.json data/names.json data/campus.json /usr/share/nginx/html/data/
COPY vendor /usr/share/nginx/html/vendor
COPY login.html /opt/peta/login.html
COPY scripts/serve.py /opt/peta/serve.py
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
