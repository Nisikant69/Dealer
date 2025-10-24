# 🚗 Dealership AI Backend - Privacy-First Agentic AI System

**Secure, intelligent automation for premium automotive dealerships**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Overview

A comprehensive **Agentic AI system** designed specifically for luxury automotive dealerships handling high-value transactions (₹2 crore - ₹15 crore+ per vehicle). This system prioritizes **data privacy** while providing intelligent automation for:

- 📞 **Voice-based customer interactions** (Vapi integration)
- 🎯 **Intelligent lead scoring and qualification**
- 📄 **Automated document generation** (invoices, quotes)
- 📧 **Smart email automation and follow-ups**
- 📊 **Real-time analytics and insights**
- 🤖 **Multi-agent orchestration**

### 🎯 Key Features

✅ **Privacy-First Architecture** - All customer data stays within your infrastructure  
✅ **Voice AI Agent** - Handle inbound calls with natural conversation  
✅ **Autonomous Lead Management** - Automatic scoring, qualification, and nurturing  
✅ **Intelligent Follow-ups** - Context-aware, personalized communication  
✅ **Document Automation** - Generate invoices, quotes with GST compliance  
✅ **Analytics Dashboard** - Real-time insights into sales pipeline  
✅ **Multi-Channel Support** - Phone, Email, WhatsApp integration ready  

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT INTERACTIONS                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Vapi   │  │   Web    │  │  Email   │  │ WhatsApp │       │
│  │  Calls   │  │   Form   │  │  Inbound │  │  (Future)│       │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘       │
└────────┼─────────────┼─────────────┼─────────────┼─────────────┘
         │             │             │             │
         └─────────────┴─────────────┴─────────────┘
                          │
         ┌────────────────▼────────────────┐
         │       FastAPI Backend           │
         │  ┌──────────────────────────┐   │
         │  │   Voice Agent Handler    │   │
         │  └──────────────────────────┘   │
         │  ┌──────────────────────────┐   │
         │  │  Lead Intelligence Agent │   │
         │  └──────────────────────────┘   │
         │  ┌──────────────────────────┐   │
         │  │ Communication Agent      │   │
         │  └──────────────────────────┘   │
         │  ┌──────────────────────────┐   │
         │  │ Document Generator Agent │   │
         │  └──────────────────────────┘   │
         └─────────────┬───────────────────┘
                       │
         ┌─────────────┴───────────────┐
         │                             │
    ┌────▼────┐              ┌────────▼────────┐
    │PostgreSQL│              │  Redis + Celery │
    │ Database │              │  Task Queue     │
    └──────────┘              └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- ngrok (for Vapi webhooks)
- Vapi account & API key
- SMTP email account

### Installation

```bash
# 1. Clone repository
git clone <your-repo>
cd dealership-ai

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials

# 3. Start services
docker-compose up --build

# 4. Run tests
python test_backend.py

# 5. Access API
open http://localhost:8000/docs
```

**See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed setup instructions.**

---

## 📁 Project Structure

```
dealership-ai/
├── backend/
│   ├── app/
│   │   ├── agents/                    # AI Agent Modules
│   │   │   ├── voice_agent/           # Vapi integration
│   │   │   ├── lead_intelligence_agent/  # Lead scoring
│   │   │   ├── communication_agent/   # Email handler
│   │   │   └── document_agent/        # PDF generation
│   │   ├── api/
│   │   │   └── v1/                    # API endpoints
│   │   │       ├── customers.py
│   │   │       ├── analytics.py
│   │   │       ├── documents.py
│   │   │       ├── voice.py
│   │   │       └── lead_intelligence.py
│   │   ├── models/                    # SQLAlchemy models
│   │   ├── schemas/                   # Pydantic schemas
│   │   ├── workflow/                  # Celery tasks
│   │   └── core/                      # Config, database
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
├── database/
│   └── schema.sql                     # Database schema
├── docker-compose.yml
├── test_backend.py                    # Test suite
└── README.md
```

---

## 🔧 Core Components

### 1. Voice Agent (`voice_agent/`)

**Handles incoming calls via Vapi:**
- Natural language conversation in Indian English/Hindi
- Lead qualification through intelligent questioning
- Automatic transcript capture and analysis
- Seamless handoff to human sales team

**Technologies:** Vapi API, Deepgram transcription

### 2. Lead Intelligence Agent (`lead_intelligence_agent/`)

**Analyzes customer interactions:**
- Rule-based + sentiment analysis
- Lead scoring (Hot/Warm/Cold)
- Intent extraction (test drive, pricing, etc.)
- Engagement scoring
- Vehicle preference detection

**Algorithms:** Keyword matching, sentiment analysis, pattern recognition

### 3. Communication Agent (`communication_agent/`)

**Manages automated communications:**
- SMTP email sending with attachments
- Personalized email templates
- Scheduled follow-up campaigns
- Multi-language support ready

**Technologies:** Python smtplib, Jinja2 templates

### 4. Document Generator Agent (`document_agent/`)

**Creates business documents:**
- GST-compliant invoices
- Custom quotations
- Proforma invoices
- PDF generation with branding

**Technologies:** xhtml2pdf, Jinja2 templates

### 5. Workflow Engine (`workflow/tasks.py`)

**Orchestrates async operations:**
- Lead scoring tasks
- Document generation
- Email sending
- Follow-up scheduling
- Daily nurture campaigns

**Technologies:** Celery, Redis

---

## 📊 API Endpoints

### Customer Management
```http
POST   /api/v1/customers/              # Create customer
GET    /api/v1/customers/              # List customers
GET    /api/v1/customers/{id}          # Get customer
PUT    /api/v1/customers/{id}          # Update customer
POST   /api/v1/customers/{id}/interactions  # Add interaction
GET    /api/v1/customers/{id}/timeline # Customer timeline
```

### Lead Intelligence
```http
POST   /api/v1/leads/score-lead        # Score a lead
GET    /api/v1/analytics/lead-pipeline # View pipeline
POST   /api/v1/customers/{id}/schedule-followup  # Schedule follow-up
```

### Analytics
```http
GET    /api/v1/analytics/dashboard-stats    # Dashboard metrics
GET    /api/v1/analytics/lead-pipeline      # Lead pipeline
GET    /api/v1/analytics/customer-insights/{id}  # Customer insights
GET    /api/v1/analytics/performance-trends # Trends over time
GET    /api/v1/analytics/ai-agent-health    # Agent status
```

### Documents
```http
POST   /api/v1/documents/generate-invoice  # Generate invoice
```

### Voice Agent
```http
POST   /api/v1/voice/webhook           # Vapi webhook (internal)
GET    /api/v1/voice/webhook/health    # Voice agent health
```

**Full API Documentation:** http://localhost:8000/docs

---

## 🧪 Testing

### Run Test Suite
```bash
# Full test suite
python test_backend.py

# Individual tests
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/analytics/dashboard-stats
```

### Test Coverage
- ✅ System health checks
- ✅ Celery worker connectivity
- ✅ Customer CRUD operations
- ✅ Lead scoring accuracy
- ✅ Interaction logging
- ✅ Analytics endpoints
- ✅ Voice webhook simulation
- ✅ Follow-up scheduling

---

## 📈 Monitoring & Logging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Filter by keyword
docker-compose logs backend | grep ERROR
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Voice agent health
curl http://localhost:8000/api/v1/voice/webhook/health

# AI agent status
curl http://localhost:8000/api/v1/analytics/ai-agent-health
```

---

## 🔐 Security & Privacy

### Data Privacy Features
- ✅ All data stored on-premises (PostgreSQL)
- ✅ No external API calls for core LLM (Vapi uses their infrastructure only for voice transport)
- ✅ Encrypted local storage
- ✅ Configurable data retention policies
- ✅ Access control ready (add authentication layer)
- ✅ Audit logging for compliance

### Security Best Practices
- Use environment variables for secrets
- Enable HTTPS in production
- Implement rate limiting
- Regular security audits
- Database encryption at rest
- Secure Redis with password

---

## 🛠️ Configuration

### Environment Variables (`backend/.env`)

```env
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Vapi
VAPI_API_KEY=your-vapi-key
VAPI_ASSISTANT_ID=your-assistant-id
```

---

## 📦 Deployment

### Production Checklist
- [ ] Change all default passwords
- [ ] Configure HTTPS/SSL
- [ ] Set up database backups
- [ ] Enable monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation (ELK Stack)
- [ ] Set up error tracking (Sentry)
- [ ] Implement rate limiting
- [ ] Configure firewall rules
- [ ] Set up CI/CD pipeline
- [ ] Document runbooks for operations

### Scaling Considerations
- Add more Celery workers for high load
- Enable PostgreSQL replication
- Implement caching layer (Redis)
- Use load balancer for multiple backend instances
- CDN for static assets
- Database connection pooling

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🆘 Support

- **Documentation:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **API Docs:** http://localhost:8000/docs
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **Vapi** - Voice AI infrastructure
- **Celery** - Distributed task queue
- **PostgreSQL** - Robust database
- **Docker** - Containerization platform

---

## 🗺️ Roadmap

### Phase 1: Core Features (Completed ✅)
- [x] Voice agent integration
- [x] Lead scoring system
- [x] Document generation
- [x] Email automation
- [x] Analytics dashboard

### Phase 2: Enhanced Intelligence (In Progress)
- [ ] WhatsApp Business API integration
- [ ] Advanced NLP for sentiment analysis
- [ ] Predictive analytics for purchase probability
- [ ] Multi-language support (Hindi, regional languages)
- [ ] Custom LLM fine-tuning for automotive domain

### Phase 3: Advanced Features (Planned)
- [ ] Frontend dashboard (React)
- [ ] Mobile app for sales team
- [ ] CRM integration (Salesforce, HubSpot)
- [ ] Video call capability
- [ ] Blockchain for transaction verification

---
