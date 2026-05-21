# Market Sentiment and Real-Time Finanical Intelligence
## Background
Market discussions reveal the public's perception of a company. This project answers the question, "How does current company sentiment drive fluctuations in their price movements?" Contextual data is pulled from Alpha Vantage, and volume data from NewsAPI. Conextual data describes company sentiment over time, while articles provide insight into a company's current public perception. The data is stored across bronze, silver, and gold databases, and is eventually used to power a dashboard to communicate real-time public sentiment about a popular tech company. 
## Tech Stack
- Data Lake: Cloudflare R2
- Data Warehouse: BigQuery
- APIs:
    - [Alpha Vantage](https://www.alphavantage.co/documentation/#news-sentiment)
    - [NewsAPI](https://newsapi.org/docs)
- Scripting Language: Python
- Dashboard:
    - D3.js
    - HTML/JS