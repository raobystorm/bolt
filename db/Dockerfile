FROM mysql:8

ENV MYSQL_ROOT_PASSWORD=bolt_2023K3D4A
ENV MYSQL_DATABASE=bolt_db
ENV MYSQL_USER=bolt_user
ENV MYSQL_PASSWORD=bolt_passK3D4

COPY init.sql /docker-entrypoint-initdb.d/
