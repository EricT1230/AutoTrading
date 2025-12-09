#!/bin/bash

# AutoTrading CI/CD Setup Script

echo "🚀 Setting up AutoTrading CI/CD Environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your actual credentials!"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs data config monitoring/grafana/dashboards monitoring/grafana/datasources

# Create monitoring configuration
echo "📊 Setting up monitoring configuration..."
cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'autotrading-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  - job_name: 'autotrading-bot'
    static_configs:
      - targets: ['trading-bot:8080']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
EOF

# Create Grafana datasource configuration
cat > monitoring/grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Create database initialization script
cat > scripts/init.sql << 'EOF'
-- Create database tables for AutoTrading

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    amount DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open_price DECIMAL(20, 8) NOT NULL,
    high_price DECIMAL(20, 8) NOT NULL,
    low_price DECIMAL(20, 8) NOT NULL,
    close_price DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    parameters JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe_timestamp ON market_data(symbol, timeframe, timestamp);
CREATE INDEX IF NOT EXISTS idx_strategies_active ON strategies(is_active);
EOF

# Create health check script
cat > scripts/health-check.sh << 'EOF'
#!/bin/bash

# Health check script for all services

echo "🏥 Checking service health..."

services=("frontend:80" "backend:8000" "web-ui:8501" "grafana:3000" "prometheus:9090")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -f "http://localhost:$port/health" &> /dev/null || curl -f "http://localhost:$port" &> /dev/null; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is not responding"
    fi
done
EOF

chmod +x scripts/health-check.sh

# Create deployment script
cat > scripts/deploy.sh << 'EOF'
#!/bin/bash

# Deployment script

echo "🚀 Starting deployment..."

# Pull latest changes
git pull origin main

# Build and start services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Run health check
./scripts/health-check.sh

echo "✅ Deployment completed!"
EOF

chmod +x scripts/deploy.sh

echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Update .env file with your credentials"
echo "2. Run: docker-compose up -d"
echo "3. Check services: ./scripts/health-check.sh"
echo ""
echo "🌐 Service URLs:"
echo "- Frontend: http://localhost"
echo "- Backend API: http://localhost:8000"
echo "- Web UI: http://localhost:8501"
echo "- Grafana: http://localhost:3000 (admin/admin)"
echo "- Prometheus: http://localhost:9090"