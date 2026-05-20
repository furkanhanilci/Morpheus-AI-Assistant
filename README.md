# 🤖 Morpheus AI

### The Ultimate Cross-Platform Personal AI Assistant & Operating System Agent — By Furkan Hanilçi

> A real-time voice AI that can hear, see, understand, and control your computer with full autonomy. Engineered for local execution on Windows, macOS, and Linux—zero subscriptions, limitless experience.

---

## ✨ Overview

Morpheus AI bridges the gap between standard chatbots and human intent, acting as a highly advanced Agentic AI empowered at the operating system level. It doesn't just answer your questions; it analyzes your screen during natural conversation, processes complex documents, and dynamically writes, executes, and heals its own Python code to solve novel problems.

With a completely redesigned multi-theme interface and an autonomous execution engine, Morpheus AI is not just an assistant—it is a natural extension of your digital life and workflow.

---

## 🚀 Core Capabilities

Morpheus AI is powered by over twenty integrated tools and a dynamic reasoning engine.

| Feature | Description |
| --- | --- |
| 🎙️ **Real-time Voice** | Ultra-low latency, seamless, and natural bidirectional conversation loop powered by the Gemini Native Audio API. |
| 🖥️ **Full System Control** | Launch applications, adjust system settings (volume, brightness, power), and manage file directories directly. |
| 🧩 **Autonomous Tasks** | Dynamic planning for complex, multi-step goals. The Agentic Loop allows it to work independently until the objective is achieved. |
| 👁️ **Visual Awareness** | Real-time screen and webcam processing; it can read UI elements and perform autonomous GUI manipulations. |
| 🧠 **Persistent Memory** | Deeply learns and remembers your identity, projects, relationships, and preferences using a categorized JSON architecture. |
| ⌨️ **Hybrid Interaction** | Seamlessly transition from voice commands to typed text or hardware-level drag-and-drop file processing (Drop Zone). |

---

## 🆕 What's Inside Morpheus AI? (Technical Deep Dive)

The project's modular and self-governing architecture delivers an unparalleled experience:

### 1. Self-Healing Agentic Executor Engine

* **Dynamic Planning:** Breaks down assigned tasks into actionable steps (`create_plan`). If a step fails, it doesn't give up; it dynamically recalculates an alternative route (`replan`).
* **Autonomous Code Generation:** If the system lacks a pre-defined tool for your request, it will write a custom Python script on the fly, execute it locally, and evaluate the output.
* **Error Handling (Self-Healing):** Should the generated code throw an exception, the system intercepts the error (`error_handler.py`), patches its own code, and safely retries execution.

### 2. Smart & Optimized Memory System

* **Deep Context:** Recognizes you beyond basic info, organizing data into advanced categories like `projects`, `preferences`, `technical_expertise`, and `strategic_perspective`.
* **Auto-Optimization:** When the memory file approaches critical limits (100,000 characters), it safeguards vital data (like identity and active projects) while intelligently purging old, obsolete notes to prevent performance degradation.

### 3. Futuristic, Hardware-Accelerated UI (MorpheusUI)

* **Thread-Safe Architecture:** The asynchronous background AI loop and the PyQt6 frontend communicate securely via signals. The interface never freezes.
* **Live Agent Tracker (Plan View):** Watch the assistant's autonomous thought process in real-time. Track which step is currently running, elapsed time, and success status directly on the HUD.
* **Adaptive Themes:** Switch instantly between "Morpheus" (Cyber/Neon), "Mission Control" (Data-Heavy), and "Minimal" aesthetics to match your workspace.

### 4. Universal Toolset

* **Advanced Web Mastery:** Built on Playwright, it navigates the web, conducts research, fills out forms, and scrapes data autonomously.
* **Daily Life Integrations:** Features dozens of specific actions, from finding flights via Google Flights and parsing local PDFs, to managing game updates on Steam/Epic Games.

---

## ⚡ Quick Start

Follow these steps to get the system running on your local machine:

```bash
# 1. Clone the Repository
git clone https://github.com/furkanhanilci/personal-ai-assistant.git
cd personal-ai-assistant

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Install Browser Engines for Web Automation
playwright install

# 4. Launch the Assistant
python main.py

```

> ⚠️ **Installation Note:** To keep the repository lightweight, some OS-specific dependencies (e.g., `comtypes` or `pywinauto` for Windows) are dynamically handled in `requirements.txt`. If you encounter a `ModuleNotFoundError` during runtime, simply install the missing package via `pip install <module_name>` for your specific OS. Upon first launch, the UI will safely prompt you to input your **Gemini API Key**.

---

## 📋 Requirements

| Requirement | Details |
| --- | --- |
| **OS** | Windows 10/11, macOS, or Linux |
| **Python** | Python 3.10 or higher |
| **Hardware** | An active microphone and speaker for the real-time voice loop |
| **API Key** | A valid Gemini API Key (obtainable via Google AI Studio) |

---

## ⚠️ License

For personal and non-commercial use only.
Licensed under the **[Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)**.

---

## 👤 About the Developer

Engineered by **Furkan Hanilçi** — Autonomous Vehicle Development Engineer & AI Researcher. Built with strict engineering principles to create an AI assistant ecosystem that pushes the limits of real-world functionality.

⭐ **Don't forget to star the repository to support the ongoing journey toward a fully Multi-Agent architecture!**
