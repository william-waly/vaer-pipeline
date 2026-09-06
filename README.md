# Weather Data Pipeline

A Python ETL pipeline that retrieves weather data from the OpenWeatherMap API, transforms and validates the data, and stores it in CSV format.

## Features

* Retrieves weather data for one or more cities
* Data validation and transformation
* Retry logic with exponential backoff
* Error handling and structured logging
* API key stored securely as an environment variable

## Technologies

* Python
* Pandas
* Requests
* OpenWeatherMap API

## Setup

Install dependencies:

```bash
pip install requests pandas
```

Set the API key:

```powershell
$env:OWM_API_KEY = "your-api-key"
```

Run the pipeline:

```bash
python vaer_pipeline.py
```

Multiple cities:

```bash
python vaer_pipeline.py --by "Oslo" "Bergen" "Stavanger" "Trondheim"
```

The collected data is stored in `vaerdata.csv`.
