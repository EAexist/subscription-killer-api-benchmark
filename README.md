# AI Operational Cost Benchmarks

This **Data & Results Branch** presents AI operational cost benchmark results for Subsciption Killer API.

---

## 📊 Executive Summary


## 📈 Visualized Results

### 1. Amortized Cost
This visualization tracks how the average cost per request stabilizes over time. This estimates long-term budget forecasting.

![Total Amortized Cost](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost.png)

---

### 2. Task-Specific Cost Breakdown
This visulizations decompose the total operational cost into each AI-backed tasks.

![Email Categorization Task Costs](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost_categorize_emails.png)
![Email Categorization Task Costs](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost_categorize_emails.png)

---

### 3. Unit Efficiency (Cost per Single Email)
This chart represents the **Cost per Single Email**, providing a normalized view regardless of the size of email list in users' requests.

![Cost per Single Email](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost.png)

---

## 📁 Repository Structure

* `/plots`: Generated `.png` files hosted via GitHub Pages for README embedding.
* `/data`: Raw CSV/JSON trace logs for audit and reproducibility.
* `/scripts`: Data preprocessing and plotting scripts.

---

*Last Updated: 2026-03-13*