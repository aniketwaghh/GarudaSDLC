FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Expose Vite dev server port
EXPOSE 5173

# Run Vite dev server with host 0.0.0.0 to allow external connections
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
