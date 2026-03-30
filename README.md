# AI Operational Cost Benchmarks

AI operational cost benchmark results for development versions of Subsciption Killer API.

---

<!-- ## 📊 Executive Summary -->


## Result

### 1. Amortized Cost

Amortized cost of AI operations as the number of requests increases. Decrease by requests implies effect of cache hits. 

![Total Amortized Cost](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost.png)

---

### 2. Task-Specific Cost Breakdown
Decomposition of total operational cost into each AI-backed tasks.

![Email Categorization Task Costs](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost_categorize_emails.png)
![Email Template Extraction Task Costs](https://EAexist.github.io/subscription-killer-api-benchmark/data-storage/results/plots/amortized_ai_cost_extract_email_templates.png)

---

## Repository Structure

* `/plots`: Generated `.png` files hosted via GitHub Pages for README embedding.
* `/data`: Raw CSV/JSON trace logs for audit and reproducibility.
* `/scripts`: Data preprocessing and plotting scripts.

---

*Last Updated: {{ site.time | date: "%Y-%m-%d" }}*