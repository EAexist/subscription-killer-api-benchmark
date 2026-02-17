<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/EAexist/subscription-killer-api">

[//]: # (    <img src="images/logo.png" alt="Logo" width="80" height="80">)
  </a>

<h3 align="center">Subscription Killer API Benchmark</h3>

  <p align="center">
    Performance benchmarking suite for Subscription Killer API
    <br />
    <br />
    <a href="https://github.com/EAexist/subscription-killer-api" target="_blank" rel="noopener noreferrer">Main Project</a>
  </p>
</div>

<!-- BENCHMARK_RESULTS -->
<!-- BENCHMARK_RESULTS_START -->
## 📊 Latest AI Cost Benchmark

### AI Token Usage and Cost

| Metric | benchmark-test-b6f280ec |
|--------|--------|
| AI Cost | $0.317 / 1K requests |
| Input Token Count | 472 tokens |
| Output Token Count | 27 tokens |
| Total Tokens | 499 tokens |

*Model: gemini-3-flash-preview. Input Token Price: $0.50 / million. Output Token Price: $3.00 / million.

### Supplementary Performance Indicators

*Indicative metrics based on limited test iterations for development insights.*

| Metric | benchmark-test-b6f280ec |
|--------|--------|
| Indicative Latency | 3.27 s |
| Gmail API Critical I/O | 1.63 s |
| AI Critical I/O | 1.18 s |
| Total Critical I/O | 2.52 s |
| Orchestration Overhead | 0.75 s |

---
*AI Cost Benchmark: 1 test iteration(s) per commit after 0 warmup exclusion.*
<!-- BENCHMARK_RESULTS_END -->


<!-- ABOUT THE PROJECT -->
## About The Project

This is the official benchmarking suite for the Subscription Killer API project.

* **AI Cost Benchmarking**
  
  Measures and analyzes AI token usage and costs across different API configurations and commits.

* **Indicative Performance Metrics Tracking**
  
  Tracks latency, critical I/O operations, and system performance indicators over time.

* **Automated Testing**
  
  Integrates with CI/CD pipelines to automatically run benchmarks and detect performance regressions.

* **Future-Ready Architecture**
  
  Designed to support additional benchmark types including precise performance measurements and load testing.


### Built With

* [![Java][Java]][Java-url]
* [![Python][Python]][Python-url]
* [![k6][k6]][k6-url]

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

- Java 17+
- Maven 3.6+
- Python 3.8+
- Docker

### Running Benchmarks

```bash
# Run AI Cost Benchmark
./run-ai-benchmark.sh
```

### Configuration

Copy `.env.example` to `.env` and configure:
- AI model pricing
- Benchmark parameters
- Docker settings

<!-- LICENSE -->
## License

Copyright (c) 2026 PyoHyeon. All rights reserved.

No permission is granted for commercial use, distribution, or modification without explicit consent.


<!-- CONTACT -->
## Contact

Pyohyeon: hyeon.expression@gmail.com

Project Link: [https://github.com/EAexist/subscription-killer-api](https://github.com/EAexist/subscription-killer-api)

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [Testcontainers](https://testcontainers.org/)
* [Best-README-Template](https://github.com/EAexist/Best-README-Template)
<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[Java]: https://img.shields.io/badge/Java-%23ED8B00.svg?logo=openjdk&logoColor=white
[Java-url]: https://www.java.com/
[Python]: https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff
[Python-url]: https://python.org
[k6]: https://img.shields.io/badge/k6-6364FF?logo=k6&logoColor=fff
[k6-url]: https://k6.io/
