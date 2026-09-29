FROM python:3.12-alpine

WORKDIR /app
ENV SERVE_BIND=0.0.0.0
ENV SERVE_PORT=80
ENV PYTHONDONTWRITEBYTECODE=1

COPY index.html editor.html login.html /app/
COPY css /app/css
COPY js/map.js js/public.js js/editor.js /app/js/
COPY assets/campus.jpg assets/logo-unsrat.png /app/assets/
COPY data/buildings.json data/names.json data/campus.json /app/data/
COPY vendor /app/vendor
COPY scripts/serve.py /app/scripts/serve.py

EXPOSE 80
CMD ["python3", "/app/scripts/serve.py"]
