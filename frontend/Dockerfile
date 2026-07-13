FROM node:20-alpine

WORKDIR /workspace

# Copy dependency specifications and install them
COPY package.json ./
RUN npm install

# Copy application source code
COPY . .

# Expose port 3000
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]
