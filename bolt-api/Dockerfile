FROM node:19-buster
WORKDIR /app

RUN npm init -y && \
    npm install --save-dev typescript ts-node @types/node @types/express && \
    npm install express knex

COPY tsconfig.json ./

# Copy the rest of the app files to the working directory
COPY src ./src

# Expose port 3000
EXPOSE 3000
