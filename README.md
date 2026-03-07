# 🌾 KrishiVanX Agent
**Smart Productivity Agent for Indian Agriculture**

*Built for AgentathonX 2026 - AI for Social Impact.*

## 🚀 Overview
KrishiVanX is a **Context-Aware Agricultural AI Agent** designed to help farmers make data-driven decisions. Moving beyond standard AI chatbots, the KrishiVanX Agent autonomously retrieves real-time satellite weather data and local government policies to generate highly specific, actionable plans tailored to the farmer's exact environment.

## 🧠 Agentic Features & Capabilities
* **Real-Time Context Injection (Tool Use):** The agent automatically fetches live weather metrics (temperature, humidity, rainfall, wind speed) via the Open-Meteo API based on the user's selected location before generating advice.
* **Policy Awareness:** Cross-references the user's location with a database of active state agricultural subsidies (e.g., UP Krishi Yantra Yojana, Maha-DBT) to recommend financial aid dynamically.
* **Visual Diagnostics:** Analyzes uploaded crop images to detect diseases and recommends organic/chemical remedies *based on current weather conditions*.
* **Multilingual Voice Interface:** Farmers can speak their queries in over 20 regional Indian languages, making the tool accessible to rural demographics.
* **Cloud Memory:** Automatically logs reports, images, and interaction history to an Azure Cosmos DB backend for persistent record-keeping.

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **AI/LLM Engine:** OpenAI (GPT-4o) via GitHub/Azure AI Models
* **Database:** Azure Cosmos DB
* **External Tools/APIs:** Open-Meteo API (Weather retrieval), SpeechRecognition (Audio input), gTTS (Text-to-Speech)

## 💻 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/ASbhay24/KrishivanX_2.0.git](https://github.com/ASbhay24/KrishivanX_2.0.git)
   cd KrishivanX_2.0
