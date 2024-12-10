
FROM node:20.11.0
WORKDIR /app
COPY package.json /app/package.json
RUN yarn
COPY . /app

EXPOSE 5173
CMD ["yarn", "dev"]

