# Justin's Financial Analysis Portfolio

# Background
There are five projects in this portfolio. Each project demonstrates my grasp of full data science lifecycle, from data acquisition and engineering to analysis and visualization. Each project has a different deliverable. The project descriptions are below.

# Project Summaries
1. Market Sentiment and Real-Time Financial Intelligence
## Background
Using company stock market tickers, I assess the volume and context of their market discussions through a combination of structured and unstructured data. This project answers the question, "How does current company sentiment drive fluctuations price movements?" Contextual data is pulled from Alpha Vantage, and volume data from NewsAPI. The structured data from Alpha Vantage describes company sentiment over time, while the unstructured article data from NewsAPI provides a current glance at a company's public perception. This data is cleaned and processed into a dashboard to explain why your favorite ticker(s) are just not getting the job done, or making you jump for joy. Turns out, daily articles explain a lot. 
### Tech Stack
- Data Lake: Cloudflare R2
- Data Warehouse: BigQuery
- APIs:
    - [https://www.alphavantage.co/documentation/#news-sentiment](Alpha Vantage)
    - [https://newsapi.org/docs](NewsAPI)
- Scripting Language: Python
- Dashboard:
    - D3.js
    - HTML/JS