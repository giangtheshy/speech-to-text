
FROM node:20.11.0
# Set the working directory
WORKDIR /app

# Copy package.json and yarn.lock for dependency installation
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install

# Copy the rest of the application code
COPY . .

RUN NODE_OPTIONS="--max-old-space-size=8192 " yarn build
# EXPOSE 4500
# CMD ["npm ", "start"]


# production stage
# FROM nginx:1.17 as nginx
FROM nginx:1.17-alpine as nginx
EXPOSE 5173
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY --from=build-stage /app/.env /usr/share/nginx/html/.env
COPY ./default.conf /etc/nginx/conf.d/default.conf
