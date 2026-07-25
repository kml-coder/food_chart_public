FROM node:20-alpine AS builder

WORKDIR /app

COPY food_app/package*.json /app/
RUN npm ci

COPY food_app /app

# In this compose setup nginx and Flask are separate origins, so the bundle
# needs an absolute backend URL.
ARG EXPO_PUBLIC_API_URL=http://localhost:5050
ENV EXPO_PUBLIC_API_URL=${EXPO_PUBLIC_API_URL}

RUN npx expo export --platform web \
    && if [ -d dist ]; then mv dist /tmp/web; elif [ -d web-build ]; then mv web-build /tmp/web; else echo "No web build output found" && exit 1; fi

FROM nginx:1.27-alpine

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /tmp/web /usr/share/nginx/html

EXPOSE 80
