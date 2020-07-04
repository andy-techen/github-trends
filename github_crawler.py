# -*- coding: utf-8 -*- 
#%%
import json
import requests
import numpy as np
import pandas as pd
from pandas import json_normalize
import os
from datetime import datetime
from tweepy import API, OAuthHandler
import string
import pybase64
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer
nltk.download('stopwords')
nltk.download('punkt')

# tokens
t_consumer_key = "C4dNIgkl43788sKKZ7iNZZy3w"
t_consumer_secret = "QBfEpERH8d6IdVCPBs4SQaLWfiXgG2b3KRGIV8QrJrBUNJWF2k"
t_access_token = "712293623665045505-c2NWLT2AQqLVRRS8jcRKxyyHsQ1kpG6"
t_access_secret = "o82dQvo1DEL2q4Cnp9EehhxsWUW8hs0huV5KwL2tX3dAs"
g_access_token = "f6522f9ba517814474c80da6312ecb3347e341ec"

# base variables
keywords_ls = ["vpn", "anonymous browsing", "online tracking", "online surveillance"]
base_api = "https://api.github.com/search/repositories?q="
token_header = {'Authorization': 'token ' + g_access_token}

# keyword extraction
stop = stopwords.words("english") + list(string.punctuation)
update_stop = ['rt', 'com', 'could']
stop.extend(update_stop)
cv = CountVectorizer(ngram_range=(1,2))
transformer = TfidfTransformer()

# twitter auth
auth = OAuthHandler(t_consumer_key, t_consumer_secret)
auth.set_access_token(t_access_token, t_access_secret)
api = API(auth)

# utility functions
def get_keywords(df):
    content_ls = []
    for c in df:
        text_ls = word_tokenize(c)
        text_ls = [txt.lower() for txt in text_ls if txt.lower() not in stop]
        content_ls.append(' '.join(text_ls))
    
    content_vector = cv.fit_transform(content_ls)
    values = transformer.fit_transform(content_vector).todense()
    features = cv.get_feature_names()
    return pd.DataFrame(values, columns=features)

def get_twitter_query(keywords=keywords_ls):
    keywords_str = '"' + '" OR "'.join(keywords) + '"'
    results = api.search(keywords_str, count=100, tweet_mode='extended', lang='en')
    results_df = json_normalize([r._json for r in results])
    return results_df['full_text']

def get_twitter_keywords(n_words=50):
    tweets_df = get_twitter_query()
    keywords_df = get_keywords(tweets_df)
    return keywords_df.agg('sum').nlargest(n_words)

# construct github query
def get_github_query(min_stars=10, min_forks=10, keywords=keywords_ls):
    keywords_str = '"' + '"+OR+"'.join(keywords) + '"'
    filters_str = "&stars:>{}&forks:>{}&sort=stars".format(min_stars, min_forks)
    query = base_api + keywords_str + filters_str
    q = requests.get(query, headers=token_header)
    repos = json.loads(q.content)['items']
    repos_df = pd.DataFrame(repos).loc[:, ['name', 'html_url', 'description', 'forks', 'stargazers_count', "url"]]

    readme_ls = []
    for i in repos_df["url"]:
        print(f'fetching repo: {i}')
        try:
            readme_url = i + "/contents/README.md?ref=master"
            r = requests.get(readme_url, headers=token_header)
            readme = json.loads(r.content)['content']
            readme_ls.append(pybase64.b64decode(readme).decode('utf-8'))
        except KeyError:
            readme_ls.append(np.nan)

    repos_df["readme"] = readme_ls
    return repos_df

def get_github_keywords(n_words=50):
    repos_df = get_github_query()
    text_cols = ['name', 'description', 'readme']
    repos_df['content'] = repos_df[text_cols].apply(lambda row: ' '.join(row.values.astype(str)), axis=1)
    keywords_df = get_keywords(repos_df['content'])
    return keywords_df.agg('sum').nlargest(n_words)


if __name__ == '__main__':
    twitter_keywords = get_twitter_keywords()
    github_repos = get_github_query()
    github_keywords = get_github_keywords()
    date = datetime.now().strftime('%Y_%m_%d')
    twitter_keywords.to_csv(f'twitter_keywords_{date}.csv')
    github_repos.to_csv(f'github_repos_{date}.csv')
    github_keywords.to_csv(f'github_keywords_{date}.csv')