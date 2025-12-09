# AutoTrading System

A comprehensive cryptocurrency trading system with real-time market data, automated trading strategies, and web-based monitoring dashboard.

## 🏗️ Architecture

- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + Python
- **Trading Bot**: Python + CCXT + Real-time WebSocket
- **Database**: PostgreSQL
- **Cache**: Redis
- **Monitoring**: Prometheus + Grafana
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone and Setup

```bash
git clone https://github.com/EricT1230/AutoTrading.git
cd AutoTrading
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual API credentials
nano .env
```

### 3. Start All Services

```bash
docker-compose up -d
```

### 4. Verify Services

```bash
./scripts/health-check.sh
```

## 🌐 Service URLs

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **Web UI Dashboard**: http://localhost:8501
- **Grafana Monitoring**: http://localhost:3000 (admin/admin)
- **Prometheus Metrics**: http://localhost:9090

## 📊 Features

### Trading Features
- Real-time market data from OKX
- ICT New York Session FVG strategy
- Risk management and position sizing
- Order execution and monitoring
- P&L tracking

### Monitoring & Analytics
- Real-time candlestick charts
- Performance metrics dashboard
- Trade history and analytics
- System health monitoring
- Grafana dashboards

### Technology Stack
- Microservices architecture
- WebSocket real-time updates
- RESTful API design
- Containerized deployment
- Automated testing and deployment

## 🔧 Development

### Local Development Setup

1. **Frontend Development**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. **Backend Development**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

3. **Trading Bot Development**:
   ```bash
   cd trading-bot
   pip install -r requirements.txt
   python start.py
   ```

### Running Tests

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && pytest

# Trading bot tests
cd trading-bot && python scripts/test_setup.py
```

### Code Quality

```bash
# Frontend linting
cd frontend && npm run lint

# Backend linting
cd backend && flake8 . && black --check .

# Trading bot linting
cd trading-bot && flake8 . && black --check .
```

## 🚢 Deployment

### Production Deployment

1. **Setup Environment Variables**:
   ```bash
   # Set these in your GitHub repository secrets:
   - DOCKER_USERNAME
   - DOCKER_PASSWORD
   - API_KEY
   - API_SECRET
   - API_PASSPHRASE
   ```

2. **Deploy via GitHub Actions**:
   - Push to main branch
   - GitHub Actions will automatically build and deploy

3. **Manual Deployment**:
   ```bash
   ./scripts/deploy.sh
   ```

### Environment Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `API_KEY` | OKX API Key | Yes |
| `API_SECRET` | OKX API Secret | Yes |
| `API_PASSPHRASE` | OKX API Passphrase | Yes |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram notifications | No |
| `GRAFANA_PASSWORD` | Grafana admin password | No |

## 📈 Monitoring

### Grafana Dashboards

1. **Trading Performance Dashboard**:
   - Real-time P&L
   - Trade history
   - Strategy performance

2. **System Monitoring Dashboard**:
   - Service health
   - Resource usage
   - Error rates

3. **Market Data Dashboard**:
   - Real-time charts
   - Volume analysis
   - Market indicators

### Prometheus Metrics

- API response times
- Trade execution metrics
- System resource usage
- Database performance

## 🔒 Security

- Environment-based configuration
- API key management via secrets
- Docker security best practices
- Regular security scanning with Trivy

## 📝 API Documentation

API documentation is available at:
- **Development**: http://localhost:8000/docs
- **Production**: Your domain/docs

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   docker-compose logs [service-name]
   ./scripts/health-check.sh
   ```

2. **Database connection issues**:
   ```bash
   docker-compose restart postgres
   ```

3. **Trading bot not connecting**:
   - Check API credentials in .env
   - Verify OKX API permissions

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f trading-bot
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. Please trade responsibly and never risk more than you can afford to lose.