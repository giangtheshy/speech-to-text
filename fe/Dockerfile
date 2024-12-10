
FROM node:20.11.0
# Set the working directory
WORKDIR /app

# Copy package.json and yarn.lock for dependency installation
COPY package.json yarn.lock ./

# Install dependencies
RUN yarn install

# Copy the rest of the application code
COPY . .

# Expose the port that Vite runs on
EXPOSE 5173

# Set the command to run the development server
CMD ["yarn", "dev", "--host"]