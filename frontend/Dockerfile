FROM nginx:1.27-alpine

RUN rm -rf /usr/share/nginx/html/*
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY public/ /usr/share/nginx/html/

RUN chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]