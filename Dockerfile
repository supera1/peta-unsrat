FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY css /usr/share/nginx/html/css
COPY js/map.js js/public.js /usr/share/nginx/html/js/
COPY assets/campus.jpg /usr/share/nginx/html/assets/campus.jpg
COPY data/buildings.json data/names.json data/campus.json /usr/share/nginx/html/data/
COPY vendor /usr/share/nginx/html/vendor

EXPOSE 80
