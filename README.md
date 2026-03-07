# GarudaSDLC

**GarudaSDLC: AI employees that turn client meetings into shipped software** 🦅🛠️🤖

Service companies: Submit a Meet link → Get Jira tickets, knowledge graphs, impact analysis, and deployments. Developers stay in control, AI does the grunt work.

## 🚀 What GarudaSDLC does

```
Client Meeting → Garuda Bot Records → Knowledge Graph → AI Proposes Jira Tickets → 
Dev Approves → Garuda Agents Code → Test → Deploy
```

- Silent **Garuda bot** joins meetings, extracts transcripts + screen shares
- Builds searchable project memory per client/workspace  
- **Garuda AI "employees"** draft tickets, analyze impact, document code
- Agents collaborate on Slack, humans approve everything
- Full traceability: every decision links back to video timestamp

## 🎯 For service companies

| Without GarudaSDLC | With GarudaSDLC |
|---|---|
| Meeting notes scattered | Living knowledge graph |
| Manual Jira tickets | AI drafts → you approve |
| Priority changes = cleanup hell | Auto impact analysis |
| "What did client say?" | Searchable + video proof |

## 🏗️ GarudaSDLC Architecture

```
Meet Webhook → S3 Storage → Gemini Transcription → 
Vector Store (Pinecone) → Garuda Agentic Workflows → Jira/GitHub APIs
                ↓
Slack Forum (AI coordination) ← Garuda Dashboard (approvals)
```

## ⚡ Quick Start

```bash
git clone https://github.com/aniketwagh/garuda-sdlc
cd garuda-sdlc
docker-compose up
```

**Your story starts here** – Create your first workspace and submit a meeting link through the intuitive UI. Watch GarudaSDLC transform conversations into actionable project insights!

## 📦 Deploy to AWS (1-click)

```bash
make deploy
```

ECS + Fargate + ALB. HIPAA-ready storage.

## 🌟 Why GitHub loves GarudaSDLC

- **Real AI agents** talking on Slack (watch Garuda agents coordinate!)
- **Production-ready** ECS deployment 
- **Zero-config** Meet integration
- **Battle-tested** on enterprise clients

## 🤝 Join 50+ service teams

> "GarudaSDLC cut requirement gathering from 2 days to 2 hours" – ServiceCo

## 🚀 GarudaSDLC Roadmap

- [x] Meeting → Knowledge Graph  
- [x] AI Jira drafts + Garuda Slack agents
- [ ] GitHub codegen agents
- [ ] Multi-meeting RAG search
- [ ] Enterprise SSO

## 👥 Garuda Community

- 💬 [Garuda Slack agents channel](https://join.slack.com/...)
- 🐛 Issues welcomed!
- 🌍 [Garuda Demo video](https://youtu.be/...)

## ⚖️ License

MIT – Fork, deploy, make $$ 💰

***

⭐ **Star if you want GarudaSDLC to ship your software**  
🔔 **Watch for Garuda agent updates**



```
Made by @aniketwagh – Building the future of service delivery with GarudaSDLC 🦅
```