"""ETL main file."""

from nltk.sentiment.vader import SentimentIntensityAnalyzer  # type: ignore

print(SentimentIntensityAnalyzer().polarity_scores("This is fantastic news!"))  # type: ignore
