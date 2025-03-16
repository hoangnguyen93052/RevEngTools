import requests
import json
from bs4 import BeautifulSoup
import pandas as pd
from transformers import GPT2Tokenizer, GPT2LMHeadModel
from nltk.sentiment import SentimentIntensityAnalyzer
import logging
from datetime import datetime
import nltk

nltk.download('vader_lexicon')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsScraper:
    def __init__(self, sources):
        self.sources = sources

    def fetch_articles(self):
        all_articles = []
        for source in self.sources:
            response = requests.get(source)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                articles = soup.find_all('article')
                for article in articles:
                    title = article.find('h2').text
                    link = article.find('a')['href']
                    all_articles.append({'title': title, 'link': link})
            else:
                logging.error(f"Failed to fetch articles from {source} with status code {response.status_code}")
        return all_articles

class ArticleGenerator:
    def __init__(self, model_name='gpt2'):
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name)

    def generate_article(self, prompt, max_length=200):
        inputs = self.tokenizer.encode(prompt, return_tensors='pt')
        outputs = self.model.generate(inputs, max_length=max_length, num_return_sequences=1)
        article = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return article

class SentimentAnalyzer:
    def __init__(self):
        self.sia = SentimentIntensityAnalyzer()

    def analyze_sentiment(self, text):
        sentiment = self.sia.polarity_scores(text)
        return sentiment

class JournalismApp:
    def __init__(self):
        self.scraper = NewsScraper([
            'https://www.bbc.com/news',
            'https://www.cnn.com',
            'https://www.reuters.com'
        ])
        self.generator = ArticleGenerator()
        self.analyzer = SentimentAnalyzer()
    
    def run(self):
        logging.info("Starting Journalism Application")
        articles = self.scraper.fetch_articles()
        
        if not articles:
            logging.warning("No articles found.")
            return
        
        article_data = []
        
        for article in articles:
            title = article['title']
            logging.info(f"Generating article for title: {title}")
            generated_article = self.generator.generate_article(title)
            sentiment = self.analyzer.analyze_sentiment(generated_article)
            article_data.append({
                'title': title,
                'generated_article': generated_article,
                'sentiment': sentiment
            })

        self.save_to_csv(article_data)
        logging.info("Articles have been generated and saved.")
    
    def save_to_csv(self, data):
        df = pd.DataFrame(data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"generated_articles_{timestamp}.csv"
        df.to_csv(file_name, index=False)
        logging.info(f"Saved the articles to {file_name}")

if __name__ == '__main__':
    app = JournalismApp()
    app.run()